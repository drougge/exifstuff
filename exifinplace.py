#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

from fractions import Fraction

class tiff:
	"""Pretty minimal TIFF container parser."""
	
	def _STRING(s): # No support for multi string fields
		return "".join(s).rstrip("\0")
	
	def _RATIONAL(s):
		res = []
		for i in range(0, len(s), 2):
			res.append(Fraction(*s[i:i+2]))
		return tuple(res)
	
	types = {1: (1, "B" , None),      # BYTE
		 2: (1, "c", _STRING),    # ASCII
		 3: (2, "H" , None),      # SHORT
		 4: (4, "I" , None),      # LONG
		 5: (8, "II", _RATIONAL), # RATIONAL
		 # No TIFF6 fields, sorry
		}
	
	def __init__(self, fh, subifd=0x14a):
		from struct import unpack, pack
		self._fh = fh
		self._subifd = subifd
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
		subifd = self.ifdget(self.ifd[0], self._subifd) or []
		for next_ifd in subifd:
			self.subifd.append(self._ifdread(next_ifd))
	
	def ifdget(self, ifd, tag):
		if tag in ifd:
			type, vc, d = ifd[tag]
			print "get",ifd[tag]
			if type not in self.types: return None
			tl, fmt, func = self.types[type]
			if isinstance(d, int): # offset
				self._fh.seek(d)
				d = self._fh.read(tl * vc)
				d = self._up(fmt * vc, d)
			if func: d = func(d)
			return d
	
	def get(self, tag):
		return self.ifdget(self.subifd[0], tag)
	
	def _ifdread(self, next_ifd):
		ifd = {}
		self._fh.seek(next_ifd)
		count = self._up1("H", self._fh.read(2))
		for i in range(count):
			d = self._fh.read(12)
			tag, type, vc = self._up("HHI", d[:8])
			if type in self.types and self.types[type][0] * vc <= 4:
				tl, fmt, _ = self.types[type]
				d = d[8:8 + (tl * vc)]
				off = self._up(fmt * vc, d)
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
exif = tiff(fh, 0x8769)
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
