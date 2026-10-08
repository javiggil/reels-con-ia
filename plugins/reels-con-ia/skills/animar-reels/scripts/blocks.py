# -*- coding: utf-8 -*-
"""Agrupa palabras alineadas (CTC) en bloques de 2-3 palabras por DP."""
import json, re, os, unicodedata

A = json.load(open('align.json'))
WORDS = [(r['w'], r['start'], r['end']) for r in A]
N = len(WORDS)

FIRST_START = float(os.environ.get("FIRST_START", "0.30"))   # lo fija verifica-bordes.py
LAST_END    = float(os.environ.get("LAST_END", "0"))         # lo fija verifica-bordes.py

def norm(s):
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    return re.sub(r"[^a-z0-9]", "", s)

FUNC = {"a","el","la","los","las","un","una","unos","unas","de","del","que","y","e","o","u",
        "en","con","por","para","sin","su","tu","mi","se","te","lo","le","les","me","nos",
        "al","es","no","ya","muy","mas","pero","como","si","cuando","donde","al","asi","habra"}

def ends_punct(w): return w.endswith(('.', ',', ':', ';', '!', '?', '…'))

def cost(i, j):   # bloque = palabras [i, j)
    if (i, j) in FORCE_BLOCKS: return -1.0
    ws = [WORDS[k][0] for k in range(i, j)]
    n = j - i
    c = 0.0
    if n == 1: c += 40
    elif n == 4: c += 34
    elif n >= 5: c += 200
    # puntuacion interior: mejor cerrar ahi
    for k in range(i, j - 1):
        if ends_punct(WORDS[k][0]): c += 46
    # no cerrar en palabra funcion
    last = WORDS[j-1][0]
    if not ends_punct(last) and norm(last) in FUNC: c += 62
    # ancho de linea
    txt = ' '.join(ws)
    if len(txt) > 22: c += 26 * (len(txt) - 22)
    # duracion legible
    dur = (WORDS[j][1] if j < N else LAST_END) - WORDS[i][1]
    if dur < 0.30: c += 34
    if dur < 0.22: c += 60
    if dur > 1.60: c += 18
    return c


# Fronteras impuestas a mano DESPUÉS de leer la primera pasada: la coherencia
# semántica manda sobre el coste del DP. Índices de palabra, los de align.json.
# Ejemplo:
#   FORCE_BLOCKS = {(12,14),(14,17)}   ->  "factura 3.200" | "extra al mes"
#   FORCE_CUTS   = {12,14,17}
FORCE_BLOCKS = set()
FORCE_CUTS = set()

INF = float('inf')
best = [INF]*(N+1); back = [0]*(N+1); best[0] = 0
for j in range(1, N+1):
    for n in (1, 2, 3, 4, 5):
        i = j - n
        if i < 0: break
        if best[i] == INF: continue
        if any(k in FORCE_CUTS for k in range(i+1, j)): continue
        c = best[i] + cost(i, j)
        if c < best[j]: best[j] = c; back[j] = i

cuts = []; j = N
while j > 0:
    i = back[j]; cuts.append((i, j)); j = i
cuts.reverse()
for c in sorted(FORCE_CUTS):
    assert any(i==c for i,j in cuts), ('frontera no respetada', c)

blocks = []
for (i, j) in cuts:
    txt = ' '.join(WORDS[k][0] for k in range(i, j))
    start = FIRST_START if i == 0 else WORDS[i][1]
    blocks.append({'i': i, 'j': j, 'text': txt, 'start': round(start, 3)})
# cortes secos encadenados
for k in range(len(blocks)-1):
    blocks[k]['end'] = blocks[k+1]['start']
blocks[-1]['end'] = LAST_END

json.dump(blocks, open('blocks.json','w'), ensure_ascii=False, indent=0)
print(len(blocks), 'bloques')
for b in blocks:
    print(f"{b['start']:7.3f} {b['end']:7.3f} {b['end']-b['start']:5.2f}  {b['text']}")
