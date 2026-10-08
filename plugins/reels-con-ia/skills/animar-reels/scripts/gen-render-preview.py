# -*- coding: utf-8 -*-
"""gen-render-preview.py <ruta-proyecto>: escribe render-all.sh y preview.sh del reel.

Lee `_assets/mapa-clips.json` (el que deja duraciones.py) y genera:
  _kit/render-all.sh  · renderiza cada clip a mov (ALFA) o mp4 (OPACO), 4K/60, sin audio
  _kit/preview.sh     · compone los clips en su timecode + subtítulos + tu audio a 540x960

El preview es el ÚNICO sitio donde se ve si un rótulo choca con la banda de
subtítulos: los snapshots por clip no la muestran.
"""
import json, os, sys, stat

R = os.path.abspath(sys.argv[1])
M = json.load(open(os.path.join(R, '_assets', 'mapa-clips.json')))
name = os.path.basename(R.rstrip('/'))
pref = name            # prefijo de los archivos de ENTREGA: el nombre del reel
DUR = float(sys.argv[2]) if len(sys.argv) > 2 else max(c['end'] for c in M.values())

items = sorted(M.items(), key=lambda kv: kv[1]['start'])

def out_name(clip, c):
    slug = clip.replace('clip-', '')
    return f"{pref}-clip-{slug}" + ("-ALFA" if c['tipo'] == 'ALFA' else "")

# ---------- render-all.sh ----------
lines = [f"""#!/bin/bash
# render-all.sh: los {len(items)} clips, NATIVOS 2160x3840 a 60 fps, SIN audio.
set -u
ROOT="{R}"
OUT="$ROOT/ENTREGA"
mkdir -p "$OUT"
export PRODUCER_ENABLE_CHUNKED_ENCODE=true

render () {{
  local dir="$ROOT/animaciones/$1" fmt="$2" name="$3"
  echo "=== $1 -> $name.$fmt"
  python3 "$ROOT/_kit/inject.py" "$dir" >/dev/null
  # --workers 1 SIEMPRE: multi-worker captura a disco (~33 MB/frame alfa); con el disco justo falla (si el disco va justo, falla)
  ( cd "$dir" && npx hyperframes render --workers 1 --format "$fmt" --fps 60 \\
      --output "$OUT/$name.$fmt" 2>&1 | tail -2 )
}}
"""]
for clip, c in items:
    fmt = 'mov' if c['tipo'] == 'ALFA' else 'mp4'
    lines.append(f'render {clip:<22} {fmt} "{out_name(clip, c)}"')
lines.append('\necho "=== HECHO"\nls -la "$OUT"')
p = os.path.join(R, '_kit', 'render-all.sh')
open(p, 'w').write('\n'.join(lines) + '\n')
os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR)

# ---------- render-some.sh (tandas: renderiza solo los clips que le pases) ----------
some = f"""#!/bin/bash
# render-some.sh <clip> [<clip>...]: mismo render que render-all.sh, solo esos clips.
# Sirve para ir renderizando por tandas mientras se autoran los demás.
set -u
ROOT="{R}"
for c in "$@"; do
  line=$(grep "^render $c " "$ROOT/_kit/render-all.sh") || {{ echo "no existe $c en render-all.sh" >&2; continue; }}
  bash -c "$(sed -n '1,/^}}$/p' "$ROOT/_kit/render-all.sh"); $line"
done
"""
p = os.path.join(R, '_kit', 'render-some.sh')
open(p, 'w').write(some)
os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR)

# ---------- preview.sh ----------
ins, filt, chain = [], [], "[0:v]"
for k, (clip, c) in enumerate(items, start=1):
    ext = 'mov' if c['tipo'] == 'ALFA' else 'mp4'
    ins.append(f'  -i "$E/{out_name(clip, c)}.{ext}" \\')
    filt.append(f"[{k}:v]scale=540:960,setpts=PTS-STARTPTS+{c['start']}/TB[v{k}]; ")
n = len(items)
ins.append(f'  -i "$E/{pref}-SUBTITULOS-ALFA.mov" \\')
ins.append(f'  -i "$R/_assets/{pref}.wav" \\')
filt.append(f"[{n+1}:v]scale=540:960,setpts=PTS-STARTPTS[vs]; ")
for k, (clip, c) in enumerate(items, start=1):
    tag = f"[o{k}]" if k < n else "[ol]"
    filt.append(f"{chain}[v{k}]overlay=enable='between(t,{c['start']},{c['end']})'{tag}; ")
    chain = tag
filt.append("[ol][vs]overlay[vout]")

body = f"""#!/bin/bash
# preview.sh: los clips en su timecode + subtítulos + tu audio, a 540x960.
# Es el ÚNICO sitio donde se ve si un rótulo choca con la banda de subtítulos.
set -eu
R="{R}"
E="$R/ENTREGA"
OUT="${{1:-$E/_preview-sincronia.mp4}}"

ffmpeg -y -v error -stats \\
  -f lavfi -t {DUR:.2f} -i "color=c=#3a3532:s=540x960:r=60" \\
{chr(10).join(ins)}
  -filter_complex "\\
{''.join(filt)}" \\
  -map "[vout]" -map {n+2}:a -t {DUR:.2f} \\
  -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 160k "$OUT"

echo "OK -> $OUT"
"""
p = os.path.join(R, '_kit', 'preview.sh')
open(p, 'w').write(body)
os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR)
print(f"render-all.sh y preview.sh escritos ({len(items)} clips, {DUR:.2f} s)")
