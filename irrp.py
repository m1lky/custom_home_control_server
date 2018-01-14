#!/usr/bin/env python

# irrp.py
# Public Domain
# InfraRed Handling Functions Source: http://abyz.me.uk/rpi/pigpio/examples.html
# Modified into a class by James Hebert

import time
import json
import os
import pigpio # http://abyz.co.uk/rpi/pigpio/python.html

GPIO       = 22 # which GPIO pin to use (default listen 22)
GLITCH     = 100 # glitch in microseconds
PRE_MS     = 200 # preamble milliseconds
POST_MS    = 15 # postamble milliseconds
FREQ       = 38.0 # frequency in kHz (most remotes are 38kHz)
VERBOSE    = False # verbose setting, for debugging
SHORT      = 10 # threshold to consider a code "too short",
# and thus is an erroroneous code
GAP_MS     = 100 # gap between keys broadcast by the remote, in ms
NO_CONFIRM = False # only press the key once
TOLERANCE  = 15 # percentage of tolerance

POST_US    = POST_MS * 1000
PRE_US     = PRE_MS  * 1000
GAP_S      = GAP_MS  / 1000.0
CONFIRM    = not NO_CONFIRM
TOLER_MIN =  (100 - TOLERANCE) / 100.0
TOLER_MAX =  (100 + TOLERANCE) / 100.0


class irrp():
	pi = None
	last_tick = 0
	in_code = False
	code = []
	fetching_code = False
	records = {}
	file = None
	def __init__(self, pigpio_instance, file):
		self.pi = pigpio_instance
		try:
			f = open(self.file, "r")
			self.records = json.load(f)
			f.close()
		except:
			print("No Current Records Found")

	def backup(self, f):
		"""
		f -> f.bak -> f.bak1 -> f.bak2
		"""
		try:
			os.rename(os.path.realpath(f)+".bak1", os.path.realpath(f)+".bak2")
		except:
			pass

		try:
			os.rename(os.path.realpath(f)+".bak", os.path.realpath(f)+".bak1")
		except:
			pass

		try:
			os.rename(os.path.realpath(f), os.path.realpath(f)+".bak")
		except:
			pass

	def carrier(self, gpio, frequency, micros):
		"""
		Generate carrier square wave.
		"""
		wf = []
		cycle = 1000.0 / frequency
		cycles = int(round(micros/cycle))
		on = int(round(cycle / 2.0))
		sofar = 0
		for c in range(cycles):
			target = int(round((c+1)*cycle))
			sofar += on
			off = target - sofar
			sofar += off
			wf.append(pigpio.pulse(1<<gpio, 0, on))
			wf.append(pigpio.pulse(0, 1<<gpio, off))
		return wf


	def normalise(self):
		"""
		Typically a code will be made up of two or three distinct
		marks (carrier) and spaces (no carrier) of different lengths.

		Because of transmission and reception errors those pulses
		which should all be x micros long will have a variance around x.

		This function identifies the distinct pulses and takes the
		average of the lengths making up each distinct pulse.  Marks
		and spaces are processed separately.

		This makes the eventual generation of waves much more efficient.

		Input

		  M    S   M   S   M   S   M    S   M    S   M
		9000 4500 600 540 620 560 590 1660 620 1690 615

		Distinct marks

		9000                average 9000
		600 620 590 620 615 average  609

		Distinct spaces

		4500                average 4500
		540 560             average  550
		1660 1690           average 1675

		Output

		  M    S   M   S   M   S   M    S   M    S   M
		9000 4500 609 550 609 550 609 1675 609 1675 609
		"""
		if VERBOSE:
			print("before normalise", self.code)
		entries = len(self.code)
		p = [0]*entries # Set all entries not processed.
		for i in range(entries):
			if not p[i]: # Not processed?
				v = self.code[i]
				tot = v
				similar = 1.0

				# Find all pulses with similar lengths to the start pulse.
				for j in range(i+2, entries, 2):
					if not p[j]: # Unprocessed.
						if (self.code[j]*TOLER_MIN) < v < (self.code[j]*TOLER_MAX): # Similar.
							tot = tot + self.code[j]
							similar += 1.0

				# Calculate the average pulse length.
				newv = round(tot / similar, 2)
				self.code[i] = newv

				# Set all similar pulses to the average value.
				for j in range(i+2, entries, 2):
					if not p[j]: # Unprocessed.
						if (self.code[j]*TOLER_MIN) < v < (self.code[j]*TOLER_MAX): # Similar.
							self.code[j] = newv
							p[j] = 1

		if VERBOSE:
			print("after normalise", c)

	def compare(self, p1, p2):
		"""
		Check that both recodings correspond in pulse length to within
		TOLERANCE%.  If they do average the two recordings pulse lengths.

		Input

			  M    S   M   S   M   S   M    S   M    S   M
		1: 9000 4500 600 560 600 560 600 1700 600 1700 600
		2: 9020 4570 590 550 590 550 590 1640 590 1640 590

		Output

		A: 9010 4535 595 555 595 555 595 1670 595 1670 595
		"""
		if len(p1) != len(p2):
			return False

		for i in range(len(p1)):
			v = p1[i] / p2[i]
			if (v < TOLER_MIN) or (v > TOLER_MAX):
				return False

		for i in range(len(p1)):
			 p1[i] = int(round((p1[i]+p2[i])/2.0))

		if VERBOSE:
			print("after compare", p1)

		return True


	def tidy_mark_space(self, base):

		ms = {}

		# Find all the unique marks (base=0) or spaces (base=1)
		# and count the number of times they appear,

		for rec in self.records:
			rl = len(self.records[rec])
			for i in range(base, rl, 2):
				if self.records[rec][i] in ms:
					ms[self.records[rec][i]] += 1
				else:
					ms[self.records[rec][i]] = 1
		
		if VERBOSE:
			print("t_m_s A", ms)

		v = None

		for plen in sorted(ms):

			# Now go through in order, shortest first, and collapse
			# pulses which are the same within a tolerance to the
			# same value.  The value is the weighted average of the
			# occurences.
			#
			# E.g. 500x20 550x30 600x30  1000x10 1100x10  1700x5 1750x5
			#
			# becomes 556(x80) 1050(x20) 1725(x10)
			#       
			if v == None:
				e = [plen]
				v = plen
				tot = plen * ms[plen]
				similar = ms[plen]

			elif plen < (v*TOLER_MAX):
				e.append(plen)
				tot += (plen * ms[plen])
				similar += ms[plen]

			else:
				v = int(round(tot/float(similar)))
				# set all previous to v
				for i in e:
					ms[i] = v
				e = [plen]
				v = plen
				tot = plen * ms[plen]
				similar = ms[plen]

		v = int(round(tot/float(similar)))
		# set all previous to v
		for i in e:
			ms[i] = v

		if VERBOSE:
			print("t_m_s B", ms)

		for rec in self.records:
			rl = len(self.records[rec])
			for i in range(base, rl, 2):
				self.records[rec][i] = ms[self.records[rec][i]]


	def tidy(self):

		self.tidy_mark_space(0) # Marks.

		self.tidy_mark_space(1) # Spaces.

	
	def end_of_code(self):
		if len(self.code) > SHORT:
			self.normalise()
			self.fetching_code = False
		else:
			self.code = []
			print("Short code, probably a repeat, try again")

	def cbf(self, gpio, level, tick):

		if level != pigpio.TIMEOUT:
			
			edge = pigpio.tickDiff(self.last_tick, tick)
			self.last_tick = tick

			if self.fetching_code:

				if (edge > PRE_US) and (not self.in_code): # Start of a code.
					self.in_code = True
					self.pi.set_watchdog(GPIO, POST_MS) # Start watchdog.

				elif (edge > POST_US) and self.in_code: # End of a code.
					self.in_code = False
					self.pi.set_watchdog(GPIO, 0) # Cancel watchdog.
					end_of_code()

				elif self.in_code:
					self.code.append(edge)

		else:
			self.pi.set_watchdog(GPIO, 0) # Cancel watchdog.
			if self.in_code:
				self.in_code = False
				self.end_of_code()

	def record(self, arg):
		self.pi.set_mode(GPIO, pigpio.INPUT) # IR RX connected to this GPIO.

		self.pi.set_glitch_filter(GPIO, GLITCH) # Ignore glitches.

		cb = self.pi.callback(GPIO, pigpio.EITHER_EDGE, self.cbf)
		
		self.code = []
		self.fetching_code = True
		while self.fetching_code:
			time.sleep(0.1)
		print("Okay")
		time.sleep(0.5)

		if CONFIRM:
			press_1 = self.code[:]
			done = False

			tries = 0
			while not done:
				# print("Press key for '{}' to confirm".format(arg))
				self.code = []
				self.fetching_code = True
				while self.fetching_code:
					time.sleep(0.1)
				press_2 = self.code[:]
				the_same = self.compare(press_1, press_2)
				if the_same:
					done = True
					self.records[arg] = press_1[:]
					print("Okay")
					time.sleep(0.5)
				else:
					tries += 1
					if tries <= 3:
						print("No match")
					else:
						print("Giving up on key '{}'".format(arg))
						done = True
					time.sleep(0.5)
		else: # No confirm.
			self.records[arg] = self.code[:]

		self.pi.set_glitch_filter(GPIO, 0) # Cancel glitch filter.
		self.pi.set_watchdog(GPIO, 0) # Cancel watchdog.

		self.tidy()

		self.backup(self.file)

		f = open(self.file, "w")
		f.write(json.dumps(self.records, sort_keys=True).replace("],", "],\n")+"\n")
		f.close()

	def play_code(self, code):
		self.pi.wave_add_new()

		emit_time = time.time()

		# Create wave

		marks_wid = {}
		spaces_wid = {}

		wave = [0]*len(code)

		for i in range(0, len(code)):
			ci = code[i]
			if i & 1: # Space
				if ci not in spaces_wid:
					self.pi.wave_add_generic([pigpio.pulse(0, 0, ci)])
					spaces_wid[ci] = self.pi.wave_create()
				wave[i] = spaces_wid[ci]
			else: # Mark
				if ci not in marks_wid:
					wf = self.carrier(GPIO, FREQ, ci)
					self.pi.wave_add_generic(wf)
					marks_wid[ci] = self.pi.wave_create()
				wave[i] = marks_wid[ci]

		delay = emit_time - time.time()

		if delay > 0.0:
			time.sleep(delay)

		self.pi.wave_chain(wave)

		if VERBOSE:
			print("key " + arg)

		while self.pi.wave_tx_busy():
			time.sleep(0.002)

		emit_time = time.time() + GAP_S

		for i in marks_wid:
			self.pi.wave_delete(marks_wid[i])

		for i in spaces_wid:
			self.pi.wave_delete(spaces_wid[i])



	



