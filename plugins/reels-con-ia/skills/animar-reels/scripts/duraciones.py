# -*- coding: utf-8 -*-
"""duraciones.py: reparte el audio en clips y saca el guion de voz de cada uno.

Se edita el bloque CLIPS (nombre, ALFA|OPACO, inicio, fin) tomando las fronteras de
blocks.json, y escribe mapa-clips.json + imprime, por clip, qué se dice y en qué
segundo RELATIVO al clip. Esos son los tiempos que van en la timeline de GSAP.
"""
import json, sys

CLIPS = [
    # ("clip-02-nombre", "ALFA",  10.569, 12.830),
    # ("clip-03-nombre", "OPACO", 12.830, 15.861),
]

if not CLIPS:
    B = json.load(open('blocks.json'))
    print("CLIPS está vacío. Fronteras disponibles (start de cada bloque):\n")
    for b in B:
        print(f"  {b['start']:7.3f}  {b['text']}")
    sys.exit(0)

B = json.load(open('blocks.json'))
out = {}
for name, tipo, a, b in CLIPS:
    inner = [x for x in B if a - 1e-6 <= x['start'] < b - 1e-6]
    out[name] = dict(tipo=tipo, start=a, end=b, dur=round(b - a, 3),
                     voz=[[x['text'], round(x['start']-a, 3), round(x['end']-a, 3)] for x in inner])
    print(f"\n== {name}  {tipo}  {a:.3f} -> {b:.3f}  ({b-a:.3f} s)")
    for t, s, e in out[name]['voz']:
        print(f"     {s:5.2f}-{e:5.2f}  {t}")
json.dump(out, open('mapa-clips.json', 'w'), ensure_ascii=False, indent=1)
print(f"\nTOTAL animado {sum(c['dur'] for c in out.values()):.3f} s en {len(out)} clips")
