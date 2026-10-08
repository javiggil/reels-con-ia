#!/usr/bin/env python3
"""inject.py <clip-dir> : sustituye los marcadores por los partials del kit.

  <!--MASCOT-->        -> kit/mascota.svg (TU mascota; opcional: si no existe, el marcador se quita)
  <!--PART:nombre-->   -> kit/parts/nombre.svg (logos, iconos, recortes vectoriales)

Idempotente: reescribe siempre desde `_src/index.src.html` si existe (autora ahí, nunca
en index.html, que se regenera).
"""
import sys, os, re

KIT = os.path.dirname(os.path.abspath(__file__))

def read(p):
    with open(p) as f: return f.read()

def clean(s):
    # los partials pueden traer comentarios con <style>/<script> literales dentro
    return re.sub(r"<!--.*?-->", "", s, flags=re.S).strip()

def main(clipdir):
    idx = os.path.join(clipdir, 'index.html')
    srcdir = os.path.join(clipdir, '_src')
    os.makedirs(srcdir, exist_ok=True)
    src = os.path.join(srcdir, 'index.src.html')
    if not os.path.exists(src):
        os.replace(idx, src)
    html = read(src)
    if '<!--MASCOT-->' in html:
        mp = os.path.join(KIT, 'mascota.svg')
        if os.path.exists(mp):
            html = html.replace('<!--MASCOT-->', clean(read(mp)))
        else:
            print('AVISO: hay <!--MASCOT--> pero no existe kit/mascota.svg; se quita', file=sys.stderr)
            html = html.replace('<!--MASCOT-->', '')
    for m in set(re.findall(r'<!--PART:([a-zA-Z0-9_\-]+)-->', html)):
        p = os.path.join(KIT, 'parts', m + '.svg')
        if not os.path.exists(p):
            sys.exit('Falta el partial %s (kit/parts/%s.svg)' % (m, m))
        html = html.replace('<!--PART:%s-->' % m, clean(read(p)))
    with open(idx, 'w') as fh: fh.write(html)
    print(os.path.basename(clipdir.rstrip('/')), '->', len(html), 'bytes')

if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit('uso: inject.py <clip-dir>')
    main(sys.argv[1])
