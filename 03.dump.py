import sys
import argparse
import tqdm

from panda.python import Panda
from panda.python.uds import UdsClient, SESSION_TYPE, DATA_IDENTIFIER_TYPE
try:
    from panda.ccp import CcpClient, BYTE_ORDER
except ImportError:
    from panda.python.ccp import CcpClient, BYTE_ORDER

CHUNK_SIZE = 4

class PARTS:
  Ecu = "Engine Control Unit"
  Transmission = "Transmission"
  Ems = "Electric Mission Sytem"
  Eps = "Electric Power Steering"
  esp = ""
  FwdCamera = "Forward Camera"
  FwdRadar = "Forward radar"
  vsa = ""

class BRAND:
  HKG = "HYUNDAI & KIA & GENESIS"


Hyundai_Radar: DATA_IDENTIFIER_TYPE = 0x0142

# FW_DATA_ID[BRAND.HKG][PARTS.Ecu]
FW_DATA_ID = {
  BRAND.HKG: {
    PARTS.Ecu:0x7e0,
    PARTS.Transmission:0x7e1,
    PARTS.Eps:0x7d4,
    PARTS.esp:0x7d1,
    PARTS.FwdCamera:0x7c4,
    PARTS.FwdRadar:0x7d0,
    # PARTS.Ems:0x7d4,
    # PARTS.vsa:0x7d4,
  }
}

default_config = b"\x00\x00\x00\x01\x00\x00"
#current_config = b"\x00\x00\x00\x01\x00\x01"
new_config = b"\x00\x00\x00\x01\x00\x01"

brand = BRAND.HKG

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='configure radar to output points (or reset to default)')
  parser.add_argument('--debug', action="store_true", default=False, help='enable debug output (default: false)')
  parser.add_argument('--bus', type=int, default=0, help='can bus to use (default: 0)')
  parser.add_argument("--start-address", default=0, type=int, help="start address")
  parser.add_argument("--end-address", default=0x5FFFF, type=int, help="end address (inclusive)")
  parser.add_argument("--output", required=True, help="output file")
  args = parser.parse_args()

  confirm = input("power on the vehicle keeping the engine off (press start button twice) then type OK to continue: ").upper().strip()
  if confirm != "OK":
    print("\nyou didn't type 'OK! (aborted)")
    sys.exit(0)

  panda = Panda()
  panda.can_clear(0xFFFF)
  panda.set_safety_mode(Panda.SAFETY_ELM327)
  uds_client = UdsClient(panda, FW_DATA_ID[BRAND.HKG][PARTS.Eps], bus=args.bus, debug=args.debug)

  print("\n[START EXTENDED DIAGNOSTIC SESSION]")
  uds_client.diagnostic_session_control(SESSION_TYPE.EXTENDED_DIAGNOSTIC)

  ECU_IDENT = 0x9B
  STATUS_FLASH = 0x9C

  print("[FIRMWARE VERSION]")
  fw_version_data_id : DATA_IDENTIFIER_TYPE = 0xf100 # type: ignore
  fw_version = uds_client.read_data_by_identifier(fw_version_data_id)
  print("version : ",fw_version)


  print("[HARDWARE/SOFTWARE VERSION]")
  ecu_ident_data_id : DATA_IDENTIFIER_TYPE = ECU_IDENT # type: ignore
  ident = uds_client.read_data_by_identifier(ecu_ident_data_id)
  print(f"Part Number : {ident[:10]}")

  status_data_id : DATA_IDENTIFIER_TYPE = STATUS_FLASH # type: ignore
  status = uds_client.read_data_by_identifier(status_data_id)
  print("Flash status : ", status)

  print("[CONNECTING CLIENT]")
  client = CcpClient(panda, 1746, 1747, byte_order=BYTE_ORDER.LITTLE_ENDIAN, bus=args.bus)
  client.connect(0x0)

  progress = tqdm.tqdm(total=args.end_address - args.start_address)

  addr = args.start_address
  client.set_memory_transfer_address(0, 0, addr)

  print("[RECEIVING DATA]")
  with open(args.output, "wb") as f:
      while addr < args.end_address:
          f.write(client.upload(CHUNK_SIZE)[:CHUNK_SIZE])
          f.flush()

          addr += CHUNK_SIZE
          progress.update(CHUNK_SIZE)
  print("[RECEIVING EXIT]")

  print("[DONE]")
  sys.exit(0)
