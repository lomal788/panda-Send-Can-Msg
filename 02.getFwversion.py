import sys
import argparse

from panda.python import Panda
from panda.python.uds import UdsClient, SESSION_TYPE, DATA_IDENTIFIER_TYPE,\
  MessageTimeoutError, NegativeResponseError

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
  parser.add_argument('--default', action="store_true", default=False, help='reset to default configuration (default: false)')
  parser.add_argument('--debug', action="store_true", default=False, help='enable debug output (default: false)')
  parser.add_argument('--bus', type=int, default=0, help='can bus to use (default: 0)')
  args = parser.parse_args()

  confirm = input("power on the vehicle keeping the engine off (press start button twice) then type OK to continue: ").upper().strip()
  if confirm != "OK":
    print("\nyou didn't type 'OK! (aborted)")
    sys.exit(0)

  panda = Panda()
  panda.can_clear(0xFFFF)
  panda.set_safety_mode(Panda.SAFETY_ELM327)
  uds_client = UdsClient(panda, FW_DATA_ID[BRAND.HKG][PARTS.Eps], bus=args.bus, debug=args.debug)


  print("\n[START DIAGNOSTIC SESSION]")
  session_type : SESSION_TYPE = 0x07 # type: ignore
  uds_client.diagnostic_session_control(SESSION_TYPE.EXTENDED_DIAGNOSTIC)

  print("[HARDWARE/SOFTWARE VERSION]")
  fw_version_data_id : DATA_IDENTIFIER_TYPE = 0xf100 # type: ignore
  fw_version = uds_client.read_data_by_identifier(fw_version_data_id)
  print(fw_version)


  odx_file, current_coding = None, None
  try:
    hw_pn = uds_client.read_data_by_identifier(DATA_IDENTIFIER_TYPE.VEHICLE_MANUFACTURER_ECU_HARDWARE_NUMBER).decode("utf-8")
    sw_pn = uds_client.read_data_by_identifier(DATA_IDENTIFIER_TYPE.VEHICLE_MANUFACTURER_SPARE_PART_NUMBER).decode("utf-8")
    sw_ver = uds_client.read_data_by_identifier(DATA_IDENTIFIER_TYPE.VEHICLE_MANUFACTURER_ECU_SOFTWARE_VERSION_NUMBER).decode("utf-8")
    component = uds_client.read_data_by_identifier(DATA_IDENTIFIER_TYPE.SYSTEM_NAME_OR_ENGINE_TYPE).decode("utf-8")
    # odx_file = uds_client.read_data_by_identifier(DATA_IDENTIFIER_TYPE.ODX_FILE).decode("utf-8")
    # current_coding = uds_client.read_data_by_identifier(VOLKSWAGEN_DATA_IDENTIFIER_TYPE.CODING)  # type: ignore
    # coding_text = current_coding.hex()

    print("\nEPS diagnostic data\n")
    print(f"   Part No HW:   {hw_pn}")
    print(f"   Part No SW:   {sw_pn}")
    print(f"   SW Version:   {sw_ver}")
    print(f"   Component:    {component}")
    # print(f"   Coding:       {coding_text}")
    # print(f"   ASAM Dataset: {odx_file}")
  except NegativeResponseError:
    print("Error fetching data from EPS")
    quit()
  except MessageTimeoutError:
    print("Timeout fetching data from EPS")
    quit()




  # fw_version_data_id : DATA_IDENTIFIER_TYPE = 0xf100 # type: ignore

  # print("[HARDWARE/SOFTWARE VERSION]")
  # for item in FW_DATA_ID[BRAND.HKG].items():
  #   uds_client.tx_addr = hex(item[1])
  #   uds_client.rx_addr = uds_client.get_rx_addr_for_tx_addr(hex(item[1]))

  #   fw_version = uds_client.read_data_by_identifier(fw_version_data_id)    
  #   print(f"{item[0]} {hex(item[1])} ")
  #   print(fw_version)

  print("[DONE]")
  sys.exit(0)
