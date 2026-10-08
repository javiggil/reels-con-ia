# -*- coding: utf-8 -*-
"""Alineacion forzada CTC (torchaudio MMS_FA) del audio contra la transcripcion.
Devuelve start/end por PALABRA VISIBLE (mismos indices que words.json)."""
import json, unicodedata, re, warnings
warnings.filterwarnings("ignore")
import torch, torchaudio

W = json.load(open('words.json'))

# numeros y extranjerismos: como SUENAN (romanizado latino basico)
# ==== RELLENA ESTO EN CADA REEL ====================================================
# El alineador CTC compara FONEMAS, no dígitos. Todo lo que no se lea como se
# escribe va aquí, romanizado a como SUENA en castellano. Si te lo saltas, el
# número descuadra su bloque y arrastra a los vecinos.
#   cifras   "3.200" -> "tres mil doscientos"   "105" -> "ciento cinco"
#   marcas   "Brixly" -> "briksli"   "Nuvo.ai," -> "nuvo ei ai"
#   siglas   "IA" -> "ia"
# La clave es la palabra EXACTA de words.json, con su puntuación pegada.
SPOKEN = {
    "IA": "ia", "IA.": "ia", "IA,": "ia",
}
def norm(s):
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.lower()
    s = re.sub(r"[^a-z ]", "", s)
    return s.strip()

units = []
tokens = []
for i, (w, a, b) in enumerate(W):
    txt = SPOKEN.get(w, w)
    toks = [t for t in norm(txt).split() if t]
    assert toks, (i, w)
    units.append((i, len(tokens), len(tokens) + len(toks)))
    tokens.extend(toks)

bundle = torchaudio.pipelines.MMS_FA
model = bundle.get_model(with_star=False)
model.eval()
DICT = bundle.get_dict(star=None)
import wave, struct
_w = wave.open('audio16k.wav'); _n = _w.getnframes(); sr = _w.getframerate()
assert sr == 16000
_d = struct.unpack('<%dh' % _n, _w.readframes(_n))
wav = torch.tensor([[x/32768.0 for x in _d]], dtype=torch.float32)
with torch.inference_mode():
    emission, _ = model(wav)
targets = torch.tensor([[DICT[c] for word in tokens for c in word]], dtype=torch.int32)
ali, scores = torchaudio.functional.forced_align(emission, targets, blank=0)
aligned, scores = ali[0], scores[0].exp()
spans = torchaudio.functional.merge_tokens(aligned, scores)
ratio = wav.size(1) / emission.size(1) / sr
out = []
p = 0
for tok in tokens:
    n = len(tok)
    s = spans[p:p+n]
    out.append((tok, s[0].start * ratio, s[-1].end * ratio, sum(x.score for x in s)/n))
    p += n
assert p == len(spans), (p, len(spans))

res = []
for (i, a, b) in units:
    st = out[a][1]; en = out[b-1][2]
    sc = sum(o[3] for o in out[a:b]) / (b-a)
    res.append(dict(i=i, w=W[i][0], start=round(st,3), end=round(en,3),
                    dtw_start=W[i][1], dtw_end=W[i][2], score=round(sc,3)))
json.dump(res, open('align.json','w'), ensure_ascii=False, indent=0)
bad = [r for r in res if r['score'] < 0.5]
print(f"{len(res)} palabras alineadas; {len(bad)} con score<0.5")
for r in bad: print("  LOW", r['i'], r['w'], r['score'])
