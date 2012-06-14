#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

from tiff import tiff

class jpeg_wrapper:
	"""Pretend to be a file that can only access the EXIF portion of a JPEG"""
	
	def __init__(self, fh):
		from struct import unpack
		data = fh.read(3)
		if data != "\xff\xd8\xff": raise Exception("Not JPEG")
		data = fh.read(9)
		while data and data[3:7] != "Exif":
			l = unpack(">H", data[1:3])[0]
			fh.seek(l - 7, 1)
			data = fh.read(9)
		if not data: raise Exception("No EXIF")
		l = unpack(">H", data[1:3])[0]
		pos = fh.tell()
		self.start = pos
		self.stop = pos + l
		self.fh = fh
	
	def read(self, size=-1):
		if size < 0: size = self.stop - self.fh.tell()
		if size <= 0: return ""
		return self.fh.read(size)
	
	def tell(self):
		return self.fh.tell() - self.start
	
	def seek(self, pos, whence=0):
		if whence == 0:
			pos = min(pos + self.start, self.stop)
		elif whence == 1:
			pos = self.fh.tell() + pos
			pos = max(min(pos, self.stop), self.start)
		else:
			raise Exception("Sorry, no from-end support")
		return self.fh.seek(pos)
	
	def write(self, data):
		left = self.stop - self.fh.tell()
		if len(data) > left: raise Exception("Overflow")
		return self.fh.write(data)

fh = open("/tmp/test.jpg", "rb+")
fh = jpeg_wrapper(fh)
exif = tiff(fh, 0x8769)
print exif.subget(0, 0x829d)
print repr(exif.subget(0, 0x920a))
print exif.subget(0, 0xa405)
if 0x829d not in exif.subifd[0] or exif.subifd[0][0x829d][:2] != (5, 1):
	print "Warning: No/bad FNumber"
else:
	exif.write(exif.subifd[0][0x829d][2], "II", 18, 5)

# 0x829d FNumber
# 0x9202 ApertureValue (doesn't seem to be set?)
# 0x920a FocalLength
# 0xa405 FocalLengthIn35mmFormat
