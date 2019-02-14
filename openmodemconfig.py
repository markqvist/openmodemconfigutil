import serial
from serial.tools import list_ports
import requests
import json
import time
import struct
from time import sleep
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from SocketServer import ThreadingMixIn
from urlparse import urlparse, parse_qs
import threading
import webview
import random
import os
import sys

portlist = []
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
		hexrep = delimiter.join("{:02x}".format(ord(c)) for c in data)
		return hexrep

	@staticmethod
	def prettyhexrep(data):
		delimiter = ""
		hexrep = "<"+delimiter.join("{:02x}".format(ord(c)) for c in data)+">"
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
	FEND			= chr(0xC0)
	FESC			= chr(0xDB)
	TFEND			= chr(0xDC)
	TFESC			= chr(0xDD)
	CMD_UNKNOWN		= chr(0xFE)
	CMD_DATA		= chr(0x00)
	CMD_TXDELAY		= chr(0x01)
	CMD_P			= chr(0x02)
	CMD_SLOTTIME	= chr(0x03)
	CMD_TXTAIL		= chr(0x04)
	CMD_FULLDUPLEX	= chr(0x05)
	CMD_SETHARDWARE	= chr(0x06)
	CMD_READY       = chr(0x0F)
	CMD_AUDIO_PEAK  = chr(0x12)
	CMD_OUTPUT_GAIN = chr(0x09)
	CMD_INPUT_GAIN  = chr(0x0A)
	CMD_EN_DIAGS    = chr(0x13)
	CMD_RETURN		= chr(0xFF)

	@staticmethod
	def escape(data):
		data = data.replace(chr(0xdb), chr(0xdb)+chr(0xdd))
		data = data.replace(chr(0xc0), chr(0xdb)+chr(0xdc))
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
			sleep(1.5)
			thread = threading.Thread(target=self.readLoop)
			thread.setDaemon(True)
			thread.start()
			self.online = True
			RNS.log("Serial port "+self.port+" is now open")
			self.interface_ready = True
			RNS.log("KISS interface configured")
		else:
			raise IOError("Could not open serial port")


	def askForPeak(self):
		kiss_command = KISS.FEND+KISS.CMD_AUDIO_PEAK+b'\x01'+KISS.FEND
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			raise IOError("Could not ask for peak data")

	def displayPeak(self, peak):
		peak_value = struct.unpack("b", peak)
		self.audiopeak = peak_value[0]

	def setPreamble(self, preamble):
		preamble_ms = preamble
		preamble = int(preamble_ms / 10)
		if preamble < 0:
			preamble = 0
		if preamble > 255:
			preamble = 255

		RNS.log("Setting preamble to "+str(preamble)+" "+chr(preamble))
		kiss_command = KISS.FEND+KISS.CMD_TXDELAY+chr(preamble)+KISS.FEND
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			raise IOError("Could not configure KISS interface preamble to "+str(preamble_ms)+" (command value "+str(preamble)+")")

	def setTxTail(self, txtail):
		txtail_ms = txtail
		txtail = int(txtail_ms / 10)
		if txtail < 0:
			txtail = 0
		if txtail > 255:
			txtail = 255

		kiss_command = KISS.FEND+KISS.CMD_TXTAIL+chr(txtail)+KISS.FEND
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			raise IOError("Could not configure KISS interface TX tail to "+str(txtail_ms)+" (command value "+str(txtail)+")")

	def setPersistence(self, persistence):
		if persistence < 0:
			persistence = 0
		if persistence > 255:
			persistence = 255

		kiss_command = KISS.FEND+KISS.CMD_P+chr(persistence)+KISS.FEND
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			raise IOError("Could not configure KISS interface persistence to "+str(persistence))

	def setSlotTime(self, slottime):
		slottime_ms = slottime
		slottime = int(slottime_ms / 10)
		if slottime < 0:
			slottime = 0
		if slottime > 255:
			slottime = 255

		kiss_command = KISS.FEND+KISS.CMD_SLOTTIME+chr(slottime)+KISS.FEND
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			raise IOError("Could not configure KISS interface slot time to "+str(slottime_ms)+" (command value "+str(slottime)+")")

	def setFlowControl(self, flow_control):
		kiss_command = KISS.FEND+KISS.CMD_READY+chr(0x01)+KISS.FEND
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

		kiss_command = KISS.FEND+KISS.CMD_INPUT_GAIN+chr(gain)+KISS.FEND
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			raise IOError("Could not configure KISS interface input gain to "+str(gain))

	def setOutputGain(self, gain):
		if gain < 0:
			gain = 0
		if gain > 255:
			gain = 255

		kiss_command = KISS.FEND+KISS.CMD_OUTPUT_GAIN+chr(gain)+KISS.FEND
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			raise IOError("Could not configure KISS interface input gain to "+str(gain))


	def enableDiagnostics(self):
		kiss_command = KISS.FEND+KISS.CMD_EN_DIAGS+chr(0x01)+KISS.FEND
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			raise IOError("Could not enable KISS interface diagnostics")

	def disableDiagnostics(self):
		kiss_command = KISS.FEND+KISS.CMD_EN_DIAGS+chr(0x00)+KISS.FEND
		written = self.serial.write(kiss_command)
		if written != len(kiss_command):
			raise IOError("Could not disable KISS interface diagnostics")
			os._exit(0)
			


	def processIncoming(self, data):
		self.has_decode = True
		RNS.log("Decoded packet");


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
			data_buffer = ""
			last_read_ms = int(time.time()*1000)

			while self.serial.is_open:
				if self.serial.in_waiting:
					byte = self.serial.read(1)
					last_read_ms = int(time.time()*1000)

					if (in_frame and byte == KISS.FEND and command == KISS.CMD_DATA):
						in_frame = False
						self.processIncoming(data_buffer)
					elif (byte == KISS.FEND):
						in_frame = True
						command = KISS.CMD_UNKNOWN
						data_buffer = ""
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
								data_buffer = data_buffer+byte
						elif (command == KISS.CMD_AUDIO_PEAK):
							self.displayPeak(byte)
				else:
					time_since_last = int(time.time()*1000) - last_read_ms
					if len(data_buffer) > 0 and time_since_last > self.timeout:
			 			data_buffer = ""
			 			in_frame = False
			 			command = KISS.CMD_UNKNOWN
			 			escape = False
					sleep(0.2)
					self.askForPeak()

		except Exception as e:
			self.online = False
			RNS.log("A serial port error occurred, the contained exception was: "+str(e))
			RNS.log("The interface "+str(self.name)+" is now offline. Restart Reticulum to attempt reconnection.")
			raise e

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

		if (request.path == "/getconfig"):
			request.json_headers()
			request.wfile.write(json.dumps({"response":"ok"}).encode("utf-8"))

		if (request.path == "/getpeak"):
			global kiss_interface
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

def open_device(port, baud):
	global kiss_interface
	try:
		kiss_interface = KISSInterface(None, "OpenModem", port, baud, 8, "N", 1, None, None, None, None, False)
		kiss_interface.enableDiagnostics()
		kiss_interface.setInputGain(200)
		return True
	except Exception as e:
		#raise e
		return False

def close_device():
	os._exit(0)

def get_port():
	return 44444
	return random.randrange(40000,49999,1)

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
			print("Server running on port "+str(port))
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
	ports = list_serial_ports()
	print(ports)
	if (len(sys.argv) == 1):
		start_server()

if __name__ == "__main__":
	main()