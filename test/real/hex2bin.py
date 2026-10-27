#!/usr/bin/env python3
"""Intel hex of a PIC16 enhanced mid-range part -> flat little-endian image of 16-bit cells
(hex addresses count bytes, two per instruction word), starting at word address 0 (cells without data hold 0x3fff, erased flash).
  hex2bin.py <in.hex> <out.bin> [words]   (default size: 32768 words = the whole 15-bit space)"""
import sys
words = int(sys.argv[3]) if len(sys.argv) > 3 else 0x8000
img = bytearray(b'\xff\x3f' * words)     # erased flash reads 0x3fff
hi = 0
for l in open(sys.argv[1]):
    l = l.strip()
    if not l.startswith(':'):
        continue
    n, a, t = int(l[1:3], 16), int(l[3:7], 16), int(l[7:9], 16)
    d = bytes.fromhex(l[9:9 + 2 * n])
    if t == 4:
        hi = int.from_bytes(d, 'big') << 16
    elif t == 0:
        a += hi
        if a < len(img):
            img[a:a + n] = d[:len(img) - a]
open(sys.argv[2], 'wb').write(img)
