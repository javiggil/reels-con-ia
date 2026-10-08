# -*- coding: utf-8 -*-
"""Agrupa los sub-tokens DTW de whisper en PALABRAS visibles -> words.json [[w,start,end],...]"""
import json, re
d = json.load(open('words.json.raw'))
segs = d['transcription']
words = []
for s in segs:
    t = s['text']
    if not t.strip():
        continue
    a = s['offsets']['from']/1000.0
    b = s['offsets']['to']/1000.0
    if t.startswith(' ') or not words:
        words.append([t.strip(), a, b])
    else:
        words[-1][0] += t.strip()
        words[-1][2] = b
# la puntuacion suelta se pega a la palabra previa
out = []
for w, a, b in words:
    if re.fullmatch(r'[.,:;!?¿¡…]+', w) and out:
        out[-1][0] += w
        out[-1][2] = b
    else:
        out.append([w, a, b])
json.dump(out, open('words.json', 'w'), ensure_ascii=False, indent=0)
print(len(out), 'palabras')
for i, (w, a, b) in enumerate(out):
    print(f'{i:3d} {a:7.3f} {b:7.3f} {w}')
