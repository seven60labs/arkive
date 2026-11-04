#!/usr/bin/env python3
"""Write a 48x48 PNG illustration (teal tile, sand radio-wave arcs) with the stdlib only. Usage: make_icon.py out.png"""
import sys, zlib, struct, math
W = H = 48; TEAL = (15, 76, 76); SAND = (217, 183, 126); OFF = (255, 255, 255)
px = []
for y in range(H):
    row = []
    for x in range(W):
        c = TEAL; dx, dy = x - 16, y - 32; r = math.hypot(dx, dy)
        if r < 4: c = OFF
        elif dx > 0 and dy < 0 and any(abs(r - k) < 1.6 for k in (11, 19, 27)): c = SAND
        row.append(c)
    px.append(row)
raw = b"".join(b"\x00" + bytes(v for p in row for v in p) for row in px)
def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
open(sys.argv[1], "wb").write(png)
