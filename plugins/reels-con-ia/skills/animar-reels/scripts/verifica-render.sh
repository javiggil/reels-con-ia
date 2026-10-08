#!/bin/bash
# verifica-render.sh <ruta-proyecto>: control de calidad de los MP4/MOV ya renderizados.
# Caza los dos fallos que pasan TODAS las verificaciones anteriores:
#   1. clip congelado (GSAP no cargó: se renderiza un frame fijo y el lint pasa)
#   2. resolución o pix_fmt equivocados (alfa que salió opaco)
set -eu
E="${1:?uso: verifica-render.sh <ruta-proyecto>}/ENTREGA"
cd "$E"
for f in *clip-*.mp4 *clip-*.mov *SUBTITULOS*.mov; do
  [ -f "$f" ] || continue
  meta=$(ffprobe -v error -show_entries stream=width,height,pix_fmt,nb_frames -of csv=p=0 "$f" | head -1)
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")
  h=""
  for p in 0.10 0.35 0.60 0.85; do
    t=$(python3 -c "print(round($d*$p,3))")
    h="$h $(ffmpeg -v error -ss $t -i "$f" -frames:v 1 -f md5 - 2>/dev/null | cut -c5-12)"
  done
  u=$(echo $h | tr ' ' '\n' | sort -u | wc -l | tr -d ' ')
  flag=""; [ "$u" -lt 3 ] && flag="  <-- ¿CONGELADO?"
  printf "%-42s %-28s %s frames distintos%s\n" "$f" "$meta" "$u/4" "$flag"
done
