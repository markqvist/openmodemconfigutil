import serial
from serial.tools import list_ports
import requests
import json
import time
import struct
from time import sleep
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs
# from cryptography.hazmat.backends import default_backend
# from cryptography.hazmat.primitives import hashes
import hashlib
import base64
import psutil
import threading
import webview
import random
import os
import sys

portlist = []
volumelist = []
kiss_interface = None

class RNS():
	@staticmethod
	def log(msg):
		logtimefmt   = "%Y-%m-%d %H:%M:%S"
		timestamp = time.time()
		logstring = "["+time.strftime(logtimefmt)+"] "+msg
		print(logstring)

	@staticmethod
	def hexrep(data, delimit=True):
		delimiter = ":"
		if not delimit:
			delimiter = ""
		hexrep = delimiter.join("{:02x}".format(c) for c in data)
		return hexrep

	@staticmethod
	def prettyhexrep(data):
		delimiter = ""
		hexrep = "<"+delimiter.join("{:02x}".format(c) for c in data)+">"
		return hexrep

class Interface:
	IN  = False
	OUT = False
	FWD = False
	RPT = False
	name = None

	def __init__(self):
		pass

class KISS():
	FEND						= 0xC0
	FESC						= 0xDB
	TFEND						= 0xDC
	TFESC						= 0xDD
	CMD_UNKNOWN					= 0xFE
	CMD_DATA					= 0x00
	CMD_TXDELAY					= 0x01
	CMD_P						= 0x02
	CMD_SLOTTIME				= 0x03
	CMD_TXTAIL					= 0x04
	CMD_FULLDUPLEX				= 0x05
	CMD_SETHARDWARE				= 0x06
	CMD_SAVE_CONFIG				= 0x07
	CMD_READY       			= 0x0F
	CMD_AUDIO_PEAK  			= 0x12
	CMD_OUTPUT_GAIN 			= 0x09
	CMD_INPUT_GAIN  			= 0x0A
	CMD_PASSALL 				= 0x0B
	CMD_LOG_PACKETS 			= 0x0C
	CMD_GPS_MODE				= 0x0D
	CMD_BT_MODE					= 0x0E
	CMD_SERIAL_BAUDRATE			= 0x10
	CMD_EN_DIAGS    			= 0x13
	CMD_MODE 		   			= 0x14
	CMD_PRINT_CONFIG			= 0xF0
	CMD_LED_INTENSITY			= 0x08
	CMD_RETURN					= 0xFF

	ADDR_E_MAJ_VERSION			= 0x00
	ADDR_E_MIN_VERSION			= 0x01
	ADDR_E_CONF_VERSION			= 0x02
	ADDR_E_P					= 0x03
	ADDR_E_SLOTTIME				= 0x04
	ADDR_E_PREAMBLE				= 0x05
	ADDR_E_TAIL					= 0x06
	ADDR_E_LED_INTENSITY		= 0x07
	ADDR_E_OUTPUT_GAIN			= 0x08
	ADDR_E_INPUT_GAIN			= 0x09
	ADDR_E_PASSALL				= 0x0A
	ADDR_E_LOG_PACKETS			= 0x0B
	ADDR_E_CRYPTO_LOCK			= 0x0C
	ADDR_E_GPS_MODE				= 0x0D
	ADDR_E_BLUETOOTH_MODE		= 0x0E
	ADDR_E_SERIAL_BAUDRATE		= 0x0F
	ADDR_E_CHECKSUM				= 0x10
	ADDR_E_END					= 0x20

	CONFIG_GPS_OFF				= 0x00
	CONFIG_GPS_AUTODETECT		= 0x01
	CONFIG_GPS_REQUIRED			= 0x02

	CONFIG_BLUETOOTH_OFF		= 0x00
	CONFIG_BLUETOOTH_AUTODETECT	= 0x01
	CONFIG_BLUETOOTH_REQUIRED	= 0x02

	MODE_AFSK_300				= 0x01
	MODE_AFSK_1200				= 0x02
	MODE_AFSK_2400				= 0x03

	@staticmethod
	def escape(data):
		data = data.replace(bytes([0xdb]), bytes([0xdb])+bytes([0xdd]))
		data = data.replace(bytes([0xc0]), bytes([0xdb])+bytes([0xdc]))
		return data

class KISSInterface(Interface):
	MAX_CHUNK = 32768

	owner    = None
	port     = None
	speed    = None
	databits = None
	parity   = None
	stopbits = None
	serial   = None

	def __init__(self, owner, name, port, speed, databits, parity, stopbits, preamble, txtail, persistence, slottime, flow_control):
		self.serial    = None
		self.owner     = owner
		self.name      = name
		self.port      = port
		self.speed     = speed
		self.databits  = databits
		self.parity    = serial.PARITY_NONE
		self.stopbits  = stopbits
		self.timeout   = 100
		self.online    = False
		self.audiopeak = 0
		self.has_decode = False

		self.packet_queue    = []
		self.flow_control = flow_control
		self.interface_ready = False

		self.preamble    = preamble if preamble != None else 350;
		self.txtail      = txtail if txtail != None else 20;
		self.persistence = persistence if persistence != None else 64;
		self.slottime    = slottime if slottime != None else 20;

		self.modem_mode = None

		self.config_p			= None
		self.config_slottime	= None
		self.config_preamble	= None
		self.config_tail		= None
		self.config_led_intensity	= None
		self.config_output_gain		= None
		self.config_input_gain		= None
		self.config_passall			= None
		self.config_log_packets		= None
		self.config_crypto_lock		= None
		self.config_gps_mode		= None
		self.config_bluetooth_mode	= None
		self.config_serial_baudrate = None
		self.config_valid			= False


		if parity.lower() == "e" or parity.lower() == "even":
			self.parity = serial.PARITY_EVEN

		if parity.lower() == "o" or parity.lower() == "odd":
			self.parity = serial.PARITY_ODD

		try:
			RNS.log("Opening serial port "+self.port+"...")
			self.serial = serial.Serial(
				port = self.port,
				baudrate = self.speed,
				bytesize = self.databits,
				parity = self.parity,
				stopbits = self.stopbits,
				xonxoff = False,
				rtscts = False,
				timeout = 0,
				inter_byte_timeout = None,
				write_timeout = None,
				dsrdtr = False,
			)
		except Exception as e:
			RNS.log("Could not open serial port "+self.port)
			raise e

		if self.serial.is_open:
			# Allow time for interface to initialise before config
			sleep(2.2)
			thread = threading.Thread(target=self.readLoop)
			thread.setDaemon(True)
			thread.start()
			self.online = True
			RNS.log("Serial port "+self.port+" is now open")
			self.interface_ready = True
		else:
			raise IOError("Could not open serial port")


	def askForPeak(self):
		kiss_command = bytes([KISS.FEND])+bytes([KISS.CMD_AUDIO_PEAK])+bytes([0x01])+bytes([KISS.FEND])
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			raise IOError("Could not ask for peak data")

	def displayPeak(self, peak):
		self.audiopeak = peak

	def setPreamble(self, preamble):
		#preamble_ms = preamble
		#preamble = int(preamble_ms / 10)
		if preamble < 0:
			preamble = 0
		if preamble > 255:
			preamble = 255

		command = KISS.escape(bytes([preamble]))
		kiss_command = bytes([KISS.FEND])+bytes([KISS.CMD_TXDELAY])+command+bytes([KISS.FEND])
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			raise IOError("Could not configure KISS interface preamble to "+str(preamble)+" (command value "+str(preamble)+")")

	def setTxTail(self, txtail):
		#txtail_ms = txtail
		#txtail = int(txtail_ms / 10)
		if txtail < 0:
			txtail = 0
		if txtail > 255:
			txtail = 255

		command = KISS.escape(bytes([txtail]))
		kiss_command = bytes([KISS.FEND])+bytes([KISS.CMD_TXTAIL])+command+bytes([KISS.FEND])
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			raise IOError("Could not configure KISS interface TX tail to "+str(txtail)+" (command value "+str(txtail)+")")

	def setPersistence(self, persistence):
		if persistence < 0:
			persistence = 0
		if persistence > 255:
			persistence = 255

		command = KISS.escape(bytes([persistence]))
		kiss_command = bytes([KISS.FEND])+bytes([KISS.CMD_P])+command+bytes([KISS.FEND])
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			raise IOError("Could not configure KISS interface persistence to "+str(persistence))

	def setSlotTime(self, slottime):
		#slottime_ms = slottime
		#slottime = int(slottime_ms / 10)
		if slottime < 0:
			slottime = 0
		if slottime > 255:
			slottime = 255

		command = KISS.escape(bytes([slottime]))
		kiss_command = bytes([KISS.FEND])+bytes([KISS.CMD_SLOTTIME])+command+bytes([KISS.FEND])
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			raise IOError("Could not configure KISS interface slot time to "+str(slottime)+" (command value "+str(slottime)+")")

	def setFlowControl(self, flow_control):
		command = KISS.escape(bytes([0x01]))
		kiss_command = bytes([KISS.FEND])+bytes([KISS.CMD_READY])+command+bytes([KISS.FEND])
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			if (flow_control):
				raise IOError("Could not enable KISS interface flow control")
			else:
				raise IOError("Could not enable KISS interface flow control")

	def setInputGain(self, gain):
		if gain < 0:
			gain = 0
		if gain > 255:
			gain = 255

		command = KISS.escape(bytes([gain]))
		kiss_command = bytes([KISS.FEND])+bytes([KISS.CMD_INPUT_GAIN])+command+bytes([KISS.FEND])
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			raise IOError("Could not configure KISS interface input gain to "+str(gain))

	def setOutputGain(self, gain):
		if gain < 0:
			gain = 0
		if gain > 255:
			gain = 255

		command = KISS.escape(bytes([gain]))
		kiss_command = bytes([KISS.FEND])+bytes([KISS.CMD_OUTPUT_GAIN])+command+bytes([KISS.FEND])
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			raise IOError("Could not configure KISS interface input gain to "+str(gain))


	def setLEDIntensity(self, val):
		if val < 0:
			val = 0
		if val > 255:
			val = 255

		command = KISS.escape(bytes([val]))
		kiss_command = bytes([KISS.FEND])+bytes([KISS.CMD_LED_INTENSITY])+command+bytes([KISS.FEND])
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			raise IOError("Could not configure KISS interface LED intensity to "+str(val))


	def setGPSMode(self, val):
		if val < 0:
			val = 0
		if val > 2:
			val = 2

		command = KISS.escape(bytes([val]))
		kiss_command = bytes([KISS.FEND])+bytes([KISS.CMD_GPS_MODE])+command+bytes([KISS.FEND])
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			raise IOError("Could not configure KISS interface GPS mode to "+str(val))

	def setBluetoothMode(self, val):
		if val < 0:
			val = 0
		if val > 2:
			val = 2

		command = KISS.escape(bytes([val]))
		kiss_command = bytes([KISS.FEND])+bytes([KISS.CMD_BT_MODE])+command+bytes([KISS.FEND])
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			raise IOError("Could not configure KISS interface BT mode to "+str(val))

	def setBaudrate(self, val):
		if val < 1:
			val = 1
		if val > 12:
			val = 12

		command = KISS.escape(bytes([val]))
		kiss_command = bytes([KISS.FEND])+bytes([KISS.CMD_SERIAL_BAUDRATE])+command+bytes([KISS.FEND])
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			raise IOError("Could not configure KISS interface baudrate to "+str(gain))

	def setPassall(self, val):
		if val < 0:
			val = 0
		if val > 1:
			val = 1

		command = KISS.escape(bytes([val]))
		kiss_command = bytes([KISS.FEND])+bytes([KISS.CMD_PASSALL])+command+bytes([KISS.FEND])
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			raise IOError("Could not configure KISS interface passall to "+str(gain))

	def setLogToSD(self, val):
		if val < 0:
			val = 0
		if val > 1:
			val = 1

		command = KISS.escape(bytes([val]))
		kiss_command = bytes([KISS.FEND])+bytes([KISS.CMD_LOG_PACKETS])+command+bytes([KISS.FEND])
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			raise IOError("Could not configure KISS interface logtosd to "+str(gain))


	def saveConfig(self):
		kiss_command = bytes([KISS.FEND])+bytes([KISS.CMD_SAVE_CONFIG])+bytes([0x01])+bytes([KISS.FEND])
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			raise IOError("Could not send save config command")

	def enableDiagnostics(self):
		kiss_command = bytes([KISS.FEND])+bytes([KISS.CMD_EN_DIAGS])+bytes([0x01])+bytes([KISS.FEND])
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			raise IOError("Could not enable KISS interface diagnostics")

	def retrieveConfig(self):
		kiss_command = bytes([KISS.FEND])+bytes([KISS.CMD_PRINT_CONFIG])+bytes([0x01])+bytes([KISS.FEND])
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			raise IOError("Could not ask for config data")

	def disableDiagnostics(self):
		kiss_command = bytes([KISS.FEND])+bytes([KISS.CMD_EN_DIAGS])+bytes([0x00])+bytes([KISS.FEND])
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			raise IOError("Could not disable KISS interface diagnostics")
			os._exit(0)
			


	def processIncoming(self, data):
		self.has_decode = True
		RNS.log("Decoded packet");

	def processConfig(self, data):
		RNS.log("Processing config")
		md5 = hashlib.md5()
		md5.update(data[:16])
		md5_result = md5.digest()

		if md5_result == data[16:]:
			RNS.log("Config checksum match")
			self.config_p				= data[KISS.ADDR_E_P]
			self.config_slottime 		= data[KISS.ADDR_E_SLOTTIME]
			self.config_preamble 		= data[KISS.ADDR_E_PREAMBLE]
			self.config_tail 			= data[KISS.ADDR_E_TAIL]
			self.config_led_intensity 	= data[KISS.ADDR_E_LED_INTENSITY]
			self.config_output_gain 	= data[KISS.ADDR_E_OUTPUT_GAIN]
			self.config_input_gain 		= data[KISS.ADDR_E_INPUT_GAIN]
			self.config_passall 		= data[KISS.ADDR_E_PASSALL]
			self.config_log_packets 	= data[KISS.ADDR_E_LOG_PACKETS]
			self.config_crypto_lock 	= data[KISS.ADDR_E_CRYPTO_LOCK]
			self.config_gps_mode 		= data[KISS.ADDR_E_GPS_MODE]
			self.config_bluetooth_mode 	= data[KISS.ADDR_E_BLUETOOTH_MODE]
			self.config_serial_baudrate = data[KISS.ADDR_E_SERIAL_BAUDRATE]
			self.config_valid = True
		else:
			print("Invalid checksum")
			self.config_valid = False

	def processOutgoing(self,data):
		pass

	def queue(self, data):
		pass

	def process_queue(self):
		pass

	def readLoop(self):
		try:
			in_frame = False
			escape = False
			command = KISS.CMD_UNKNOWN
			data_buffer = b""
			config_buffer = b""
			last_read_ms = int(time.time()*1000)

			while self.serial.is_open:
				if self.serial.in_waiting:
					byte = ord(self.serial.read(1))
					last_read_ms = int(time.time()*1000)

					if (in_frame and byte == KISS.FEND and command == KISS.CMD_DATA):
						in_frame = False
						self.processIncoming(data_buffer)
					elif (in_frame and byte == KISS.FEND and command == KISS.CMD_PRINT_CONFIG):
						in_frame = False
						self.processConfig(config_buffer)
					elif (byte == KISS.FEND):
						in_frame = True
						command = KISS.CMD_UNKNOWN
						data_buffer = b""
						config_buffer = b""
					elif (in_frame and len(data_buffer) < 611):
						if (len(data_buffer) == 0 and command == KISS.CMD_UNKNOWN):
							command = byte
						elif (command == KISS.CMD_DATA):
							if (byte == KISS.FESC):
								escape = True
							else:
								if (escape):
									if (byte == KISS.TFEND):
										byte = KISS.FEND
									if (byte == KISS.TFESC):
										byte = KISS.FESC
									escape = False
								data_buffer = data_buffer+bytes([byte])
						elif (command == KISS.CMD_PRINT_CONFIG):
							if (byte == KISS.FESC):
								escape = True
							else:
								if (escape):
									if (byte == KISS.TFEND):
										byte = KISS.FEND
									if (byte == KISS.TFESC):
										byte = KISS.FESC
									escape = False
								config_buffer = config_buffer+bytes([byte])
						elif (command == KISS.CMD_AUDIO_PEAK):
							self.displayPeak(byte)
						elif (command == KISS.CMD_MODE):
							self.modem_mode = byte
				else:
					time_since_last = int(time.time()*1000) - last_read_ms
					if len(data_buffer) > 0 and time_since_last > self.timeout:
			 			data_buffer = b""
			 			in_frame = False
			 			command = KISS.CMD_UNKNOWN
			 			escape = False
					sleep(0.2)
					self.askForPeak()

		except Exception as e:
			self.online = False
			RNS.log("A serial port error occurred, the contained exception was: "+str(e))
			RNS.log("The interface "+str(self.name)+" is now offline.")
			raise e
			close_device()

	def __str__(self):
		return "KISSInterface["+self.name+"]"

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
	"""Handle requests threaded via mixin"""

class appRequestHandler(BaseHTTPRequestHandler):
	def log_message(self, format, *args):
		return

	def json_headers(request):
		request.send_response(200)
		request.send_header("Content-Type", "text/json")
		request.end_headers()

	def do_GET(request):
		global kiss_interface, keyfile_exists, entropy_source_exists, aes_disabled

		if (request.path == "/"):
			request.send_response(302)
			request.send_header("Location", "/app/")
			request.end_headers()

		if (request.path == "/favicon.ico"):
			#request.path = "/app/favicon.ico"
			request.send_response(404)

		if (request.path == "/getports"):
			request.json_headers()
			request.wfile.write(json.dumps(list_serial_ports()).encode("utf-8"))

		if (request.path == "/getvolumes"):
			request.json_headers()
			request.wfile.write(json.dumps(list_volumes()).encode("utf-8"))

		if (request.path == "/saveconfig"):
			request.json_headers()
			kiss_interface.saveConfig()
			request.wfile.write(json.dumps({"response":"ok"}).encode("utf-8"))

		if (request.path == "/getconfig"):
			request.json_headers()
			if kiss_interface and kiss_interface.config_valid:
				configData = {
					"preamble": kiss_interface.config_preamble,
					"tail": kiss_interface.config_tail,
					"p": kiss_interface.config_p,
					"slottime": kiss_interface.config_slottime,
					"led_intensity": kiss_interface.config_led_intensity,
					"output_gain": kiss_interface.config_output_gain,
					"input_gain": kiss_interface.config_input_gain,
					"passall": kiss_interface.config_passall,
					"log_packets": kiss_interface.config_log_packets,
					"crypto_lock": kiss_interface.config_crypto_lock,
					"gps_mode": kiss_interface.config_gps_mode,
					"bluetooth_mode": kiss_interface.config_bluetooth_mode,
					"serial_baudrate": kiss_interface.config_serial_baudrate,
					"modem_mode": kiss_interface.modem_mode
				}
				request.wfile.write(json.dumps({"response":"ok", "config":configData}).encode("utf-8"))
			else:
				request.wfile.write(json.dumps({"response":"failed"}).encode("utf-8"))

		if (request.path == "/getpeak"):
			request.json_headers()
			request.wfile.write(json.dumps({"response":"ok", "peak":kiss_interface.audiopeak, "decode": kiss_interface.has_decode}).encode("utf-8"))
			kiss_interface.has_decode = False

		if (request.path.startswith("/disconnect")):
			close_device()

		if (request.path.startswith("/connect")):
			request.json_headers()
			query = parse_qs(urlparse(request.path).query)
			q_port = query["port"][0]
			q_baud = int(query["baud"][0])

			if (open_device(q_port, q_baud)):
				request.wfile.write(json.dumps({"response":"ok"}).encode("utf-8"))
			else:
				request.wfile.write(json.dumps({"response":"failed"}).encode("utf-8"))

		if (request.path.startswith("/volumeinit")):
			request.json_headers()
			query = parse_qs(urlparse(request.path).query)
			q_path = query["path"][0]

			if (volume_init(q_path)):
				request.wfile.write(json.dumps({"response":"ok", "key_installed": keyfile_exists, "aes_disabled":aes_disabled}).encode("utf-8"))
			else:
				request.wfile.write(json.dumps({"response":"failed"}).encode("utf-8"))

		if (request.path.startswith("/setled")):
			request.json_headers()
			query = parse_qs(urlparse(request.path).query)
			q_val = int(query["val"][0])
			kiss_interface.setLEDIntensity(q_val)
			request.wfile.write(json.dumps({"response":"ok"}).encode("utf-8"))

		if (request.path.startswith("/setingain")):
			request.json_headers()
			query = parse_qs(urlparse(request.path).query)
			q_val = int(query["val"][0])
			kiss_interface.setInputGain(q_val)
			request.wfile.write(json.dumps({"response":"ok"}).encode("utf-8"))

		if (request.path.startswith("/setoutgain")):
			request.json_headers()
			query = parse_qs(urlparse(request.path).query)
			q_val = int(query["val"][0])
			kiss_interface.setOutputGain(q_val)
			request.wfile.write(json.dumps({"response":"ok"}).encode("utf-8"))

		if (request.path.startswith("/setpersistence")):
			request.json_headers()
			query = parse_qs(urlparse(request.path).query)
			q_val = int(query["val"][0])
			kiss_interface.setPersistence(q_val)
			request.wfile.write(json.dumps({"response":"ok"}).encode("utf-8"))

		if (request.path.startswith("/setpreamble")):
			request.json_headers()
			query = parse_qs(urlparse(request.path).query)
			q_val = int(query["val"][0])
			kiss_interface.setPreamble(q_val)
			request.wfile.write(json.dumps({"response":"ok"}).encode("utf-8"))

		if (request.path.startswith("/settail")):
			request.json_headers()
			query = parse_qs(urlparse(request.path).query)
			q_val = int(query["val"][0])
			kiss_interface.setTxTail(q_val)
			request.wfile.write(json.dumps({"response":"ok"}).encode("utf-8"))

		if (request.path.startswith("/setslottime")):
			request.json_headers()
			query = parse_qs(urlparse(request.path).query)
			q_val = int(query["val"][0])
			kiss_interface.setSlotTime(q_val)
			request.wfile.write(json.dumps({"response":"ok"}).encode("utf-8"))

		if (request.path.startswith("/setbaudrate")):
			request.json_headers()
			query = parse_qs(urlparse(request.path).query)
			q_val = int(query["val"][0])
			kiss_interface.setBaudrate(q_val)
			request.wfile.write(json.dumps({"response":"ok"}).encode("utf-8"))

		if (request.path.startswith("/setpassall")):
			request.json_headers()
			query = parse_qs(urlparse(request.path).query)
			q_val = int(query["val"][0])
			kiss_interface.setPassall(q_val)
			request.wfile.write(json.dumps({"response":"ok"}).encode("utf-8"))

		if (request.path.startswith("/setlogtosd")):
			request.json_headers()
			query = parse_qs(urlparse(request.path).query)
			q_val = int(query["val"][0])
			kiss_interface.setLogToSD(q_val)
			request.wfile.write(json.dumps({"response":"ok"}).encode("utf-8"))

		if (request.path.startswith("/setgpsmode")):
			request.json_headers()
			query = parse_qs(urlparse(request.path).query)
			q_val = int(query["val"][0])
			kiss_interface.setGPSMode(q_val)
			request.wfile.write(json.dumps({"response":"ok"}).encode("utf-8"))

		if (request.path.startswith("/setbluetoothmode")):
			request.json_headers()
			query = parse_qs(urlparse(request.path).query)
			q_val = int(query["val"][0])
			kiss_interface.setBluetoothMode(q_val)
			request.wfile.write(json.dumps({"response":"ok"}).encode("utf-8"))

		if (request.path == "/aesenable"):
			request.json_headers()
			if aes_enable():
				request.wfile.write(json.dumps({"response":"ok"}).encode("utf-8"))
			else:
				request.wfile.write(json.dumps({"response":"fail"}).encode("utf-8"))

		if (request.path == "/aesdisable"):
			request.json_headers()
			if aes_disable():
				request.wfile.write(json.dumps({"response":"ok"}).encode("utf-8"))
			else:
				request.wfile.write(json.dumps({"response":"fail"}).encode("utf-8"))

		if (request.path == "/generatekey"):
			request.json_headers()
			if generate_key():
				request.wfile.write(json.dumps({"response":"ok"}).encode("utf-8"))
			else:
				request.wfile.write(json.dumps({"response":"fail"}).encode("utf-8"))

		if (request.path.startswith("/loadkey")):
			request.json_headers()
			query = parse_qs(urlparse(request.path).query)
			q_val = query["val"][0]
			if load_key(q_val):
				request.wfile.write(json.dumps({"response":"ok"}).encode("utf-8"))
			else:
				request.wfile.write(json.dumps({"response":"fail"}).encode("utf-8"))
			


		if (request.path.startswith("/app/")):
			path = request.path.replace("/app/", "")
			file = None

			if (path == ""):
				file = "index.html"
			else:
				file = path

			base, extension = os.path.splitext(file)
			request.send_response(200)
			
			if (extension == ".css"):
				request.send_header("Content-Type", "text/css")
			if (extension == ".js"):
				request.send_header("Content-Type", "text/javascript")
			if (extension == ".html"):
				request.send_header("Content-Type", "text/html")

			request.end_headers()

			requestpath = "./public/"+file

			fh = open(requestpath, "rb")
			request.wfile.write(fh.read())
			fh.close()

def list_serial_ports():
	ports = list_ports.comports()
	portlist = []
	for port in ports:
		portlist.insert(0, port.device)

	return portlist

def list_volumes():
	partitions = psutil.disk_partitions()
	volumelist = []
	for partition in partitions:
		if partition.mountpoint != "/" and partition.mountpoint != "C://" and not partition.mountpoint.startswith("/private") and not partition.mountpoint.startswith("/Volumes/Time Machine Backups"):
			RNS.log("Found partition:")
			RNS.log("\t"+str(partition))
			volumelist.append(partition.mountpoint)

	return volumelist

def open_device(port, baud):
	global kiss_interface
	try:
		kiss_interface = KISSInterface(None, "OpenModem", port, baud, 8, "N", 1, None, None, None, None, False)
		kiss_interface.enableDiagnostics()
		kiss_interface.retrieveConfig()
		return True
	except Exception as e:
		return False

def close_device():
	os._exit(0)

keyfile_exists = False
entropy_source_exists = False
aes_disabled = False
volume_ok = False
volume_path = None
def volume_init(path):
	global keyfile_exists, entropy_source_exists, volume_ok, volume_path, aes_disabled

	volume_ok = False
	RNS.log("Volume init: "+path)

	if os.path.isdir(path+"/OpenModem"):
		RNS.log("OpenModem data directory exists")
	else:
		RNS.log("OpenModem data directory does not exist, creating")
		try:
			os.mkdir(path+"/OpenModem")
			RNS.log("Directory created")
		except Exception as e:
			RNS.log("Could not create directory")
			volume_ok = False
			return False

	if os.path.isfile(path+"/OpenModem/entropy.source"):
		entropy_source_exists = True
		RNS.log("Entropy source installed")
	else:
		RNS.log("Entropy source is not installed, installing...")
		if install_entropy_source(path+"/OpenModem/"):
			entropy_source_exists = True
		else:
			entropy_source_exists = False

	if os.path.isfile(path+"/OpenModem/aes128.key"):
		keyfile_exists = True
		RNS.log("AES-128 key installed")
	else:
		RNS.log("AES-128 key is not installed")
		keyfile_exists = False

	if os.path.isfile(path+"/OpenModem/aes128.disable"):
		aes_disabled = True
		RNS.log("AES-128 is disabled")
	else:
		RNS.log("AES-128 is allowed")
		aes_disabled = False

	volume_ok = True
	volume_path = path + "/OpenModem/"
	RNS.log("Volume path is "+volume_path)
	return True

def generate_key():
	global volume_ok, volume_path
	if volume_ok:
		RNS.log("Generating new AES-128 key in "+volume_path+"...")
		try:
			file = open(volume_path+"aes128.key", "w")
			file.write(os.urandom(128/8))
			file.close()

			return True
		except Exception as e:
			RNS.log("Could not generate key")
			return False

def load_key(keydata):
	global volume_ok, volume_path
	if volume_ok:
		RNS.log("Loading supplied key onto "+volume_path+"...")
		try:
			key = base64.b64decode(keydata)
			file = open(volume_path+"aes128.key", "w")
			file.write(key)
			file.close()
			return True
		except Exception as e:
			raise e
			return False
	else:
		return False


def aes_disable():
	global volume_ok, volume_path
	if volume_ok:
		open(volume_path+"aes128.disable", 'a').close()
		RNS.log("Disabling AES-128")
		return True

	return False

def aes_enable():
	global volume_ok, volume_path
	if volume_ok:
		if os.path.isfile(volume_path+"aes128.disable"):
			os.remove(volume_path+"aes128.disable")
			RNS.log("Allowing AES-128")
			return True

	return False


def install_entropy_source(path):
	RNS.log("Installing entropy source in "+path+"...")
	try:
		megabytes_to_write = 32
		bytes_per_block = 1024
		bytes_written = 0
		file = open(path+"entropy.source", "a")
		while bytes_written < megabytes_to_write*1024*1024:
			file.write(os.urandom(bytes_per_block))
			bytes_written = bytes_written + bytes_per_block
		file.close()

		return True
	except Exception as e:
		RNS.log("Could not install entropy source")
		return False


def get_port():
	# TODO: Change
	#return random.randrange(40000,49999,1)
	return 48031

def start_server():
	retries = 0
	server_started = False

	while not server_started and retries < 100:
		try:
			list_serial_ports()
			port = get_port()
			server_address = ("127.0.0.1", port)
			httpd = ThreadedHTTPServer(server_address, appRequestHandler)
			threading.Thread(target=httpd.serve_forever).start()
			print(("Server running on port "+str(port)))
			retval = webview.create_window('OpenModem Configuration', 'http://localhost:'+str(port)+'/', width=575, height=600)
			if retval == None:
				os._exit(0)

		except Exception as e:
			retries += 1

	print("Could not start server, exiting")
	exit()


def main():
	include_path = os.path.dirname(os.path.realpath(sys.argv[0]))
	os.chdir(include_path)
	list_serial_ports()
	list_volumes()
	if (len(sys.argv) == 1):
		start_server()

if __name__ == "__main__":
	main()