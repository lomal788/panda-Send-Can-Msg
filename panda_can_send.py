from panda import Panda
import sys
import time


if __name__ == "__main__":

	try:
		print("Trying to connect to Panda over USB...")
		p = Panda()

	except AssertionError:
		print("USB connection failed. Trying WiFi...")
		sys.exit(0)

	#Panda Safety off
	p.set_safety_mode(Panda.SAFETY_ALLOUTPUT)

	#p.set_power_save(False)

	while True:
		try:
		  p.send_heartbeat()
		  time.sleep(1)
		except:
		  break

	#SEt Can speed
	#p.set_can_speed_kbps(0, 125)
	#cnt = 0
	try:
	  while True:
	  	#EMS14 엔진 점검등 켜기
	  	#p.can_send(0x545, b'\x02\x00\x00\x00\x00\x00\x00\x00', 0)

	  	#Engine Rpm Set to 1k
	  	#p.can_send(0x316, b'\x45\x1f\xe6\x0f\x1f\x1a\x00\x7f', 0)

	  	#Engine Rpm set to over the limit
	  	#p.can_send(0x316, b'\x00\x00\xff\x0f\x00\x00\xff\x00', 0)

	  	
	  	#sleep 0.1s
	  	#time.sleep(0.1)
	  	#print('send data')
	  	
	  	#cnt = cnt+1
	  	#get can msg
	    #data = panda.can_recv()
	    #for addr, _, dat, bus in data:
	      #print(addr, _, dat, bus)
	except KeyboardInterrupt:
	  pass