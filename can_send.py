from panda import Panda
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from opendbc.can.packer import CANPacker
from os.path import dirname, abspath, join
import cantools

dbc_name ='toyota_nodsu_hybrid_pt_generated' # put you correct odbc here (search in values.py)

# DBC files: car and leddar
base_path = dirname(abspath(__file__))
parent_path = abspath(join(base_path, os.pardir))
leddar = join(parent_path,'car/kia_forte_koup_2013.dbc')
LEDDAR_DBC = cantools.database.load_file(leddar)

# SPAS steering limits
STEER_ANG_MAX = 360          # SPAS Max Angle
STEER_ANG_MAX_RATE = 1.5    # SPAS Degrees per ms

# LEDDAR_DBC.decode_message(address, dat)
# values = {
#   "CF_Spas_Stat": 0,
#   "CF_Spas_TestMode": 0, # Maybe if set to 1 will ignore VS... needs testing.
#   "CR_Spas_StrAngCmd": 100,
#   "CF_Spas_BeepAlarm": 0,
#   "CF_Spas_Mode_Seq": 2, # 2 if LEGACY_SAFETY_MODE_CAR else 1,
#   "CF_Spas_AliveCnt": 100 % 0x200, 
#   "CF_Spas_Chksum": 0,
#   "CF_Spas_PasVol": 0,
# }

# msg = LEDDAR_DBC.encode_message(912, values)
# values = {
#   "CF_Spas_HMI_Stat": 0,
#   "CF_Spas_Disp": 0,
#   "CF_Spas_FIL_Ind": 0,
#   "CF_Spas_FIR_Ind": 0,
#   "CF_Spas_FOL_Ind": 0,
#   "CF_Spas_FOR_Ind": 0,
#   "CF_Spas_VolDown": 0,
#   "CF_Spas_RIL_Ind": 0,
#   "CF_Spas_RIR_Ind": 0,
#   "CF_Spas_FLS_Alarm": 0,
#   "CF_Spas_ROL_Ind": 0,
#   "CF_Spas_ROR_Ind": 0,
#   "CF_Spas_FCS_Alarm": 0,
#   "CF_Spas_FI_Ind": 0,
#   "CF_Spas_RI_Ind": 0,
#   "CF_Spas_FRS_Alarm": 0,
#   "CF_Spas_FR_Alarm": 0,
#   "CF_Spas_RR_Alarm": 0,
#   "CF_Spas_BEEP_Alarm": 0,
#   "CF_Spas_StatAlarm": 0,
#   "CF_Spas_RLS_Alarm": 0,
#   "CF_Spas_RCS_Alarm": 0,
#   "CF_Spas_RRS_Alarm": 0
# }

# msg = LEDDAR_DBC.encode_message(1268, values)
# print(msg)

# def main():
  # msg = create_spas11(0, 1, 2, 3)
  # SPAS11
  # p.can_send(0x912, msg, 0)
  # SPAS12
  # p.can_send(0x1268, b"\x00\x00\x00\x00\x00\x00\x00\x00", 0)
  # print(msg)

def clip(x, lo, hi):
  return max(lo, min(hi, x))

def interp(x, xp, fp):
  N = len(xp)

  def get_interp(xv):
    hi = 0
    while hi < N and xv > xp[hi]:
      hi += 1
    low = hi - 1
    return fp[-1] if hi == N and xv > xp[low] else (
      fp[0] if hi == 0 else
      (xv - xp[low]) * (fp[hi] - fp[low]) / (xp[hi] - xp[low]) + fp[low])

  return [get_interp(v) for v in x] if hasattr(x, '__iter__') else get_interp(x)

def mean(x):
  return sum(x) / len(x)


def create_spas11(en_spas, apply_steer, spas_mode_sequence, frame):
    values = {
      "CF_Spas_Stat": en_spas,
      "CF_Spas_TestMode": 0, # Maybe if set to 1 will ignore VS... needs testing.
      "CR_Spas_StrAngCmd": apply_steer,
      "CF_Spas_BeepAlarm": 0,
      "CF_Spas_Mode_Seq": spas_mode_sequence, # 2 if LEGACY_SAFETY_MODE_CAR else 1,
      "CF_Spas_AliveCnt": frame % 0x200, 
      "CF_Spas_Chksum": 0,
      "CF_Spas_PasVol": 0,
    }
    dat = LEDDAR_DBC.encode_message(912,values)
    # if car_fingerprint in CHECKSUM["crc8"]:
    #   dat = dat[:6]
    #   values["CF_Spas_Chksum"] = hyundai_checksum(dat)
    # else:
    values["CF_Spas_Chksum"] = sum(dat[:6]) % 256
    return LEDDAR_DBC.encode_message(912,values)

def create_ems_366(enabled):
  values = {
      "TQI_1": 0,
      "N": 0,
      "TQI_2": 0,
      "VS": 0,
      "SWI_IGK": 0,
  }
  if enabled:
    values["VS"] = 1
  return LEDDAR_DBC.encode_message(870,values)

if __name__ == "__main__":

    # main()
  last_apply_angle = 0.0
  en_spas = 3
  mdps11_stat_last = 0
  spas_active = False
  mdps_bus = 2
  spas_enabled = True
  apply_steer_ang = 0
  mdps11_stat = 0
  mdps11_strang = 0
  cruz_on = 0
  cruz_on_last = 0

  #SPAS TYPE2
  en_cnt = 0
  spas_enabled2 = True

  try:
    print("Trying to connect to Panda over USB...")
    p = Panda()
  
  except AssertionError:
    print("USB connection failed. Trying WiFi...")
    sys.exit(0)

	#Panda Safety off
  p.set_safety_mode(Panda.SAFETY_ALLOUTPUT)
  #p.set_power_save(False)

	# while True:
	# 	try:
	# 	  p.send_heartbeat()
	# 	  time.sleep(1)
	# 	except:
	# 	  break

	#SEt Can speed
  print("connected")
  print("%s: %s" % (p.get_serial()[0], p.get_version()))
  #p.set_can_speed_kbps(0, 125)
  frame = 0
  try:
    while True:
      if cruz_on == 1 or cruz_on_last == 1:
        spas_active = True
        cruz_on_last = cruz_on
      else:
        spas_active = False
        cruz_on_last = cruz_on

	#   	#EMS14 엔진 점검등 켜기
	#   	#p.can_send(0x545, b'\x02\x00\x00\x00\x00\x00\x00\x00', 0)

	#   	#Engine Rpm Set to 1k
	#   	#p.can_send(0x316, b'\x45\x1f\xe6\x0f\x1f\x1a\x00\x7f', 0)

	#   	#Engine Rpm set to over the limit
	#   	#p.can_send(0x316, b'\x00\x00\xff\x0f\x00\x00\xff\x00', 0)
	  	
	#   	#sleep 0.1s
	#   	#time.sleep(0.1)
	#   	#print('send data')

      steerAngle = -50 if mdps11_strang > 50 else 55
      #steerAngle = -10
      
      #print(steerAngle, -1*(STEER_ANG_MAX), STEER_ANG_MAX)

      apply_steer_ang_req = clip(steerAngle, -1*(STEER_ANG_MAX), STEER_ANG_MAX)
      #apply_steer_ang_req = -10

      # SPAS limit angle rate for safety
      if abs(apply_steer_ang - apply_steer_ang_req) > STEER_ANG_MAX_RATE:
        if apply_steer_ang_req > apply_steer_ang:
          apply_steer_ang += STEER_ANG_MAX_RATE
        else:
          apply_steer_ang -= STEER_ANG_MAX_RATE
      else:
        apply_steer_ang = apply_steer_ang_req


############### SPAS STATES ############## JPR
# State 1 : Start
# State 2 : New Request
# State 3 : Ready to Assist(Steer)
# State 4 : Hand Shake between OpenPilot and MDPS ECU
# State 5 : Assisting (Steering)
# State 6 : Failed to Assist (Steer)
# State 7 : Cancel
# State 8 : Failed to get ready to Assist (Steer)
# ---------------------------------------------------
      if spas_enabled:
        #Spoof Speed
        if mdps_bus:
          spas_active_stat = False
          if spas_active: # Spoof Speed on mdps11_stat 4 and 5 JPR
            if mdps11_stat == 4 or mdps11_stat == 5 or mdps11_stat == 3: 
              spas_active_stat = True
            else:
              spas_active_stat = False
          p.can_send(0x870, create_ems_366(spas_active_stat), 0)

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

          if not spas_active:
            apply_steer_ang = mdps11_strang

          mdps11_stat_last = mdps11_stat
          p.can_send(0x390,create_spas11(en_spas, apply_steer_ang, mdps_bus,(frame // 2)),0)



      if (frame % 2) == 0 and spas_enabled2:
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

        mdps11_stat_last = mdps11_stat
        en_cnt += 1
        p.can_send(0x390,create_spas11(en_spas, apply_steer_ang, mdps_bus,(frame // 2)),0)
        #can_sends.append(create_spas11(self.packer, (frame // 2), self.en_spas, self.apply_steer_ang, self.checksum))




      # SPAS12 20Hz
      if (frame % 5) == 0:
        #can_sends.append(create_spas12(mdps_bus))
        p.can_send(0x4f4, b"\x00\x00\x00\x00\x00\x00\x00\x00", 0)
        print("MDPS SPAS State: ", mdps11_stat) # SPAS STATE DEBUG
        print("OP SPAS State: ", en_spas) # OpenPilot Ask MDPS to switch to state.
      
      data = p.can_recv()
      for addr, _, dat, bus in data:
        if (addr == 912): # SPAS11
          smdps11Msg = LEDDAR_DBC.decode_message(addr, dat)
          print(smdps11Msg)
        elif(addr == 357): # VSM2
          smdps12Msg = LEDDAR_DBC.decode_message(addr, dat)
        elif(addr == 897): # MDPS11
          mdpsMsg = LEDDAR_DBC.decode_message(addr, dat)
          mdps11_strang = mdpsMsg["CR_Mdps_StrAng"]
          mdps11_stat = mdpsMsg["CF_Mdps_Stat"]
          print('MDPS11')
          print(mdpsMsg)
        elif(addr == 1264): # CLU11
          cluMsg = LEDDAR_DBC.decode_message(addr, dat)
          aa = cluMsg["CF_Clu_CruiseSwState"]
          cruz_on = cluMsg["CF_Clu_CruiseSwMain"]
          cc = cluMsg["CF_Clu_Odometer"]
          #mdps11_strang = mdpsMsg["CR_Mdps_StrAng"]
          #mdps11_stat = mdpsMsg["CF_Mdps_Stat"]
          #print('CLU11')
          #print(aa)
          #print(bb)
          #print(cc)
        elif(addr == 914): # S_MDPS11
          s_mdps11Msg = LEDDAR_DBC.decode_message(addr, dat)
          mdps11_strang = s_mdps11Msg["CR_Mdps_StrAng"]
          mdps11_stat = s_mdps11Msg["CF_Mdps_Stat"]
          if(frame % 2) == 0:
            print('S_MDPS11')
            print(s_mdps11Msg)
        
      # print(addr, _, dat, bus)
    
      frame = frame+1
	  	# get can msg
	    # data = panda.can_recv()
	    # for addr, _, dat, bus in data:
	    #   print(addr, _, dat, bus)
  except KeyboardInterrupt:
	  pass
