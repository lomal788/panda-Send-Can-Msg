import sys
import argparse

from panda.python import Panda
from panda.python.uds import UdsClient, SESSION_TYPE, DATA_IDENTIFIER_TYPE

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

Hyundai_Varient_Code_Addr = 0x0142

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
  uds_client = UdsClient(panda, 0x7D0, bus=args.bus, debug=args.debug)


  print("\n[START DIAGNOSTIC SESSION]")
  session_type : SESSION_TYPE = 0x07 # type: ignore
  uds_client.diagnostic_session_control(session_type)

  print("[HARDWARE/SOFTWARE VERSION]")
  fw_version_data_id : DATA_IDENTIFIER_TYPE = 0xf100 # type: ignore
  fw_version = uds_client.read_data_by_identifier(fw_version_data_id)
  print(fw_version)
#   if fw_version not in SUPPORTED_FW_VERSIONS.keys():
#     print("radar not supported! (aborted)")
#     sys.exit(1)

  print("[GET CONFIGURATION]")
  # Varient Code
  config_data_id : DATA_IDENTIFIER_TYPE = 0x0142 # type: ignore
  current_config = uds_client.read_data_by_identifier(config_data_id)

  print(f"current config: 0x{current_config.hex()}")
  if current_config != new_config:
    print("[CHANGE CONFIGURATION]")
    print(f"new config:     0x{new_config.hex()}")
    uds_client.write_data_by_identifier(config_data_id, new_config)
    if not args.default and current_config != default_config:
      print("\ncurrent config does not match expected default! (aborted)")
      sys.exit(1)

    print("[DONE]")
    print("\nrestart your vehicle and ensure there are no faults")
    if not args.default:
      print("you can run this script again with --default to go back to the original (factory) settings")
  else:
    print("[DONE]")
    print("\ncurrent config is already the desired configuration")
    sys.exit(0)
