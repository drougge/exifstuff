#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
#
# For manipulating JPEGs embedded in RAWs
#

from tiff import tiff

def find_jpegs(fh):
	"""Returns (offset, length) pairs for all embedded JPEGs found in fh.
	Handles DNG, NEF, PEF and quite possibly other TIFF-derived formats.
	Might ignore thumbnails, depending on format."""
	
	def find(a, oid, lid):
		for i in range(len(a)):
			o = t.ifdget(a[i], oid)
			l = t.ifdget(a[i], lid)
			if o and l and len(o) == len(l):
				for p in zip(o, l):
					fh.seek(p[0])
					if fh.read(4) == "\xff\xd8\xff\xdb":
						r.append(p)
	
	t = tiff(fh)
	r = []
	find(t.subifd, 0x111, 0x117) # DNG looks like this
	find(t.subifd, 0x201, 0x202) # NEF looks like this
	find(t.ifd, 0x201, 0x202)    # PEF looks like this
	return r

for fn in "/tmp/IMGP6496.PEF", "/tmp/DROU5668.DNG", "/tmp/DSC_0658.NEF":
	fh = file(fn, "rb")
	jpegs = find_jpegs(fh)
	print fn, jpegs
	for i, j in enumerate(jpegs):
		fh.seek(j[0])
		d = fh.read(j[1])
		o = open(fn + "." + str(i), "wb")
		o.write(d)
		o.close()
	fh.close()
