#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

from fractions import Fraction

class exif:
	"""Pretty minimal TIFF container parser.
	Uses EXIF (0x8769) instead of normal subifd (0x14a)."""
	
	def __init__(self, fh):
		from struct import unpack, pack
		self._fh = fh
		d = fh.read(4)
		if d not in ("II*\0", "MM\0*"): raise Exception("Not TIFF")
		endian = {"M": ">", "I": "<"}[d[0]]
		self._up = lambda fmt, *a: unpack(endian + fmt, *a)
		self._up1 = lambda *a: self._up(*a)[0]
		self._pack = lambda fmt, *a: pack(endian + fmt, *a)
		next_ifd = self._up1("I", fh.read(4))
		self.reinit_from(next_ifd)
	
	def reinit_from(self, next_ifd):
		self.ifd = []
		while next_ifd:
			self.ifd.append(self._ifdread(next_ifd))
			next_ifd = self._up1("I", self._fh.read(4))
		self.subifd = []
		subifd = self.ifdget(self.ifd[0], 0x8769) or []
		for next_ifd in subifd:
			self.subifd.append(self._ifdread(next_ifd))
	
	def ifdget(self, ifd, tag):
		if tag in ifd:
			type, vc, off = ifd[tag]
			print "get",ifd[tag]
			if type in (3, 4): # SHORT or LONG
				if vc == 1: return (off,)
				self._fh.seek(off)
				dt = {3: "H", 4: "I"}[type]
				return self._up(dt * vc, self._fh.read(4 * vc))
			elif type == 2: # STRING
				self._fh.seek(off)
				return self._fh.read(vc).rstrip("\0")
			elif type == 5: # rational
				self._fh.seek(off)
				print self._up("II", self._fh.read(8))
				self._fh.seek(off)
				return Fraction(*self._up("II", self._fh.read(8)))
	
	def get(self, tag):
		return self.ifdget(self.subifd[0], tag)
	
	def _ifdread(self, next_ifd):
		ifd = {}
		self._fh.seek(next_ifd)
		count = self._up1("H", self._fh.read(2))
		for i in range(count):
			d = self._fh.read(12)
			tag, type, vc = self._up("HHI", d[:8])
			if type == 3 and vc == 1:
				off = self._up1("H", d[8:10])
			else:
				off = self._up1("I", d[8:])
			ifd[tag] = (type, vc, off)
		return ifd
	
	def write(self, offset, fmt, *data):
		data = self._pack(fmt, *data)
		self._fh.seek(offset)
		self._fh.write(data)

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
exif = exif(fh)
print exif.get(0x829d)
print repr(exif.get(0x920a))
print exif.get(0xa405)
if 0x829d not in exif.subifd[0] or exif.subifd[0][0x829d][:2] != (5, 1):
	print "Warning: No/bad FNumber"
else:
	exif.write(exif.subifd[0][0x829d][2], "II", 18, 5)

# 0x829d FNumber
# 0x9202 ApertureValue (doesn't seem to be set?)
# 0x920a FocalLength
# 0xa405 FocalLengthIn35mmFormat
