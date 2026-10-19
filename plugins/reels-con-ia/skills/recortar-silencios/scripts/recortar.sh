#!/usr/bin/env bash
# ============================================================================
# recortar.sh — Recorta los silencios de un talking-head y exporta un timeline
#               de Final Cut Pro (.fcpxml, NO destructivo) con los cortes hechos.
#               Después lo LIMPIA (limpiar.py): fuera los golpecitos sin voz y
#               las retomas (si repites una frase, se queda el último intento).
#
# Envuelve auto-editor (versión Nim 31.x). Instalar con: brew install auto-editor
# El .fcpxml referencia el media original por ruta absoluta: cero reencode,
# no toca el archivo fuente.
#
# Uso: recortar.sh <video> [--umbral 12%] [--margen 0.02s] [--smooth 0.05s,0.03s]
#      [--suave] [--solo-silencios] [--idioma es] [--fps auto] [--nombre dia-0018]
#      [--molde export.fcpxmld] [--legacy] [--mp4] [--out f.fcpxml]
# Exit: 0 ok · 1 uso · 2 vídeo no existe · 3 auto-editor no instalado
#       5 sin habla / timeline vacío · 6 auto-editor falló al exportar
# ============================================================================
set -uo pipefail

uso() {
  cat <<'EOF'
Uso: recortar.sh <video> [opciones]

  <video>          Ruta al vídeo talking-head.
  --umbral <v>     Umbral de silencio (default 12%, agresivo). Acepta % , dB o
                   fracción. Aún queda silencio → súbelo (15%). Se te come
                   palabras flojas → bájalo (8% o --suave).
  --margen <v>     Colchón alrededor del habla, en segundos (default 0.02s).
                   Cortes que suenan bruscos o comen respiraciones → súbelo
                   (0.1-0.3s). Dos valores: 0.3s,1s
  --smooth <v>     Corte y clip mínimos (default 0.05s,0.03s: cero aire).
                   Más largo (0.2s,0.1s) deja respiración entre frases.
  --suave          Preset menos agresivo (el default antiguo): umbral 8%,
                   margen 0.1s, cortes 0.1s,0.05s. Solo pisa lo que no fijes.
  --agresivo       Ya es el default; se acepta por compatibilidad.
  --solo-silencios No limpia: deja los golpecitos y las retomas (solo recorta
                   los silencios, como la versión antigua).
  --idioma <xx>    Idioma para transcribir las retomas (default es).
  --fps <n>        Frame rate del timeline (default: auto = el nominal del
                   vídeo). Evita el crash de Final Cut con rates raros. Fuerza
                   uno estándar si hace falta: 60, 30, 25, 24, 30000/1001…
  --nombre <n>     Nombre del proyecto/timeline dentro de Final Cut
                   (default: el nombre del .fcpxml de salida, p.ej. dia-0018).
  --molde <ruta>   MODO A PRUEBA DE CRASH. Ruta a un XML (.fcpxml o bundle
                   .fcpxmld) exportado desde TU Final Cut con el clip ya
                   importado. La skill calcula los cortes e injerta el timeline
                   sobre el asset REAL del molde (con su bookmark), así FCP lo
                   importa siempre sin cerrarse. Es el flujo recomendado.
  --legacy         Exporta FCPXML 1.10 (para versiones antiguas de Final Cut).
  --mp4            Además del .fcpxml, renderiza un MP4 de preview (reencoda,
                   lento en 4K; el .fcpxml no depende de esto).
  --out <archivo>  Ruta del .fcpxml (default: <vídeo>-cortado.fcpxml junto al vídeo).
  -h, --help       Esta ayuda.
EOF
}

# --- Bloque 1: defaults + parseo -------------------------------------------
UMBRAL="12%"; U_SET=0      # agresivo por defecto
MARGEN="0.02s"; M_SET=0
SMOOTH="0.05s,0.03s"; S_SET=0
LIMPIAR=1                  # golpecitos y retomas fuera (limpiar.py)
IDIOMA="es"
FPS="auto"                 # auto = detecta el rate nominal del vídeo (evita crash de FCP)
MOLDE=""                   # ruta a un XML exportado de FCP (modo a prueba de crash)
SUAVE=0
LEGACY=0
MP4=0
OUT=""
NOMBRE=""
VIDEO=""

while [ $# -gt 0 ]; do
  case "$1" in
    --umbral) [ $# -ge 2 ] || { echo "Falta el valor de --umbral"; exit 1; }; UMBRAL="$2"; U_SET=1; shift 2 ;;
    --margen) [ $# -ge 2 ] || { echo "Falta el valor de --margen"; exit 1; }; MARGEN="$2"; M_SET=1; shift 2 ;;
    --smooth) [ $# -ge 2 ] || { echo "Falta el valor de --smooth"; exit 1; }; SMOOTH="$2"; S_SET=1; shift 2 ;;
    --fps)    [ $# -ge 2 ] || { echo "Falta el valor de --fps"; exit 1; };    FPS="$2";    shift 2 ;;
    --agresivo|--agressive) shift ;;
    --suave)  SUAVE=1; shift ;;
    --solo-silencios) LIMPIAR=0; shift ;;
    --idioma) [ $# -ge 2 ] || { echo "Falta el valor de --idioma"; exit 1; }; IDIOMA="$2"; shift 2 ;;
    --nombre) [ $# -ge 2 ] || { echo "Falta el valor de --nombre"; exit 1; }; NOMBRE="$2"; shift 2 ;;
    --molde)  [ $# -ge 2 ] || { echo "Falta el valor de --molde"; exit 1; };  MOLDE="$2";  shift 2 ;;
    --out)    [ $# -ge 2 ] || { echo "Falta el valor de --out"; exit 1; };    OUT="$2";    shift 2 ;;
    --legacy|--fcp-legacy) LEGACY=1; shift ;;
    --mp4)    MP4=1; shift ;;
    -h|--help) uso; exit 0 ;;
    --*)      echo "Opción desconocida: $1"; uso; exit 1 ;;
    *)        if [ -z "$VIDEO" ]; then VIDEO="$1"; else echo "Argumento de más: $1"; exit 1; fi; shift ;;
  esac
done

# Preset --suave: el default antiguo (deja algo de aire). Solo pisa lo que NO
# hayas fijado tú a mano.
if [ "$SUAVE" = 1 ]; then
  [ "$U_SET" = 0 ] && UMBRAL="8%"
  [ "$M_SET" = 0 ] && MARGEN="0.1s"
  [ "$S_SET" = 0 ] && SMOOTH="0.1s,0.05s"
fi

# --- Bloque 2: validaciones (gates) ----------------------------------------
[ -n "$VIDEO" ] || { echo "Falta la ruta al vídeo."; uso; exit 1; }
[ -f "$VIDEO" ] || { echo "No existe el fichero: $VIDEO"; exit 2; }
command -v auto-editor >/dev/null 2>&1 || {
  echo "auto-editor no está instalado."
  echo "Instálalo con:  brew install auto-editor"
  exit 3
}
HAVE_FFPROBE=1; command -v ffprobe >/dev/null 2>&1 || HAVE_FFPROBE=0
HAVE_XMLLINT=1; command -v xmllint >/dev/null 2>&1 || HAVE_XMLLINT=0
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$LIMPIAR" = 1 ] && ! command -v python3 >/dev/null 2>&1; then
  echo "Aviso: sin python3 no puedo quitar golpecitos ni retomas; solo recorto silencios."
  LIMPIAR=0
fi
if [ -n "$MOLDE" ]; then
  [ -e "$MOLDE" ] || { echo "No existe el molde: $MOLDE"; exit 2; }
  command -v python3 >/dev/null 2>&1 || { echo "El modo --molde necesita python3."; exit 3; }
fi

# Normaliza umbral desnudo: "4" -> "4%" (si no, auto-editor lo lee como 400%)
if [[ "$UMBRAL" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
  awk -v u="$UMBRAL" 'BEGIN{ exit !(u+0 >= 1) }' && {
    echo "Aviso: interpreto --umbral $UMBRAL como ${UMBRAL}% (un número >=1 sin sufijo sería 400%)."
    UMBRAL="${UMBRAL}%"
  }
fi

# --- Bloque 3: rutas de salida ---------------------------------------------
DIR="$(cd "$(dirname "$VIDEO")" && pwd)"
BASE="$(basename "$VIDEO")"
STEM="${BASE%.*}"
: "${OUT:=$DIR/${STEM}-cortado.fcpxml}"
EXPORT="final-cut-pro"; [ "$LEGACY" = 1 ] && EXPORT="final-cut-pro:version=10"

# --- Bloque 4: criterio de corte único (mismo para fcpxml, mp4 y stats) ----
# Frame rate del timeline. auto-editor, si detecta un rate no estándar (p.ej.
# 59,99), escribe un frameDuration raro (100/5999s) que HACE CRASHEAR a Final
# Cut al importar. Forzamos el rate NOMINAL del vídeo (60/1 -> 1/60s limpio).
if [ "$FPS" = "auto" ]; then
  if [ "$HAVE_FFPROBE" = 1 ]; then
    FPS="$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of csv=p=0 "$VIDEO" 2>/dev/null)"
    FPS="${FPS//[^0-9\/]/}"   # limpia comas/espacios: "60/1," -> "60/1"
    FPS="${FPS%/1}"           # "60/1" -> "60"  (deja intacto "30000/1001")
  else
    FPS=""            # sin ffprobe no forzamos; que decida auto-editor
  fi
fi

AE_EDIT=( "$VIDEO" --edit "audio:threshold=$UMBRAL" --margin "$MARGEN" )
[ -n "$SMOOTH" ] && AE_EDIT+=( --smooth "$SMOOTH" )
[ -n "$FPS" ]    && AE_EDIT+=( --frame-rate "$FPS" )

echo ""
echo "=============================================================="
echo "  Recortando silencios$([ "$SUAVE" = 1 ] && echo '  [suave]')$([ "$LIMPIAR" = 1 ] && echo ' + golpecitos y retomas')"
echo "  Vídeo : $BASE"
echo "  Umbral: $UMBRAL   Margen: $MARGEN   Cortes: ${SMOOTH:-0.2s,0.1s (nativo)}"
echo "  FPS   : ${FPS:-auto-editor}   FCPXML: $([ -n "$MOLDE" ] && echo '1.14 (molde)' || { [ "$LEGACY" = 1 ] && echo 1.10 || echo 1.11; })"
[ -n "$MOLDE" ] && echo "  Molde : $(basename "$MOLDE")   (asset+bookmark reales de FCP)"
echo "=============================================================="

# Nombre del proyecto/timeline en Final Cut (se necesita ya para el modo molde).
FCP_NAME="$NOMBRE"
if [ -z "$FCP_NAME" ]; then FCP_NAME="$(basename "$OUT")"; FCP_NAME="${FCP_NAME%.fcpxml}"; fi

# --- Bloque 5: run principal (el .fcpxml es EL entregable) -----------------
# auto-editor calcula los cortes. En modo --molde escribe a un temporal (solo
# nos interesa la GEOMETRÍA de los trozos); si no, escribe directo al entregable.
AE_OUT="$OUT"
[ -n "$MOLDE" ] && AE_OUT="${TMPDIR:-/tmp}/recortar-$$-ae.fcpxml"
auto-editor "${AE_EDIT[@]}" --export "$EXPORT" -o "$AE_OUT"
AE_RC=$?
if [ "$AE_RC" -ne 0 ] || [ ! -s "$AE_OUT" ]; then
  echo "auto-editor falló al exportar el .fcpxml (rc=$AE_RC)."
  echo "Si el vídeo no tuviera pista de audio analizable, ese es el motivo."
  exit 6
fi

# --- Bloque 5-molde: injertar los cortes sobre el molde real de FCP --------
# El modo a prueba de crash: reemplaza el timeline del molde (exportado desde
# el propio Final Cut, con el asset y su bookmark reales) por los trozos de
# habla. Salta el renombrado y la corrección de orientación: el molde ya trae
# el <format> y el <asset> correctos.
if [ -n "$MOLDE" ]; then
  python3 "$SKILL_DIR/molde.py" "$MOLDE" "$AE_OUT" "$OUT" "$FCP_NAME" "$STEM"
  M_RC=$?
  rm -f "$AE_OUT"
  if [ "$M_RC" -ne 0 ] || [ ! -s "$OUT" ]; then
    echo "No se pudo injertar sobre el molde (rc=$M_RC)."
    exit "$M_RC"
  fi
  if [ "$HAVE_XMLLINT" = 1 ]; then
    xmllint --noout "$OUT" 2>/dev/null && echo "  ✓ .fcpxml bien formado (injertado sobre el molde real)."
  fi
fi

# --- Bloque 5b: nombre del proyecto/timeline en Final Cut ------------------
# (Solo modo normal.) auto-editor bautiza el proyecto con el nombre del fichero
# de cámara; lo renombramos al nombre pedido para que entre en FCP ya llamado
# bien (p.ej. dia-0018) y no "A001_07131534_C094".
if [ -z "$MOLDE" ] && command -v perl >/dev/null 2>&1; then
  FCP_NAME_ESC="$(printf '%s' "$FCP_NAME" | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g')" \
    perl -0777 -i -pe 's{(<project\s+name=")[^"]*(")}{$1 . $ENV{FCP_NAME_ESC} . $2}e;
                       s{(<event\s+name=")[^"]*(")}{$1 . $ENV{FCP_NAME_ESC} . $2}e' "$OUT"
fi

# --- Bloque 5c: corregir la ORIENTACIÓN del <format> -----------------------
# auto-editor escribe las dimensiones CODIFICADAS del vídeo. Si está rotado
# (grabado en vertical), Final Cut espera las de VISUALIZACIÓN; ese desajuste
# (declarar 3840x2160 cuando la media es 2160x3840) HACE CRASHEAR a FCP al
# importar. Ajustamos el <format> a las dims reales y le quitamos el `name`
# (como hace el propio FCP en su export).
if [ -z "$MOLDE" ] && [ "$HAVE_FFPROBE" = 1 ] && command -v python3 >/dev/null 2>&1; then
  python3 - "$OUT" "$VIDEO" <<'PY' || true
import sys, re, json, subprocess
out, vid = sys.argv[1], sys.argv[2]
try:
    r = subprocess.run(['ffprobe','-v','error','-select_streams','v:0',
        '-show_entries','stream=width,height:stream_side_data=rotation',
        '-of','json', vid], capture_output=True, text=True)
    st = (json.loads(r.stdout or '{}').get('streams') or [{}])[0]
    w = int(st.get('width') or 0); h = int(st.get('height') or 0)
    rot = 0
    for sd in st.get('side_data_list', []) or []:
        if sd.get('rotation') not in (None, ''):
            rot = int(sd['rotation'])
    if w and h and abs(rot) % 180 == 90:   # vertical: intercambiar
        w, h = h, w
    if w and h:
        xml = open(out).read()
        def fix(m):
            s = m.group(0)
            s = re.sub(r'\s+name="[^"]*"', '', s)        # como el FCP nativo
            s = re.sub(r'width="\d+"',  f'width="{w}"',  s)
            s = re.sub(r'height="\d+"', f'height="{h}"', s)
            return s
        xml = re.sub(r'<format\b[^>]*/>', fix, xml, count=1)
        open(out, 'w').write(xml)
except Exception:
    pass
PY
fi

# --- Bloque 5d: limpieza (golpecitos y retomas) ----------------------------
# El timeline solo-silencios se guarda en <out>-tomas/silencios.fcpxml (también
# importable, por si acaso) y limpiar.py escribe el entregable limpio en $OUT,
# con un segundo proyecto «<nombre> · descartes» con lo que ha quitado.
WORK=""
if [ "$LIMPIAR" = 1 ]; then
  WORK="${OUT%.fcpxml}-tomas"
  mkdir -p "$WORK" && mv -f "$OUT" "$WORK/silencios.fcpxml"
  echo ""
  echo "  Limpiando golpecitos y retomas (whisper por bloques)..."
  python3 "$SKILL_DIR/limpiar.py" analizar "$WORK/silencios.fcpxml" "$VIDEO" "$WORK" "$OUT" --idioma "$IDIOMA"
  L_RC=$?
  if [ "$L_RC" -ne 0 ] || [ ! -s "$OUT" ]; then
    echo "  Aviso: la limpieza falló (rc=$L_RC); entrego el timeline solo con los silencios recortados."
    cp -f "$WORK/silencios.fcpxml" "$OUT"
    LIMPIAR=0
  fi
fi

# --- Bloque 6: reporte (fuente de verdad = el propio .fcpxml) --------------
# Suma duraciones tipo "N/Ds" o "Ns" que llegan por stdin -> segundos totales.
sum_dur() { awk -F'[/s]' '{ if($2!="" && $2+0!=0) s+=$1/$2; else s+=$1 } END{ printf "%.3f", s+0 }'; }
# Formatea segundos -> M:SS.d
fmt() { awk -v s="${1:-0}" 'BEGIN{ if(s=="")s=0; m=int(s/60); printf "%d:%05.2f", m, s-m*60 }'; }

BEFORE=""; [ "$HAVE_FFPROBE" = 1 ] && BEFORE="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$VIDEO" 2>/dev/null)"

N_SEG=""; AFTER=""
if [ "$HAVE_XMLLINT" = 1 ]; then
  # solo el primer proyecto: el segundo es el de descartes
  N_SEG="$(xmllint --xpath 'count((//project)[1]//asset-clip)' "$OUT" 2>/dev/null | awk '{printf "%d", $1+0}')"
  AFTER="$(xmllint --xpath '(//project)[1]//asset-clip/@duration' "$OUT" 2>/dev/null | grep -oE '[0-9]+(/[0-9]+)?s' | sum_dur)"
  MID=""
  [ -n "$WORK" ] && MID="$(xmllint --xpath '(//project)[1]//asset-clip/@duration' "$WORK/silencios.fcpxml" 2>/dev/null | grep -oE '[0-9]+(/[0-9]+)?s' | sum_dur)"
fi

# Gate "sin habla": timeline vacío -> el umbral es demasiado alto o no hay audio.
if [ "$HAVE_XMLLINT" = 1 ] && { [ -z "$N_SEG" ] || [ "$N_SEG" -eq 0 ]; }; then
  echo ""
  echo "No se detectó habla (timeline vacío). Baja el umbral (p.ej. --umbral 2%)"
  echo "o revisa que el audio del vídeo no esté mudo."
  rm -f "$OUT"
  exit 5
fi

echo ""
echo "  ---------------------------------------------------------"
if [ -n "$BEFORE" ]; then
  echo "  Antes     : $(fmt "$BEFORE")  (${BEFORE}s)"
else
  echo "  Antes     : (ffprobe no disponible)"
fi
[ -n "$MID" ] && echo "  Sin pausas: $(fmt "$MID")  (${MID}s)"
if [ -n "$AFTER" ]; then
  echo "  Después   : $(fmt "$AFTER")  (${AFTER}s)$([ -n "$MID" ] && echo '  ← sin golpecitos ni retomas')"
  if [ -n "$BEFORE" ]; then
    CUT="$(awk -v b="$BEFORE" -v a="$AFTER" 'BEGIN{printf "%.3f", b-a}')"
    PCT="$(awk -v b="$BEFORE" -v a="$AFTER" 'BEGIN{ if(b+0>0) printf "%.1f", (b-a)/b*100; else print "0" }')"
    echo "  Recortado : $(fmt "$CUT")  (${PCT}%)"
    # "Sin silencios": conservó prácticamente todo.
    awk -v b="$BEFORE" -v a="$AFTER" 'BEGIN{ exit !((b-a) < 0.5) }' && \
      echo "  (Apenas había silencios que recortar: casi todo es habla.)"
  fi
fi
if [ -n "$N_SEG" ]; then
  echo "  Segmentos : $N_SEG    Cortes  : ~$(( N_SEG > 0 ? N_SEG - 1 : 0 ))"
fi
echo "  ---------------------------------------------------------"

# --- Bloque 7: MP4 de preview (opcional) -----------------------------------
if [ "$MP4" = 1 ]; then
  # El preview vive junto al .fcpxml y hereda su nombre (dia-0018-preview.mp4),
  # no el del fichero de cámara.
  MP4OUT="$(dirname "$OUT")/${FCP_NAME}-preview.mp4"
  echo ""
  echo "  Renderizando MP4 de preview a media resolución (para revisar los cortes)..."
  # --scale 0.5 => a la mitad (p.ej. 4K -> 1080p): rápido y suficiente para
  # eyeballar que no corta palabras. El master de verdad lo montas en FCP.
  if [ "$LIMPIAR" = 1 ]; then
    python3 "$SKILL_DIR/limpiar.py" preview "$WORK" "$VIDEO" "$MP4OUT"
  else
    auto-editor "${AE_EDIT[@]}" --scale 0.5 -o "$MP4OUT"
  fi
  if [ $? -eq 0 ]; then
    echo "  Preview MP4: $MP4OUT"
  else
    echo "  Aviso: el preview MP4 falló, pero el .fcpxml ya está listo."
  fi
fi

# --- Bloque 8: cierre ------------------------------------------------------
FMT_LINE="$(grep -m1 '<format' "$OUT")"
FMT_W="$(printf '%s' "$FMT_LINE" | grep -oE 'width="[0-9]+"'  | grep -oE '[0-9]+')"
FMT_H="$(printf '%s' "$FMT_LINE" | grep -oE 'height="[0-9]+"' | grep -oE '[0-9]+')"
FMT_DIMS="${FMT_W:-?}x${FMT_H:-?}"
echo ""
echo "  Listo. Importa en Final Cut:  File > Import > XML…"
echo "  FCPXML  : $OUT"
echo "  Proyecto: $FCP_NAME   (así aparece el timeline en Final Cut)"
[ "$LIMPIAR" = 1 ] && echo "  Tomas   : $WORK/tomas.md   (qué se ha quitado y por qué; descartes en «$FCP_NAME · descartes»)"
echo "  Formato : ${FMT_DIMS:-?}   (orientación real del vídeo)"
echo "  (No muevas ni renombres el vídeo original antes de importar: rompería el enlace.)"
echo ""
exit 0
