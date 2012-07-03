#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
#
# For manipulating JPEGs embedded in RAWs
#
# rawjpeg.py raw_fn jpg_fn
# if jpg_fn exists, replace largest jpeg in raw with this.
# if jpg_fn doesn't exist, extract largest jpeg in raw to this.

from tiff import tiff
from sys import argv, exit
import Image
from os.path import exists

def find_jpegs(t):
	"""Returns (offset, length) pairs for all embedded JPEGs found in tiff.
	Handles DNG, PEF and quite possibly other TIFF-derived formats.
	Might ignore thumbnails, depending on format."""
	
	def find(a, oid, lid):
		for aa in a:
			o, l = t.ifdget(aa, oid), t.ifdget(aa, lid)
			w, h = t.ifdget(aa, 0x100), t.ifdget(aa, 0x101)
			if o and l and w and h:
				t.fh.seek(o[0])
				if t.fh.read(3) == "\xff\xd8\xff": # JPEGish
					if t.fh.read(1) != "\xc3": # Not DNG RAW data
						r.append((o[0], l[0], aa[lid], aa[0x100], aa[0x101]))
	
	r = []
	find(t.subifd, 0x111, 0x117) # DNG looks like this
	find(t.subifd, 0x201, 0x202) # NEF looks like this (doesn't work though)
	find(t.ifd, 0x201, 0x202)    # PEF looks like this
	return r

raw_fn, jpg_fn = argv[1:]
if exists(jpg_fn):
	jpg_fh = open(jpg_fn, "rb")
	jpg = Image.open(jpg_fn)
	w, h = jpg.size
	jpg_fh.seek(0)
	jpg = jpg_fh.read()
	raw = tiff(open(raw_fn, "rb+"))
	jpg_pos = max(find_jpegs(raw))
	raw.fh.seek(0, 2)
	if sum(jpg_pos[:2]) != raw.fh.tell():
		print("ERROR: Largest JPEG not at end of RAW.")
		exit(1)
	for field in jpg_pos[2:]:
		if field[1:3] != (4, 1):
			print("ERROR: Unhandled field format.")
			exit(1)
	for field, value in zip(jpg_pos[2:], (len(jpg), w, h)):
		raw.write(field[0] + 8, "I", value)
	raw.fh.seek(jpg_pos[0], 0)
	raw.fh.truncate()
	raw.fh.write(jpg)
else:
	raw = tiff(open(raw_fn, "rb"))
	jpg_pos = max(find_jpegs(raw))
	raw.fh.seek(jpg_pos[0])
	jpg = raw.fh.read(jpg_pos[1])
	assert len(jpg) == jpg_pos[1]
	jpg_fh = open(jpg_fn, "wb")
	jpg_fh.write(jpg)
