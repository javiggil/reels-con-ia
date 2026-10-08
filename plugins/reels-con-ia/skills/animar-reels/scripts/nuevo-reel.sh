#!/bin/bash
# nuevo-reel.sh <nombre-reel> <ruta/al/audio.wav>
# Monta el proyecto del reel: carpetas, kit, audio a 16 kHz mono y los scripts de
# trabajo (scaffold / ver / render-all / preview) ya apuntando a este reel.
#
#   REELS_DIR=~/reels   (por defecto) carpeta madre de tus proyectos
#   WHISPER_MODEL=...   ruta al modelo ggml-large-v3.bin (para el aviso final)
#   LANG_AUDIO=es       idioma del audio (para el comando de whisper del aviso final)
set -eu
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="${1:?uso: nuevo-reel.sh <nombre-reel> <audio.wav>}"
AUDIO="${2:?falta el wav}"
[ -f "$AUDIO" ] || { echo "No existe el audio: $AUDIO" >&2; exit 1; }
case "$NAME" in *[!a-zA-Z0-9_-]*|"") echo "El nombre solo admite letras, números, guiones y guion bajo: $NAME" >&2; exit 1;; esac
REELS_DIR="${REELS_DIR:-$HOME/reels}"
R="$REELS_DIR/$NAME"
MODEL="${WHISPER_MODEL:-$HOME/.cache/hyperframes/whisper/models/ggml-large-v3.bin}"
LANG_AUDIO="${LANG_AUDIO:-es}"
GSAP_URL="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"

mkdir -p "$R"/{_assets/raw,_kit/fonts,_kit/parts,animaciones,subtitulos/fonts,ENTREGA}
cp "$SKILL"/kit/{base.css,demo.css,demo.js,inject.py,check.py} "$R/_kit/"
cp "$SKILL"/kit/parts/* "$R/_kit/parts/" 2>/dev/null || true
[ -f "$SKILL/kit/mascota.svg" ] && cp "$SKILL/kit/mascota.svg" "$R/_kit/" || true
cp "$SKILL"/scripts/*.py "$R/_assets/"
cp "$SKILL"/kit/subtitulos.tpl.html "$R/subtitulos/index.html"

# --- GSAP: se baja del CDN una vez y se copia a cada composición (el render no depende de la red)
if [ ! -s "$R/_kit/gsap.min.js" ]; then
  curl -fsSL "$GSAP_URL" -o "$R/_kit/gsap.min.js" \
    || { rm -f "$R/_kit/gsap.min.js"; echo "AVISO: no pude bajar GSAP. Hazlo a mano: curl -L $GSAP_URL -o $R/_kit/gsap.min.js (o npm i gsap y copia gsap/dist/gsap.min.js)" >&2; }
fi
[ -f "$R/_kit/gsap.min.js" ] && cp "$R/_kit/gsap.min.js" "$R/subtitulos/"

# --- Fuentes: no vienen en la skill (licencia OFL, se descargan). Si las dejas en
#     ~/reels/_fuentes/ (o en $FONTS_DIR) se copian solas. Ver reference/estilo-ejemplo.md
FONTS_DIR="${FONTS_DIR:-$REELS_DIR/_fuentes}"
for f in Fraunces-var Fraunces-Italic-var Anton inter-var; do
  [ -f "$FONTS_DIR/$f.woff2" ] && cp "$FONTS_DIR/$f.woff2" "$R/_kit/fonts/" || echo "AVISO: falta $FONTS_DIR/$f.woff2 (descárgala, ver reference/estilo-ejemplo.md)" >&2
done
[ -f "$FONTS_DIR/inter-var.woff2" ] && cp "$FONTS_DIR/inter-var.woff2" "$R/subtitulos/fonts/" || true

cat > "$R/subtitulos/hyperframes.json" <<'JSON'
{
  "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
  "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
  "paths": { "blocks": "compositions", "components": "compositions/components", "assets": "assets" }
}
JSON

cp "$AUDIO" "$R/_assets/$NAME.wav"
ffmpeg -y -v error -i "$R/_assets/$NAME.wav" -ac 1 -ar 16000 -c:a pcm_s16le "$R/_assets/audio16k.wav"

# --- scaffold.sh: crea la carpeta de un clip ---
cat > "$R/_kit/scaffold.sh" <<EOF
#!/bin/bash
# scaffold.sh <nombre-clip>
set -e
ROOT="$R"
D="\$ROOT/animaciones/\$1"
mkdir -p "\$D/fonts"
cp "\$ROOT/_kit/fonts/"*.woff2 "\$D/fonts/" 2>/dev/null || true
cp "\$ROOT/_kit/gsap.min.js" "\$ROOT/_kit/base.css" "\$ROOT/_kit/demo.css" "\$ROOT/_kit/demo.js" "\$D/"
mkdir -p "\$D/_src"   # se autora SIEMPRE en _src/index.src.html (inject.py regenera index.html)
cat > "\$D/hyperframes.json" <<'JSON'
{
  "\$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
  "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
  "paths": { "blocks": "compositions", "components": "compositions/components", "assets": "assets" }
}
JSON
echo "\$D listo"
EOF

# --- ver.sh: lint + snapshot + hoja de contacto con las guías dibujadas ---
cat > "$R/_kit/ver.sh" <<EOF
#!/bin/bash
# ver.sh <clip> [alfa] [t1,t2,...]   (sin tiempos: 5 frames repartidos)
set -e
R="$R"
C="\$1"; MODE="\${2:-}"; AT="\${3:-}"
python3 "\$R/_kit/inject.py" "\$R/animaciones/\$C"
( cd "\$R/animaciones/\$C" && npx hyperframes lint 2>&1 | tail -3 )
rm -rf "\$R/animaciones/\$C/snapshots"
if [ -n "\$AT" ]; then
  ( cd "\$R/animaciones/\$C" && npx hyperframes snapshot --at "\$AT" --no-end >/dev/null 2>&1 )
else
  ( cd "\$R/animaciones/\$C" && npx hyperframes snapshot --frames 5 --no-end >/dev/null 2>&1 )
fi
python3 "\$R/_kit/check.py" "\$R/animaciones/\$C/snapshots" \$MODE | tail -1
EOF

chmod +x "$R/_kit"/*.sh
echo "== $R listo"
echo "   audio  $NAME.wav + audio16k.wav (16 kHz mono)"
echo "   ahora  cd $R/_assets && whisper-cli -m $MODEL \\"
echo "            -f audio16k.wav -l $LANG_AUDIO -nfa -ml 1 --split-on-word -oj -of words"
