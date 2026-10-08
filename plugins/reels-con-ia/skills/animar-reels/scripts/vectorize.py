#!/usr/bin/env python3
"""vectorize.py <png> <out.svg> [--thr N] [--invert]: traza una capa con potrace y
devuelve SOLO los <path d="..."> (sin cabecera), listos para pegar inline."""
import sys, subprocess, os, re
from PIL import Image

src, out = sys.argv[1], sys.argv[2]
thr = 128; inv = False
for i,a in enumerate(sys.argv):
    if a == '--thr': thr = int(sys.argv[i+1])
    if a == '--invert': inv = True
im = Image.open(src).convert('L')
im = im.resize((1024, 1024), Image.LANCZOS)
bw = im.point(lambda p: 255 if ((p > thr) != inv) else 0, '1')
pbm = out + '.pbm'
bw.save(pbm)
subprocess.run(['potrace', '-s', '-o', out, '--flat', '-t', '2', '-a', '1.2', pbm], check=True)
os.remove(pbm)
s = open(out).read()
paths = re.findall(r'<path[^>]*d="[^"]*"[^>]*/?>', s)
vb = re.search(r'viewBox="([^"]+)"', s)
tr = re.search(r'<g([^>]*)>', s)
print('viewBox', vb.group(1) if vb else '?')
print('g', tr.group(1) if tr else '?')
print(len(paths), 'paths,', sum(len(p) for p in paths), 'bytes')
