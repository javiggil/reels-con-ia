# -*- coding: utf-8 -*-
"""Puntua hipotesis de texto contra un recorte de audio con CTC (torchaudio MMS_FA)."""
import sys, json, unicodedata, re, warnings, wave, struct
warnings.filterwarnings("ignore")
import torch, torchaudio

def norm(s):
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    return re.sub(r"[^a-z ]", " ", s).split()

bundle = torchaudio.pipelines.MMS_FA
model = bundle.get_model(with_star=False); model.eval()
DICT = bundle.get_dict(star=None)

def emis(path):
    w = wave.open(path); n = w.getnframes(); assert w.getframerate() == 16000
    d = struct.unpack('<%dh' % n, w.readframes(n))
    wav = torch.tensor([[x/32768.0 for x in d]], dtype=torch.float32)
    with torch.inference_mode():
        e, _ = model(wav)
    return e

def score(path, text):
    e = emis(path)
    toks = norm(text)
    tgt = torch.tensor([[DICT[c] for w in toks for c in w]], dtype=torch.int32)
    ali, sc = torchaudio.functional.forced_align(e, tgt, blank=0)
    return float(sc[0].exp().mean())

for line in sys.stdin:
    line = line.strip()
    if not line: continue
    p, t = line.split('|', 1)
    print(f"{score(p.strip(), t):.4f}  {t}")
