#!/usr/bin/env python

import socket
import pigpio
import json
import irrp

GPIO_PLAYBACK = 22 # GPIO pin that's connected to transmitter LED
GPIO_RECORD = 23 # GPIO pin that's connected to decoder pin on IR recorder
class skill_server():
	clientsocket = None
	serversocket = None
	pi = None
	ir = None
	file = None
	setupfile = None
	records = None
	message_length = None

	def __init__(self, port, file='remote_codes.txt', setupfile='code_names.txt'):
		self.message_length = 4096
		self.serversocket = socket.socket()
		self.serversocket.bind(('', port))
		self.serversocket.listen(5)
		self.pi = pigpio.pi() # Connect to Pi.
		if not self.pi.connected:
			print("pi not connected to pigpio")
			exit(0)
		self.ir = irrp.irrp(self.pi, file)
		self.file = file
		self.scan_records()
		self.setupfile = setupfile
		self.pi.set_mode(GPIO_PLAYBACK, pigpio.OUTPUT) # IR TX connected to this GPIO.

	def __del__(self):
		self.pi.stop() # Disconnect from Pi.

	# sets self.records according to file
	def scan_records(self):
		try:
			f = open(self.file, "r")
		except:
			print("Can't open: {}".format(self.file))
			exit(0)
		self.records = json.load(f)
		f.close()

	# receive data until \n encountered, return False on error
	def __recieve_data(self):
		if( self.clientsocket ):
			received_data = ""
			bytes_received = 0
			while "\n" not in received_data:
				chunk = self.clientsocket.recv(min(self.message_length - bytes_received, 2048))
				if(chunk is b''):
					return False
				received_data += chunk.decode('utf8')
				bytes_received += len(chunk)
			return received_data[:-1] # splicing to get rid of delimiter
		return False

	#  not actually called as of v1
	# receives a series of transmissions with names to use for codes
	# returns list of names
	def __receive_code_names(self):
		print("receive code names")
		code_names = []
		receiving_codes = True
		while receiving_codes:
			self.set_client_socket()
			d = self.__recieve_data()
			print(d)
			if("finished" in  d):
				receiving_codes = False
			code_names.append(d)
		return code_names

	# read names from self.setupfile, return list 
	def __read_setup_code_names(self):
		try:
			with open(self.setupfile, "r") as f:
				code_names = f.readlines()
		except:
			print("Can't open: {}".format(self.setupfile))
			exit(0)
		return code_names
	
	# sets self.clientsocket if it's broken
	def set_client_socket(self):
		if( not self.clientsocket ):
			(self.clientsocket, address) = self.serversocket.accept()

	# begins recording process for all codes specified in code_names
	def setup(self, code_names):
		print("setup")
		self.pi.set_mode(GPIO_RECORD, pigpio.OUTPUT) # IR TX connected to this GPIO.
		for c in code_names:
			self.ir.record(c)
		self.scan_records()
		self.pi.set_mode(GPIO_PLAYBACK, pigpio.OUTPUT) # IR TX connected to this GPIO.

	def listen_infinitely(self):
		while True:
			self.set_client_socket()
			data = self.__recieve_data()
			print(data)
			if("setup" in data):
				code_names = self.__read_setup_code_names()
				self.setup(code_names)
			else:
				try:
					decoded_command = self.records[data]
					self.ir.play_code(decoded_command)
				except:
					print('unrecognized command:' + data)
