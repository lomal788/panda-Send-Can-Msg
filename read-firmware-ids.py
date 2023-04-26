# EXAMPLE OUTPUT
# ==============
# opening device 0xddcc
# connected
# tester present ...
# read data by id: boot software id ...
# 39990-TVA-A110
# read data by id: application software id ...
# 39990-TVA-A150
# read data by id: application data id ...
# READ_DATA_BY_IDENTIFIER - request out of range
# read data by id: boot software fingerprint ...
# READ_DATA_BY_IDENTIFIER - request out of range
# read data by id: application software fingerprint ...
# READ_DATA_BY_IDENTIFIER - request out of range
# read data by id: application data fingerprint ...
# READ_DATA_BY_IDENTIFIER - request out of range

from python import Panda
from python.uds import UdsClient, DATA_IDENTIFIER_TYPE

if __name__ == "__main__":
  panda = Panda()
  panda.set_safety_mode(Panda.SAFETY_ELM327)
  address = 0x18da30f1 # EPS
  uds_client = UdsClient(panda, address, debug=False)
  print("tester present ...")
  uds_client.tester_present()

  try:
    print("read data by id: boot software id ...")
    data = uds_client.read_data_by_identifier(DATA_IDENTIFIER_TYPE.BOOT_SOFTWARE_IDENTIFICATION)
    print(data)
  except BaseException as e:
    print(e)

  try:
    print("read data by id: application software id ...")
    data = uds_client.read_data_by_identifier(DATA_IDENTIFIER_TYPE.APPLICATION_SOFTWARE_IDENTIFICATION)
    print(data)
  except BaseException as e:
    print(e)

  try:
    print("read data by id: application data id ...")
    data = uds_client.read_data_by_identifier(DATA_IDENTIFIER_TYPE.APPLICATION_DATA_IDENTIFICATION)
    print(data)
  except BaseException as e:
    print(e)

  try:
    print("read data by id: boot software fingerprint ...")
    data = uds_client.read_data_by_identifier(DATA_IDENTIFIER_TYPE.BOOT_SOFTWARE_FINGERPRINT)
    print(data)
  except BaseException as e:
    print(e)

  try:
    print("read data by id: application software fingerprint ...")
    data = uds_client.read_data_by_identifier(DATA_IDENTIFIER_TYPE.APPLICATION_SOFTWARE_FINGERPRINT)
    print(data)
  except BaseException as e:
    print(e)

  try:
    print("read data by id: application data fingerprint ...")
    data = uds_client.read_data_by_identifier(DATA_IDENTIFIER_TYPE.APPLICATION_DATA_FINGERPRINT)
    print(data)
  except BaseException as e:
    print(e)
