#!/usr/bin/env python3
# ============================================================================
# molde.py — Injerta los cortes calculados por auto-editor sobre un MOLDE real
#            exportado desde el propio Final Cut Pro.
#
# Por qué existe: Final Cut CRASHEA al importar un .fcpxml cuyo <asset> no lleva
# SU bookmark (el marcador de seguridad macOS que FCP genera al importar la
# media). No se puede fabricar a mano de forma fiable. La solución robusta:
# el usuario importa el clip en FCP y exporta un XML (el "molde", que ya trae el
# asset con su bookmark real); nosotros reemplazamos su timeline por los trozos
# de habla que calculó auto-editor. Resultado: importa siempre, cero crash.
#
# Uso: molde.py <molde.fcpxml|.fcpxmld> <autoeditor.fcpxml> <out.fcpxml>
#               <nombre_proyecto> <stem_del_video>
# Exit: 0 ok · 4 no se pudo casar el asset / molde inválido · 5 timeline vacío
# ============================================================================
import sys, os, re

def die(code, msg):
    sys.stderr.write(msg.rstrip() + "\n"); sys.exit(code)

if len(sys.argv) < 6:
    die(1, "uso: molde.py <molde> <autoeditor.fcpxml> <out> <nombre> <stem>")

molde_arg, ae_path, out_path, nombre, stem = sys.argv[1:6]

# --- localizar el Info.fcpxml si nos dan un bundle .fcpxmld -----------------
molde_path = molde_arg
if os.path.isdir(molde_arg):
    cand = os.path.join(molde_arg, "Info.fcpxml")
    molde_path = cand if os.path.isfile(cand) else molde_arg
if not os.path.isfile(molde_path):
    die(4, f"No encuentro el molde: {molde_arg}")

molde = open(molde_path, encoding="utf-8").read()
ae    = open(ae_path,   encoding="utf-8").read()

# --- extraer TODOS los <asset>...</asset> del molde ------------------------
assets = re.findall(r'<asset\b.*?</asset>', molde, re.S)
# por si algún asset viniera autocerrado (sin media-rep): tras los completos
assets += [m + "" for m in re.findall(r'<asset\b[^>]*/>', molde)]
if not assets:
    die(4, "El molde no tiene ningún <asset>. ¿Exportaste el XML SIN meter el "
           "clip en un proyecto? En Final Cut: importa el vídeo, arrástralo a un "
           "proyecto nuevo y luego Archivo > Exportar XML.")

def asset_attr(a, name):
    m = re.search(r'\b' + name + r'="([^"]*)"', a)
    return m.group(1) if m else ""

def asset_basename(a):
    src = asset_attr(a, "src")   # file:///...//A001_..._C094.mov
    if src:
        b = os.path.basename(src)
        try:
            from urllib.parse import unquote
            b = unquote(b)
        except Exception:
            pass
        return os.path.splitext(b)[0]
    return asset_attr(a, "name")

# --- casar el asset con el vídeo por nombre de fichero ---------------------
target = None
for a in assets:
    if asset_basename(a) == stem or asset_attr(a, "name") == stem:
        target = a; break
if target is None:
    if len(assets) == 1:
        target = assets[0]          # molde de un solo clip: sin ambigüedad
    else:
        nombres = ", ".join(asset_basename(a) or "?" for a in assets)
        die(4, f"El molde tiene {len(assets)} clips ({nombres}) y ninguno casa "
               f"con «{stem}». Exporta un molde que contenga ese clip, o renombra "
               f"la salida para que coincida.")

aid = asset_attr(target, "id")
fid = asset_attr(target, "format")

# --- el <format> que usa ese asset -----------------------------------------
fmt = None
if fid:
    m = re.search(r'<format\b[^>]*\bid="' + re.escape(fid) + r'"[^>]*/>', molde)
    if m: fmt = m.group(0)
if fmt is None:
    m = re.search(r'<format\b[^>]*/>', molde)   # último recurso: el primero
    if m:
        fmt = m.group(0)
        if not fid:
            mm = re.search(r'\bid="([^"]+)"', fmt); fid = mm.group(1) if mm else ""
if fmt is None:
    die(4, "El molde no tiene <format>.")

# frameDuration del molde -> timebase de destino (p.ej. 20/1200s)
fd = re.search(r'frameDuration="(\d+)/(\d+)s"', fmt)
if fd:
    FN, FD_ = int(fd.group(1)), int(fd.group(2))   # 20, 1200
else:
    FN, FD_ = 20, 1200
FPS_BASE = FD_ // FN            # 1200/20 = 60 -> ticks por segundo = FD_
TICKS = FD_                     # denominador de destino (1200)

# --- start intrínseco del asset (timecode de cámara), en ticks -------------
def to_ticks(v):
    """'56065s' o 'N/Ds' -> ticks del timebase de destino (denominador TICKS)."""
    if not v or v == "0s":
        return 0
    m = re.match(r'(-?\d+)/(\d+)s$', v)
    if m:
        return round(int(m.group(1)) / int(m.group(2)) * TICKS)
    m = re.match(r'(-?\d+)s$', v)
    if m:
        return int(m.group(1)) * TICKS
    return 0

ASSET_START = to_ticks(asset_attr(target, "start"))

# start intrínseco que auto-editor ya escribió en SU asset (= timecode de cámara
# embebido en el .mov, si lo hay). Los `start` de los trozos de auto-editor ya
# vienen medidos desde ESE origen; para reanclarlos al asset del molde hay que
# sumar solo la DIFERENCIA (normalmente 0, porque ambos leen el mismo timecode).
# Si no lo tuviéramos en cuenta, sumaríamos el timecode dos veces -> el `start`
# se sale del rango del asset y Final Cut CRASHEA al importar.
ae_asset = re.search(r'<asset\b[^>]*>', ae)
AE_ASSET_START = to_ticks(re.search(r'\bstart="([^"]*)"', ae_asset.group(0)).group(1)) \
    if ae_asset and re.search(r'\bstart="([^"]*)"', ae_asset.group(0)) else 0
BASE = ASSET_START - AE_ASSET_START

# --- leer los trozos de habla del .fcpxml de auto-editor -------------------
spine = re.search(r'<spine\b.*?</spine>', ae, re.S)
region = spine.group(0) if spine else ae
clips = []
for ac in re.finditer(r'<asset-clip\b[^>]*/?>', region):
    tag = ac.group(0)
    o = to_ticks(re.search(r'\boffset="([^"]*)"',   tag).group(1) if re.search(r'\boffset="([^"]*)"', tag)   else "0s")
    s = to_ticks(re.search(r'\bstart="([^"]*)"',    tag).group(1) if re.search(r'\bstart="([^"]*)"', tag)    else "0s")
    d = to_ticks(re.search(r'\bduration="([^"]*)"', tag).group(1) if re.search(r'\bduration="([^"]*)"', tag) else "0s")
    if d > 0:
        clips.append((o, s, d))
if not clips:
    die(5, "El .fcpxml de auto-editor no tiene trozos (timeline vacío).")

# --- library SIN location (a propósito) ------------------------------------
# Si emitimos <library location="…una.fcpbundle/"> apuntando a un bundle que YA
# está abierto en Final Cut (justo el que exportaste), FCP intenta importar el
# proyecto dentro de esa librería abierta y CRASHEA. Con <library> a secas, FCP
# importa en la librería activa (comportamiento seguro, el que funcionó en el
# día 19). El relink de la media no depende de esto: va por el src absoluto y el
# bookmark del media-rep.
asset_name = asset_attr(target, "name") or stem

def tt(n):
    return "0s" if n == 0 else f"{n}/{TICKS}s"

# --- salvaguarda anti-crash: los start DEBEN caer dentro del asset ---------
# Un asset-clip cuyo start (o start+duración) se sale del rango real del asset
# [ASSET_START, ASSET_START+asset_dur] hace CRASHEAR a Final Cut al importar.
# Preferimos abortar con un aviso claro que escribir un .fcpxml que revienta.
ASSET_DUR = to_ticks(asset_attr(target, "duration"))
lo, hi = ASSET_START, ASSET_START + ASSET_DUR
if ASSET_DUR > 0:
    bad = [(o, s, d) for (o, s, d) in clips
           if BASE + s < lo - TICKS or BASE + s + d > hi + TICKS]
    if bad:
        die(4, f"Los cortes se salen del rango del asset "
               f"[{lo/TICKS:.1f}s..{hi/TICKS:.1f}s]: p.ej. start={ (BASE+bad[0][1])/TICKS:.1f}s. "
               f"Suele indicar un desajuste de timecode entre auto-editor y el molde; "
               f"revisa que el molde corresponde a ESTE clip.")

total = sum(d for (_o, _s, d) in clips)

# --- emitir el .fcpxml final (v1.14, molde real + cortes) ------------------
spine_xml = []
for (o, s, d) in clips:
    spine_xml.append(
        f'                        <asset-clip ref="{aid}" offset="{tt(o)}" '
        f'name="{asset_name}" start="{tt(BASE + s)}" duration="{tt(d)}" '
        f'tcFormat="NDF" audioRole="dialogue"/>')
spine_xml = "\n".join(spine_xml)

lib_open = "<library>"

doc = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>

<fcpxml version="1.14">
    <resources>
        {target}
        {fmt}
    </resources>
    {lib_open}
        <event name="{nombre}">
            <project name="{nombre}">
                <sequence format="{fid}" duration="{tt(total)}" tcStart="0s" tcFormat="NDF" audioLayout="stereo" audioRate="48k">
                    <spine>
{spine_xml}
                    </spine>
                </sequence>
            </project>
        </event>
    </library>
</fcpxml>
'''

open(out_path, "w", encoding="utf-8").write(doc)
sys.stderr.write(f"molde: asset «{asset_name}» (id {aid}, fmt {fid}) · "
                 f"{len(clips)} trozos · total {total}/{TICKS}s\n")
sys.exit(0)
