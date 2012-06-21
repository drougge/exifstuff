#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

from tiff import tiff
from sys import argv
import re
from fractions import Fraction

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

FNum, FL, FL135 = 0x829d, 0x920a, 0xa405
names = {FNum: "FNumber", FL: "FocalLength", FL135: "FocalLengthIn35mmFormat"}
argmap = {"f": FNum, "fnum" : FNum, "fnumber": FNum, "f-number": FNum,
          "fl": FL, "focallength": FL, "focal-length": FL,
          "fl135": FL135, "fl35": FL135, "focallengthin35mm": FL135, "focallengthin35mmformat": FL135,
         }

num    = r"(\d+(?:[\./]\d+)?)"
re_num = re.compile(num + "$")
re_arg = re.compile(r"(?:--)?(\w+=)?" + num + r"(mm)?$")
re_f   = re.compile(r"(f)/?" + num + r"$")

args  = []
p_arg = None
props = {}

def arg(a):
	global p_arg
	a = a.lower()
	if p_arg:
		if a:
			m = re_num.match(a)
			if not m and a:
				raise Exception("Bad argument value " + a + " for " + p_arg[0])
			args.append((p_arg[0], p_arg[1], Fraction(m.group(1))))
		else:
			args.append((p_arg[0], p_arg[1], None))
		p_arg = None
		return True
	m = re_arg.match(a) or re_f.match(a)
	if m:
		sa = m.group(1) or ""
		args.append((a, sa.rstrip("="), Fraction(m.group(2))))
		return True
	if a[:2] == "--":
		if "=" in a:
			a, v = a.split("=", 1)
			if v:
				raise Exception("Unknown arg " + a)
			else:
				args.append((a, a[2:], None))
		else:
			p_arg = (a, a[2:])
		return True

def apply_args():
	here = {}
	bare = []
	rem  = []
	for a, sa, v in args:
		if sa:
			if sa not in argmap:
				raise Exception("Unknown arg " + a)
			here[argmap[sa]] = v
		else:
			bare.append(v)
	seq = (FL, FL135, FNum)
	l = len(here) + len(bare)
	if l > 3:
		a = [a for a in a, sa, v in args if not sa]
		raise Exception("More numbers than I know what to do with: " + " ".join(a))
	for v in bare:
		if l > 1:
			here[[i for i in seq if i not in here][0]] = v
		else:
			here[FNum] = v
	for a, v in here.items():
		if v is None:
			del here[a]
			if a in props: del props[a]
	props.update(here)

def bad(p):
	return Exception("Missing/bad " + names[p])

for fn in argv[1:]:
	if arg(fn): continue
	apply_args()
	if not props:
		raise Exception("File before any values " + fn)
	print fn
	fh = open(fn, "rb+")
	try:
		fh = jpeg_wrapper(fh)
	except Exception:
		fh.seek(0)
	exif = tiff(fh, 0x8769)
	print exif.subget(0, FNum)
	print repr(exif.subget(0, FL))
	print exif.subget(0, FL135)
	for p, v in props.items():
		print "  " + names[p] + " => " + str(v)
		if p not in exif.subifd[0]:
			raise bad(p)
		e = exif.subifd[0][p]
		if e[1:3] == (5, 1):
			exif.write(e[3], "II", v.numerator, v.denominator)
		elif e[1] in (1, 3, 4) and e[2] == 1:
			if v.denominator != 1:
				raise Exception("Value of " + names[p] + " must be integer")
			exif.write(e[0] + 2, "HII", 4, 1, v.numerator)
		else:
			raise bad(p)
	print
