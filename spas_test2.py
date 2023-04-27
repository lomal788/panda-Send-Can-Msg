#!/usr/bin/env python3

"""
For greatest compatibility this script doesn't depend bob-built-in modules - 
except for the USB CAN interface (Panda, ) and it can be run on PC or Comma EON. 
Keyboard input (w,s, q keys) in game mode - supported even over SSH
"""
from panda import Panda
# install https://github.com/commaai/panda

import binascii
import argparse
import time
import _thread
import queue
import threading
import subprocess
import crcmod
import csv

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from opendbc.can.packer import CANPacker
from os.path import dirname, abspath, join
import cantools

# DBC files: car and leddar
base_path = dirname(abspath(__file__))
parent_path = abspath(join(base_path, os.pardir))
leddar = join(parent_path,'openpilot/kia_forte_koup_2013.dbc')
LEDDAR_DBC = cantools.database.load_file(leddar)

hyundai_checksum = crcmod.mkCrcFun(0x11D, initCrc=0xFD, rev=False, xorOut=0xdf)


def heartbeat_thread(p):
  while True:
    try:
      p.send_heartbeat()
      time.sleep(1)
    except:
      break
      raise

# from Msg.h which is from ocelot_controls.dbc
MSG_STEERING_COMMAND_FRAME_ID = 0x22e
MSG_STEERING_STATUS_FRAME_ID = 0x22f
motor_bus_speed = 500  #StepperServoCAN baudrate 500kbps
#MOTOR_MSG_TS = 0.008 #10Hz
MOTOR_MSG_TS = 0.0008 #100Hz
MAX_TORQUE = 9
MAX_ANGLE = 4095

#game mode options
torque_rise_factor = 1.2
torque_decay_factor = 0.8
angle_rise_factor = 1.4
quick_decay_factor = 0.6 #common

#STEERING_COMMAND:STEER_MODE options
modes = {
    'OFF': 0,
    'TORQUE_CONTROL': 1,
    'ANGLE_CONTROL': 2,
    'SOFT_OFF': 3
}

actions = {
    'UP': 1,
    'DOWN': 2,
    'STOP': 3,
    'HOLD': 4
}

def create_ems366():
    values = {
      "TQI_1": 10,
      "N": 1000,
      "TQI_2": 10,
      "VS": 0,
      "SWI_IGK": 1,
    }

    return LEDDAR_DBC.encode_message(870,values)

def create_spas11(en_spas, apply_steer, spas_mode_sequence, frame):
    # print(frame % 0xff)
    values = {
      "CF_Spas_Stat": en_spas,
      "CF_Spas_TestMode": 0, # Maybe if set to 1 will ignore VS... needs testing.
      "CR_Spas_StrAngCmd": apply_steer,
      "CF_Spas_BeepAlarm": 0,
      "CF_Spas_Mode_Seq": spas_mode_sequence, # 2 if LEGACY_SAFETY_MODE_CAR else 1,
      # "CF_Spas_AliveCnt": 255 if frame % 0x200 > 255 else frame % 0x200, 
      "CF_Spas_AliveCnt": frame / 2,  #0xff
      "CF_Spas_Chksum": 0,
      "CF_Spas_PasVol": 0,
    }

    dat = LEDDAR_DBC.encode_message(912,values)
    # if car_fingerprint in CHECKSUM["crc8"]:
    dat = dat[:6]
    values["CF_Spas_Chksum"] = hyundai_checksum(dat)
    # else:
    # values["CF_Spas_Chksum"] = sum(dat[:6]) % 256
    # checksum = (sum(dat[:6]) + dat[7]) % 256

    return LEDDAR_DBC.encode_message(912,values)


def calc_checksum_8bit(work_data, msg_id): # 0xb8 0x1a0 0x19e 0xaa 0xbf
  checksum = msg_id
  for byte in work_data: #checksum is stripped from the data
    checksum += byte     #add up all the bytes

  checksum = (checksum & 0xFF) + (checksum >> 8); #add upper and lower Bytes
  checksum &= 0xFF #throw away anything in upper Byte
  return checksum

import struct
def steering_msg_cmd_data(counter: int, steer_mode: int, steer_torque: float, steer_angle: float) -> bytes:
  # Define the structure format and pack the data
  canbus_fmt = '<Bhb' # msg '<bbhb'  without checksum byte[0]
  packed_data = struct.pack(canbus_fmt,
                            (steer_mode << 4) | counter,
                            max(min(int(steer_angle  * 8), 32767), -32768),
                            max(min(int(steer_torque * 8), 127), -128)
                            )
  checksum = calc_checksum_8bit(packed_data, MSG_STEERING_COMMAND_FRAME_ID)
  packed_data = struct.pack('<B', checksum) + packed_data # add checksum byte at the end
  return packed_data

def rise_and_decay(value:float, delta:float, max_min_limit:float):
  small_value = 0.1
  decay = False
  if delta > 1:
    value += small_value
  elif delta < -1:
    value -= small_value
  else:
    decay = True

  if value*delta > 0 or decay:  #same sign
    value = value * abs(delta)
  else: #if direction change, use quick decay
    value = value * quick_decay_factor 
  
  if value > max_min_limit:
    value = max_min_limit
  elif value < -max_min_limit:
    value = -max_min_limit
  elif value < small_value and value > -small_value: #if value is small, set to 0
    value = 0.0

  return value

def CAN_tx_thread(p:Panda, bus):
  print("Starting CAN TX thread...")
  global _torque
  global _angle
  global _mode
  global mdps11_stat
  global mdps11_strang
  global _en_spas
  global apply_steer_ang

  frame = 0 # 10hz
  en_spas = 1
  _en_spas = 1
  mdps11_stat_last = 0
  mdps11_stat = 2
  mdps11_strang = 0
  __type = "1"

  # SEND SPAS12
  p.can_send(0x4f4, b"\x00\x00\x00\x00\x00\x00\x00\x00", 0)
  p.can_send(0x436, b"\x00\x00\x00\x00", 0)

#   dat = steering_msg_cmd_data(frame, _mode, _torque, _angle)
#   p.can_send(MSG_STEERING_COMMAND_FRAME_ID, dat, bus)
  
  t_prev =0
  while True:
    time.sleep(MOTOR_MSG_TS)

    # SPAS11 50 HZ
    if (frame % 2) == 0:
        if mdps11_stat == 7:
            en_spas = 7

        if mdps11_stat == 7 and mdps11_stat_last == 7:
            en_spas = 3
            if mdps11_stat == 3:
                en_spas = 2
                if mdps11_stat == 2:
                    en_spas = 3
                    if mdps11_stat == 3:
                        en_spas = 4
                        if mdps11_stat == 3 and en_spas == 4:
                            en_spas = 3  

        if mdps11_stat == 3 and spas_active:
            en_spas = 4
            if mdps11_stat == 4:
                en_spas = 5
        
        if mdps11_stat == 2 and spas_active:
            en_spas = 3 # Switch to State 3, and get Ready to Assist(Steer). JPR

        if mdps11_stat == 3 and spas_active:
            en_spas = 4
        
        if mdps11_stat == 4 and spas_active:
            en_spas = 5

        if mdps11_stat == 5 and not spas_active:
            en_spas = 3

        if mdps11_stat == 6: # Failed to Assist and Steer, Set state back to 2 for a new request. JPR
            en_spas = 2

        if mdps11_stat == 8: #MDPS ECU Fails to get into state 3 and ready for state 5. JPR
            en_spas = 2

        # if mdps11_stat == 1: #MDPS ECU Fails to get into state 3 and ready for state 5. JPR
        #     en_spas = 2

        apply_steer_ang = _angle
        if not spas_active:
            apply_steer_ang = mdps11_strang


        if __type == "2":
            if mdps11_stat == 7 and not mdps11_stat_last == 7:
                en_spas == 7
                en_cnt = 0
            if en_spas == 7 and en_cnt >= 8:
                en_spas = 3
                en_cnt = 0

            if en_cnt < 8 and spas_active:
                en_spas = 4
            elif en_cnt >= 8 and spas_active:
                en_spas = 5
        
            if not spas_active:
                apply_steer_ang = mdps11_strang
                en_spas = 3
                en_cnt = 0

            en_cnt += 1

        mdps11_stat_last = mdps11_stat
        _en_spas = en_spas

        if apply_steer_ang != 32767:
          p.can_send(0x390,create_spas11(en_spas, apply_steer_ang, 2,frame % 0x200),0)

    # SPAS12 20HZ
    if (frame % 5) == 0:
      #SPAS12
      p.can_send(0x4f4, b"\x00\x00\x00\x00\x00\x00\x00\x00", 0)
      #PAS11
      # p.can_send(0x436, b"\x00\x00\x00\x00", 0)

      #frame
      # print("MDPS degree: ", apply_steer_ang) # MDPS degree
      # print("MDPS SPAS State: ", mdps11_stat) # SPAS STATE DEBUG
      # print("OP SPAS State: ", en_spas) # OpenPilot Ask MDPS to switch to state.

    frame += 1
    # dat = steering_msg_cmd_data(frame % 0xF, _mode, _torque, _angle)
    # p.can_send(MSG_STEERING_COMMAND_FRAME_ID, dat, bus)

def CAN_rx_thread(p, bus):
  global mdps11_strang
  global mdps11_stat

  import time
  date_string = time.strftime("%Y-%m-%d-%H:%M")


  outputfile = open('output' + date_string + '.csv', 'w')
  csvwriter = csv.writer(outputfile)
  # Write Header
  csvwriter.writerow(['Bus', 'MessageID', 'Message', 'MessageLength'])


  t_status_msg_prev =0
  print("Starting CAN RX thread...")
  p.can_clear(bus)     #flush the buffers
  while True:
    time.sleep(MOTOR_MSG_TS/10) #read fast enough so the CAN interface buffer is cleared each loop
    t = time.time()
    can_recv = p.can_recv()
    for address, _, dat, src in can_recv:
      csvwriter.writerow([str(src), str(address), f"0x{dat.hex()}", len(dat)])
      if src == bus and address == MSG_STEERING_STATUS_FRAME_ID:
        if t - t_status_msg_prev > 0.0001:
          hz = 1/(t - t_status_msg_prev)
        else:
          hz = -1
        print(f"{hz:3.0f}Hz, addr: {address}, bus: {bus}, dat: {binascii.hexlify(dat)}")
        t_status_msg_prev = t
      elif(address == 914): # S_MDPS11
        s_mdps11Msg = LEDDAR_DBC.decode_message(address, dat)
        mdps11_strang = s_mdps11Msg["CR_Mdps_StrAng"]
        mdps11_stat = s_mdps11Msg["CF_Mdps_Stat"]


def getChar(): #https://stackoverflow.com/a/36974338/1531161
  # figure out which function to use once, and store it in _func
  if "_func" not in getChar.__dict__:
    try:
      # for Windows-based systems
      import msvcrt # If successful, we are on Windows
      getChar._func=msvcrt.getch
    except ImportError:
      # for POSIX-based systems (with termios & tty support)
      import tty, sys, termios # raises ImportError if unsupported
      def _ttyRead():
        fd = sys.stdin.fileno()
        oldSettings = termios.tcgetattr(fd) # type: ignore
        try:
          tty.setcbreak(fd) # type: ignore
          answer = sys.stdin.read(1)
        finally:
          termios.tcsetattr(fd, termios.TCSADRAIN, oldSettings) # type: ignore
        return answer
      getChar._func=_ttyRead
  return getChar._func()


"""Detects long presses on wsad and perform torque ramping"""
def long_press_value_ramp(key_queue:queue.Queue, break_key:threading.Event):
  global _torque
  while not break_key.is_set():
    time.sleep(0.1) #clear key_queue buffer in 100ms
    try:
      c = key_queue.get_nowait()
    except queue.Empty:
      c = None
    if c == 'w':
      _torque = rise_and_decay(_torque, torque_rise_factor, MAX_TORQUE)
    elif c == 's':
      _torque = rise_and_decay(_torque, -torque_rise_factor, MAX_TORQUE)
    else:
      _torque = rise_and_decay(_torque, torque_decay_factor, MAX_TORQUE)
    print_cmd_state()

def print_cmd_state():
  global _torque
  global _angle
  global _mode
  global mdps11_stat
  global _en_spas
  global spas_active
  global mdps11_strang
  global apply_steer_ang

  if _mode == modes['TORQUE_CONTROL']:
    print(f"Torque: {_torque:3.2f}")
  elif _mode == modes['ANGLE_CONTROL']:
    print(f"Angle:{_angle:4.2f}, FeedForward torque: {_torque:3.2f}")
    spas_active = True
  else:
    spas_active = False
  print(spas_active)
  print(apply_steer_ang)
  print(mdps11_stat)
  print(_en_spas)

  # print("MDPS degree: ", apply_steer_ang) # MDPS degree
  # print("MDPS SPAS State: ", mdps11_stat) # SPAS STATE DEBUG
  # print("OP SPAS State: ", en_spas) # OpenPilot Ask MDPS to switch to state.


def motor_tester(bus):
  panda = Panda()
  panda.set_can_speed_kbps(bus, motor_bus_speed)
  # Now set the panda from its default of SAFETY_SILENT (read only) to SAFETY_ALLOUTPUT
  print("Setting Panda to All Output mode...")
  panda.set_safety_mode(Panda.SAFETY_ALLOUTPUT)
  print("Enable all pandas busses...") #in case panda was sleeping
  panda.set_power_save(False) #enable all the busses
  print("Enable panda usb heartbeat..") #so it doesn't stop
  _thread.start_new_thread(heartbeat_thread, (panda,))

  #Request off control mode first - in case motmo
  # or was in SoftOff fault mode
  
  print("\nRequesting motor OFF mode...")
#   dat = steering_msg_cmd_data(modes["OFF"], 0, 0.0, 0.0)
#   print('Sent:' + ''.join('\\x{:02x}'.format(b) for b in dat)) ##b"\x30\x00\x00\x00\x00"
#   panda.can_send(MSG_STEERING_COMMAND_FRAME_ID, dat, bus)
  
  global _torque
  global _angle
  global _mode
  global spas_active
  _torque = 0.0
  _angle = 0.0
  spas_active = False
  

  key_queue = queue.Queue(maxsize=2) #key buffer
  tx_t = threading.Thread(target=CAN_tx_thread, args=(panda, bus), daemon=True)
  rx_t = threading.Thread(target=CAN_rx_thread, args=(panda, bus), daemon=True)

  _mode = modes['OFF']

  first_run = True
  
  break_long_key = threading.Event()
  long_key_t = None #thread placeholder
  while True:
    if first_run:
      first_run = False
      tx_t.start()
      print(f"Mode: {[name for name, val in modes.items() if val == _mode][0]}")
      time.sleep(0.1)
      _mode = modes['TORQUE_CONTROL']
      print(f"Mode: {[name for name, val in modes.items() if val == _mode][0]}")
      rx_t.start()
      print("\nEnter torque value or used W/S keys to increase/decrease torque and A/D angle. Q to quit:") #show this before CAN messages spam the terminal
      
    try:
      c = getChar()
      if c == 'q' or c == '\x03':  # Ctrl+C
        break
      if c in {'w', 's'}: #in wsad gammode torque is controlled by keyboard and ramp generator
        if long_key_t is None:
          long_key_t = threading.Thread(target=long_press_value_ramp, args=(key_queue, break_long_key), daemon=True)
          long_key_t.start()
          # because getch is blocking and and because key presses arrive sometimes erratic (SSH)
        try:
          key_queue.put_nowait(c)
        except queue.Full:
          pass #fine
      elif c == 'm': #mode input mode
        _mode = (_mode + 1)%len(modes) # cycle thru modes
        print(_mode)
        print(f"Mode: {[name for name, val in modes.items() if val == _mode][0]}")
        print_cmd_state()
      elif c == 'd' or c == 'a': #angle input mode
        if _mode == modes['ANGLE_CONTROL']:
          if c == 'd':
            _angle = rise_and_decay(_angle, angle_rise_factor, MAX_ANGLE)
            _torque = max(abs(_torque), 0.1) #match torque signal to angle
          else:
            _angle = rise_and_decay(_angle, -angle_rise_factor, MAX_ANGLE)
            _torque = min(-abs(_torque), -0.1) #match torque signal to angle
          if _angle == 0.0:
            _torque = 0.0
          print_cmd_state()

      elif c in {'1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-'}: #numeric input mode
        if c == '-':
          c = getChar()
          temp = -float(c)
        else:
          temp = float(c)
        break_long_key.set() #stop long key detection and value ramping
        try:
          if long_key_t is not None:
            long_key_t.join() #wait for thread to finish
            long_key_t = None
        except RuntimeError:
          pass
        break_long_key.clear()  
        _torque = temp
        print_cmd_state()
    except KeyboardInterrupt:
      break

  print("Disabling output on Panda...")
  panda.set_safety_mode(Panda.SAFETY_SILENT)


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Simple motor tester-runner with numeric or game lile controls",
                                   formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("--bus", type=int, help="CAN bus id to which motor is connected", default=0)
  args = parser.parse_args()
  print("Killing boardd to release USB...")
  try: #useful if run on EON
    subprocess.run(['pkill', '-f', 'boardd'])
  except:
    pass
  motor_tester(args.bus)
