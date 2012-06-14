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
	
	def get(self, idx, tag):
		return self.ifdget(self.ifd[idx], tag)
	def subget(self, idx, tag):
		return self.ifdget(self.subifd[idx], tag)
	
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