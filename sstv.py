#!/usr/bin/env python

from __future__ import division, with_statement
from math import sin, pi
from random import random
import struct

FREQ_VIS_BIT1 = 1100
FREQ_SYNC = 1200
FREQ_VIS_BIT0 = 1300
FREQ_BLACK = 1500
FREQ_VIS_START = 1900
FREQ_WHITE = 2300
FREQ_RANGE = FREQ_WHITE - FREQ_BLACK

MSEC_VIS_START = 300
MSEC_VIS_SYNC = 10
MSEC_VIS_BIT = 30

class SSTV(object):
	def __init__(self, image, samples_per_sec, bits):
		self.image = image
		self.samples_per_sec = samples_per_sec
		self.bits = bits

	BITS_TO_STRUCT = {8: 'b', 16: 'h'}
	def write_wav(self, filename):
		bytes_per_sec = self.bits // 8
		fmt = '<' + self.BITS_TO_STRUCT[self.bits]
		data = ''.join(struct.pack(fmt, b) for b in self.gen_samples())
		payload = ''.join((
				'WAVE',
				'fmt ',
				struct.pack('<IHHIIHH', 16, 1, 1, self.samples_per_sec,
					self.samples_per_sec * bytes_per_sec, bytes_per_sec,
					self.bits),
				'data',
				struct.pack('<I', len(data))
				))
		header = 'RIFF' + struct.pack('<I', len(payload) + len(data))
		with file(filename, 'wb') as wav:
			wav.write(header)
			wav.write(payload)
			wav.write(data)

	def gen_samples(self):
		"""generates bits from gen_values"""
		max_value = 2 ** self.bits
		alias = 1 / max_value
		amp = max_value / 2
		lowest = -amp
		highest = amp - 1
		for value in self.gen_values():
			sample = int(round(value * amp + alias * (random() - 0.5)))
			yield max(min(highest, sample), lowest)

	def gen_values(self):
		"""generates -1 .. +1 values from freq_bits"""
		spms = self.samples_per_sec / 1000
		param = 0
		for freq, msec in self.gen_freq_bits():
			offset = param
			for sample in xrange(int(round(spms * msec))):
				t = sample / self.samples_per_sec
				param = t * freq * 2 * pi + offset
				yield sin(param)

	def gen_freq_bits(self):
		"""generates (freq, msec) tuples from image"""
		yield FREQ_VIS_START, MSEC_VIS_START
		yield FREQ_SYNC, MSEC_VIS_SYNC
		yield FREQ_VIS_START, MSEC_VIS_START
		yield FREQ_SYNC, MSEC_VIS_BIT # start bit
		vis = self.VIS_CODE
		num_ones = 0
		for _ in xrange(7):
			bit = vis & 1
			vis >>= 1
			num_ones += bit
			bit_freq = FREQ_VIS_BIT1 if bit == 1 else FREQ_VIS_BIT0
			yield bit_freq, MSEC_VIS_BIT
		parity_freq = FREQ_VIS_BIT1 if num_ones % 2 == 1 else FREQ_VIS_BIT0
		yield parity_freq, MSEC_VIS_BIT
		yield FREQ_SYNC, MSEC_VIS_BIT # stop bit


class GrayscaleSSTV(SSTV):
	def gen_freq_bits(self):
		for item in SSTV.gen_freq_bits(self):
			yield item
		for line in xrange(self.HEIGHT):
			for item in self.horizontal_sync():
				yield item
			for item in self.encode_line(line):
				yield item

	def horizontal_sync(self):
		yield FREQ_SYNC, self.SYNC

	def encode_line(self, line):
		msec_pixel = self.SCAN / self.WIDTH
		image = self.image
		for col in xrange(self.WIDTH):
			pixel = image.getpixel((col, line))
			value = sum(pixel) / len(pixel)
			freq_pixel = FREQ_BLACK + FREQ_RANGE * value / 255
			yield freq_pixel, msec_pixel


class ColorSSTV(GrayscaleSSTV):
	RED, GREEN, BLUE = range(3)

	def encode_line(self, line):
		cs = self.COLOR_SEQ
		msec_pixel = self.SCAN / self.WIDTH
		image = self.image
		for index in cs:
			for item in self.before_channel(index):
				yield item
			for col in xrange(self.WIDTH):
				pixel = image.getpixel((col, line))
				value = pixel[index]
				freq_pixel = FREQ_BLACK + FREQ_RANGE * value / 255
				yield freq_pixel, msec_pixel

	def before_channel(self, index):
		return []


class Robot8BW(GrayscaleSSTV):
	VIS_CODE = 0x02
	WIDTH = 160
	HEIGHT = 120
	SYNC = 10
	SCAN = 56


class Robot24BW(GrayscaleSSTV):
	VIS_CODE = 0x0A
	WIDTH = 320
	HEIGHT = 240
	SYNC = 12
	SCAN = 93


class MartinM1(ColorSSTV):
	COLOR_SEQ = (ColorSSTV.GREEN, ColorSSTV.BLUE, ColorSSTV.RED)
	VIS_CODE = 0x2c
	WIDTH = 320
	HEIGHT = 256
	SYNC = 4.862
	SCAN = 146.432
	INTER_CH_GAP = 0.572

	def before_channel(self, index):
		if index != ColorSSTV.GREEN:
			yield FREQ_BLACK, self.INTER_CH_GAP


class MartinM2(MartinM1):
	VIS_CODE = 0x28
	WIDTH = 160
	SCAN = 73.216


class ScottieS1(MartinM1):
	VIS_CODE = 0x3c
	SYNC = 9
	SCAN = 138.24
	INTER_CH_GAP = 1.5

	def horizontal_sync(self):
		return []

	def before_channel(self, index):
		if index != ColorSSTV.RED:
			yield FREQ_SYNC, self.SYNC
		yield FREQ_BLACK, self.INTER_CH_GAP


class ScottieS2(ScottieS1):
	VIS_CODE = 0x38
	SCAN = 88.064
	WIDTH = 160


if __name__ == '__main__':
	from PIL import Image
	image = Image.open('160x120bw.png')
	s = Robot8BW(image, 48000, 16)
	s.write_wav('test.wav')
