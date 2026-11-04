#!/usr/bin/env python3
"""Write a 48x48 PNG illustration (teal tile, sand heartbeat line) with the stdlib only. Usage: make_icon.py out.png"""
import sys, zlib, struct
W = H = 48; TEAL = (15, 76, 76); SAND = (217, 183, 126)
pts = [(4, 26), (16, 26), (20, 14), (26, 38), (30, 26), (44, 26)]
def near(x, y):
    for (a, b), (c, d) in zip(pts, pts[1:]):
        for t in range(41):
            u = t / 40; px, py = a + (c - a) * u, b + (d - b) * u
            if (x - px) ** 2 + (y - py) ** 2 < 3.2: return True
    return False
rows = [b"\x00" + bytes(v for x in range(W) for v in (SAND if near(x, y) else TEAL)) for y in range(H)]
def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b"")
open(sys.argv[1], "wb").write(png)
