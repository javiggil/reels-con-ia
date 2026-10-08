# -*- coding: utf-8 -*-
"""Afina cada frontera de bloque al hueco real de la envolvente (o lead-in de 50 ms)."""
import wave, struct, math, json
w = wave.open('audio16k.wav'); n = w.getnframes(); sr = w.getframerate()
d = struct.unpack('<%dh' % n, w.readframes(n))
WIN = 0.02
def db(t):
    a = int(t*sr); b = a + int(WIN*sr)
    s = d[a:b]
    if not s: return -99.0
    r = math.sqrt(sum(x*x for x in s)/len(s))/32768.0
    return 20*math.log10(r + 1e-9)

B = json.load(open('blocks.json'))
LEAD = 0.10
moved = []
cand = []
for k in range(1, len(B)):
    s = B[k]['start']
    lo, hi = s - 0.20, s + 0.05
    ts = [lo + i*0.01 for i in range(int((hi-lo)/0.01)+1)]
    vals = [(db(t), t) for t in ts]
    mn, tmn = min(vals)
    if mn < -25.0:                       # hueco real -> cortar dentro del silencio
        new = round(tmn + 0.015, 3)
    else:                                # habla continua -> lead-in fijo
        new = round(s - LEAD, 3)
    cand.append((k, s, new))

MIN = 0.28
for k, s, new in cand:
    B[k]['snap'] = new
for k in range(1, len(B)):
    prev_start = B[k-1]['start']
    new = B[k]['snap']
    if new - prev_start < MIN:            # no aplastes el bloque anterior
        new = max(B[k]['start'] - 0.05, prev_start + MIN)
        new = min(new, B[k]['start'])
    if k+1 < len(B) and B[k+1]['snap'] - new < MIN:
        new = min(new, B[k+1]['snap'] - MIN)
    new = round(max(new, prev_start + 0.20), 3)
    s0 = B[k]['start']
    if abs(new - s0) > 0.005:
        moved.append((k, B[k]['text'][:26], s0, new, round(new-s0, 3)))
    B[k]['start'] = new
for b in B: b.pop('snap', None)
for k in range(len(B)-1):
    B[k]['end'] = B[k+1]['start']
json.dump(B, open('blocks.json', 'w'), ensure_ascii=False, indent=0)
print(len(moved), 'fronteras movidas de', len(B)-1)
for m in moved[:200]: print('  ', m)
d2 = [b['end']-b['start'] for b in B]
print('min', round(min(d2),2), 'media', round(sum(d2)/len(d2),2), 'max', round(max(d2),2))
