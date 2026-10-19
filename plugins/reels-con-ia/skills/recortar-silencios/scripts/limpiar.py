#!/usr/bin/env python3
# ============================================================================
# limpiar.py — Segunda pasada sobre el timeline ya recortado de silencios:
#              quita los GOLPECITOS (clips sin voz) y las RETOMAS (cuando te
#              equivocas y repites la frase, se queda solo el último intento).
#
# Por qué así:
#  · Golpecitos: auto-editor corta por volumen, así que un golpe en la mesa o un
#    chasquido sobrevive como clip de 0,05 s. El VAD de voz (silero, el de
#    whisper.cpp) los separa limpio: un golpe da 0 % de voz; una sílaba corta
#    de verdad («fac-», «te») cae dentro de voz.
#  · Retomas: whisper sobre el audio entero DEDUPLICA las repeticiones («cada
#    test menos de un… cada test menos de un céntimo» sale una sola vez). Por
#    eso cada BLOQUE de habla (clips seguidos sin pausa) se transcribe por
#    separado, y un bloque cuyo texto reaparece al principio de un bloque
#    posterior es un intento fallido.
#
# Subcomandos:
#   analizar <silencios.fcpxml> <video> <workdir> <out.fcpxml> [--idioma es]
#       Transcribe, propone decisiones (tomas.json + tomas.md) y escribe out.
#   aplicar <workdir> <out.fcpxml> [--quitar B3,s17] [--mantener B5,s40]
#       Reescribe out con las decisiones de tomas.json más los cambios. Es
#       idempotente: siempre parte de <workdir>/silencios.fcpxml.
#   preview <workdir> <video> <out.mp4>
#       MP4 a media resolución con solo los clips que se quedan.
#
# Exit: 0 ok · 1 uso · 3 falta whisper-cli/ffmpeg/modelo · 5 timeline vacío
# ============================================================================
import sys, os, re, json, glob, wave, struct, shutil, subprocess, unicodedata
from fractions import Fraction
from difflib import SequenceMatcher

HUECO_BLOQUE = 0.40   # pausa (s) a partir de la cual empieza otro bloque
VOZ_MIN      = 0.30   # fracción mínima del clip dentro de voz para no ser golpe
SIM_RETOMA   = 0.72   # parecido mínimo entre el intento y el arranque del siguiente
VENTANA      = 4      # bloques hacia delante donde buscar la repetición
VENTANA_S    = 25.0   # y como mucho estos segundos después
ALUCINACIONES = ("gracias", "subtitulos", "amara", "antarctica", "suscribete",
                 "suscribanse", "musica", "aplausos")

def die(code, msg):
    sys.stderr.write(msg.rstrip() + "\n"); sys.exit(code)

# --- tiempos FCPXML ---------------------------------------------------------
def frac(v):
    if not v: return Fraction(0)
    m = re.match(r'(-?\d+)/(\d+)s$', v)
    if m: return Fraction(int(m.group(1)), int(m.group(2)))
    m = re.match(r'(-?[\d.]+)s$', v)
    return Fraction(m.group(1)) if m else Fraction(0)

def attr(tag, name):
    m = re.search(r'\b' + name + r'="([^"]*)"', tag)
    return m.group(1) if m else ""

def attr_raw(tag, name):
    m = re.search(r'\b' + name + r'="[^"]*"', tag)
    return m.group(0) if m else ""

def set_attr(tag, name, val):
    if re.search(r'\b' + name + r'="', tag):
        return re.sub(r'\b' + name + r'="[^"]*"', f'{name}="{val}"', tag, count=1)
    return re.sub(r'\s*/?>$', lambda m: f' {name}="{val}"' + m.group(0), tag, count=1)

def leer_timeline(path):
    """Clips del primer <spine>, en orden, con su tiempo en el fichero fuente."""
    xml = open(path, encoding="utf-8").read()
    spine = re.search(r'(<spine\b[^>]*>)(.*?)(</spine>)', xml, re.S)
    if not spine: die(5, f"{path}: no hay <spine>.")
    tags = re.findall(r'<asset-clip\b[^>]*/>', spine.group(2))
    if not tags: die(5, f"{path}: timeline vacío.")
    assets = {attr(a, "id"): a for a in re.findall(r'<asset\b[^>]*>', xml)}
    # denominador con el que vienen escritos los tiempos (60, 1200…): los offsets nuevos van igual
    den = max(int(m.group(1)) for t in tags for m in [re.search(r'/(\d+)s"', attr_raw(t, "duration"))] if m) \
        if any("/" in attr(t, "duration") for t in tags) else 1
    clips = []
    for k, t in enumerate(tags):
        a0 = frac(attr(assets.get(attr(t, "ref"), ""), "start"))
        s = frac(attr(t, "start")) - a0
        d = frac(attr(t, "duration"))
        clips.append({"id": f"s{k+1}", "tag": t, "a": float(s), "b": float(s + d), "dur": d})
    return xml, spine, clips, den

# --- audio ------------------------------------------------------------------
def extraer_wav(video, dst):
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vn", "-ac", "1",
                        "-ar", "16000", "-c:a", "pcm_s16le", dst])
    if r.returncode != 0 or not os.path.isfile(dst):
        die(3, "ffmpeg no pudo sacar el audio del vídeo.")

def leer_pcm(path):
    w = wave.open(path); n = w.getnframes()
    return struct.unpack('<%dh' % n, w.readframes(n))

def escribir_wav(path, muestras):
    o = wave.open(path, "wb"); o.setnchannels(1); o.setsampwidth(2); o.setframerate(16000)
    o.writeframes(struct.pack('<%dh' % len(muestras), *muestras)); o.close()

def modelos():
    dirs = [os.environ.get("RECORTAR_WHISPER_DIR", ""),
            os.path.expanduser("~/.cache/hyperframes/whisper/models"),
            os.path.expanduser("~/whisper-models"),
            "/opt/homebrew/share/whisper-cpp", "/opt/homebrew/share/whisper.cpp"]
    def busca(nombres):
        if os.environ.get("RECORTAR_WHISPER_MODEL") and "silero" not in nombres[0]:
            return os.environ["RECORTAR_WHISPER_MODEL"]
        for n in nombres:
            for d in dirs:
                if not d: continue
                hits = sorted(glob.glob(os.path.join(d, n)))
                if hits: return hits[-1]
        return ""
    return (busca(["ggml-large-v3.bin", "ggml-large-v3-turbo.bin", "ggml-medium.bin", "ggml-small.bin"]),
            busca(["ggml-silero-*.bin"]))

def vad(wav, modelo):
    """Tramos de voz [(a, b)] en segundos según silero (whisper.cpp)."""
    if not modelo or not shutil.which("whisper-vad-speech-segments"):
        return None
    r = subprocess.run(["whisper-vad-speech-segments", "-f", wav, "-vm", modelo,
                        "-vt", "0.5", "-vsd", "30", "-vp", "0"],
                       capture_output=True, text=True)
    tramos = [(float(a) / 100, float(b) / 100) for a, b in
              re.findall(r'start = ([\d.]+), end = ([\d.]+)', r.stdout + r.stderr)]
    return tramos or None

def fraccion_voz(a, b, tramos):
    if b <= a: return 0.0
    dentro = sum(max(0.0, min(b, y) - max(a, x)) for x, y in tramos)
    return dentro / (b - a)

def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9ñ ]", " ", s).split()

# --- análisis ---------------------------------------------------------------
def transcribir_bloques(bloques, pcm, workdir, modelo, idioma):
    d = os.path.join(workdir, "bloques"); os.makedirs(d, exist_ok=True)
    pad = [0] * int(16000 * 0.3)
    args = []
    for b in bloques:
        f = os.path.join(d, f"{b['id']}.wav")
        trozo = []
        for c in b["clips"]:   # solo el audio que queda en el timeline, sin las pausas
            trozo += list(pcm[int(c["a"] * 16000):int(c["b"] * 16000)]) + [0] * 800
        escribir_wav(f, pad + trozo + pad)
        args += ["-f", f]
    r = subprocess.run(["whisper-cli", "-m", modelo, "-l", idioma, "-mc", "0", "-otxt", "-np",
                        "-nt"] + args, capture_output=True, text=True)
    for b in bloques:
        txt = os.path.join(d, f"{b['id']}.wav.txt")
        b["texto"] = " ".join(open(txt, encoding="utf-8").read().split()) if os.path.isfile(txt) else ""
    shutil.rmtree(d, ignore_errors=True)
    if r.returncode != 0:
        sys.stderr.write("Aviso: whisper-cli devolvió error; las retomas pueden quedar sin detectar.\n")

def es_alucinacion(texto, dur):
    w = norm(texto)
    return dur < 1.2 and (not w or all(any(h in x for h in ALUCINACIONES) for x in w)
                          or " ".join(w) in ("cc por antarctica films argentina",))

def proponer(bloques):
    vivos = [b for b in bloques if b["decision"] == "queda"]
    for i, b in enumerate(vivos):
        wi = norm(b["texto"])
        if not wi: continue
        for c in vivos[i + 1:i + 1 + VENTANA]:
            if c["a"] - b["b"] > VENTANA_S: break
            wj = norm(c["texto"])
            if not wj: continue
            # el intento fallido se parece al ARRANQUE de un bloque posterior
            n = len(wi)
            sim = SequenceMatcher(None, wi, wj[:n + 1]).ratio()
            if n <= 2:
                ok = wj[:n] == wi and len(wj) > n     # «y tú» → «y tú puedes…»
            else:
                ok = sim >= SIM_RETOMA
            if ok:
                b["decision"] = "fuera"
                b["motivo"] = f"retoma: lo repites en {c['id']} ({int(sim*100)} %)"
                break
    # un bloque cortito justo antes de una retoma suele ser un arranque en falso
    # («de todas formas…» y vuelta a empezar): no se quita solo, se marca para revisar
    for x, y in zip(vivos, vivos[1:]):
        if x["decision"] == "queda" and len(norm(x["texto"])) <= 3 and y["motivo"].startswith("retoma"):
            x["aviso"] = "¿arranque en falso? va justo antes de una retoma"
    # retoma reformulada («y tú puedes copiarle» → «y tú puedes aplicarlo…»): arranca
    # igual que el bloque siguiente pero cambia las palabras. Tampoco se quita sola.
    quedan = [b for b in vivos if b["decision"] == "queda"]
    for x, y in zip(quedan, quedan[1:]):
        wx, wy = norm(x["texto"]), norm(y["texto"])
        if not x.get("aviso") and len(wx) >= 2 and wx[:2] == wy[:2] and y["a"] - x["b"] < 10:
            x["aviso"] = f"¿retoma reformulada? arranca igual que {y['id']}"

def analizar(silencios, video, workdir, out, idioma):
    for t in ("ffmpeg", "whisper-cli"):
        if not shutil.which(t): die(3, f"Falta {t}: la limpieza de retomas lo necesita.")
    modelo, silero = modelos()
    if not modelo: die(3, "No encuentro un modelo de whisper (ggml-large-v3.bin). "
                          "Pon su ruta en RECORTAR_WHISPER_MODEL.")
    _, _, clips, _ = leer_timeline(silencios)
    wav = os.path.join(workdir, "audio16k.wav")
    extraer_wav(video, wav)
    pcm = leer_pcm(wav)

    # 1) golpecitos: clips sin voz
    tramos = vad(wav, silero)
    for c in clips:
        c["voz"] = round(fraccion_voz(c["a"], c["b"], tramos), 2) if tramos else None
        c["decision"], c["motivo"] = "queda", ""
        if tramos is not None and c["voz"] < VOZ_MIN:
            c["decision"], c["motivo"] = "fuera", f"golpe/ruido: {int(c['voz']*100)} % de voz"
        elif tramos is None and c["b"] - c["a"] <= 0.09:
            c["decision"], c["motivo"] = "fuera", "golpe/ruido: clip de menos de 0,1 s"

    # 2) bloques de habla: clips con voz separados por menos de HUECO_BLOQUE
    bloques, actual = [], None
    for c in clips:
        if c["decision"] == "fuera": continue
        if actual and c["a"] - actual["clips"][-1]["b"] < HUECO_BLOQUE and c["b"] - actual["clips"][0]["a"] < 28:
            actual["clips"].append(c)
        else:
            actual = {"clips": [c]}; bloques.append(actual)
    for k, b in enumerate(bloques):
        b["id"] = f"B{k+1}"
        b["a"], b["b"] = b["clips"][0]["a"], b["clips"][-1]["b"]
        b["decision"], b["motivo"] = "queda", ""
        for c in b["clips"]: c["bloque"] = b["id"]

    transcribir_bloques(bloques, pcm, workdir, modelo, idioma)
    for b in bloques:
        dur = sum(c["b"] - c["a"] for c in b["clips"])
        if es_alucinacion(b["texto"], dur):
            b["decision"], b["motivo"] = "fuera", "sin palabras (ruido o respiración)"
    proponer(bloques)
    os.remove(wav)

    estado = {
        "video": os.path.abspath(video),
        "clips": [{k: c[k] for k in ("id", "a", "b", "voz", "decision", "motivo")} | {"bloque": c.get("bloque", "")}
                  for c in clips],
        "bloques": [{"id": b["id"], "a": b["a"], "b": b["b"], "clips": [c["id"] for c in b["clips"]],
                     "texto": b["texto"], "decision": b["decision"], "motivo": b["motivo"],
                     "aviso": b.get("aviso", "")}
                    for b in bloques],
    }
    json.dump(estado, open(os.path.join(workdir, "tomas.json"), "w"), ensure_ascii=False, indent=1)
    aplicar(workdir, out, [], [])

# --- aplicar ----------------------------------------------------------------
def decisiones(estado, quitar, mantener):
    """id de clip → (queda?, motivo). Bloque decide sobre sus clips; clip suelto manda."""
    fuera = {c["id"]: c["motivo"] for c in estado["clips"] if c["decision"] == "fuera"}
    por_bloque = {b["id"]: b for b in estado["bloques"]}
    for b in estado["bloques"]:
        if b["decision"] == "fuera":
            for cid in b["clips"]: fuera[cid] = b["motivo"]
    for x in quitar + mantener:
        if x not in por_bloque and x not in {c["id"] for c in estado["clips"]}:
            die(1, f"No existe «{x}» (usa ids tipo B12 o s40 de tomas.md).")
    for x in quitar:
        for cid in (por_bloque[x]["clips"] if x in por_bloque else [x]):
            fuera[cid] = "a mano"
    for x in mantener:
        for cid in (por_bloque[x]["clips"] if x in por_bloque else [x]):
            fuera.pop(cid, None)
    return fuera

def tt(v, den):
    if v == 0: return "0s"
    n = v * den
    return f"{n.numerator}/{den}s" if n.denominator == 1 else f"{v.numerator}/{v.denominator}s"

def aplicar(workdir, out, quitar, mantener):
    estado = json.load(open(os.path.join(workdir, "tomas.json"), encoding="utf-8"))
    xml, spine, clips, den = leer_timeline(os.path.join(workdir, "silencios.fcpxml"))
    fuera = decisiones(estado, quitar, mantener)
    # las decisiones a mano se guardan, para que un aplicar posterior no las pierda
    for b in estado["bloques"]:
        if b["id"] in quitar: b["decision"], b["motivo"] = "fuera", "a mano"
        if b["id"] in mantener: b["decision"], b["motivo"] = "queda", "a mano"
    for c in estado["clips"]:
        if c["id"] in quitar: c["decision"], c["motivo"] = "fuera", "a mano"
        if c["id"] in mantener: c["decision"], c["motivo"] = "queda", "a mano"
        c["final"] = "fuera" if c["id"] in fuera else "queda"
    json.dump(estado, open(os.path.join(workdir, "tomas.json"), "w"), ensure_ascii=False, indent=1)

    def montar(lista, renombrar=False):
        off, tags = Fraction(0), []
        for c in lista:
            t = set_attr(c["tag"], "offset", tt(off, den))
            if renombrar:
                t = set_attr(t, "name", f"{c['id']} · {fuera[c['id']]}".replace('"', "'"))
            tags.append(t); off += c["dur"]
        return tags, off

    quedan = [c for c in clips if c["id"] not in fuera]
    descartes = [c for c in clips if c["id"] in fuera]
    if not quedan: die(5, "Con estas decisiones no queda ningún clip.")
    ind = re.search(r'\n([ \t]*)<asset-clip', spine.group(2))
    ind = ind.group(1) if ind else "  "
    tags, total = montar(quedan)
    cuerpo = "\n" + "\n".join(ind + t for t in tags) + "\n" + ind[:-2]
    nuevo = xml[:spine.start(2)] + cuerpo + xml[spine.end(2):]

    proj = re.search(r'([ \t]*)<project\b[^>]*>.*?</project>', nuevo, re.S)
    if proj:
        p = proj.group(0)
        p = re.sub(r'(<sequence\b[^>]*?\bduration=")[^"]*(")', lambda m: m.group(1) + tt(total, den) + m.group(2), p, count=1)
        bloque_desc = ""
        if descartes:
            dtags, dtotal = montar(descartes, renombrar=True)
            d = re.sub(r'(<spine\b[^>]*>).*?(</spine>)',
                       lambda m: m.group(1) + "\n" + "\n".join(ind + t for t in dtags) + "\n" + ind[:-2] + m.group(2),
                       p, count=1, flags=re.S)
            d = re.sub(r'(<project\b[^>]*\bname=")([^"]*)(")', lambda m: m.group(1) + m.group(2) + " · descartes" + m.group(3), d, count=1)
            d = re.sub(r'(<sequence\b[^>]*?\bduration=")[^"]*(")', lambda m: m.group(1) + tt(dtotal, den) + m.group(2), d, count=1)
            d = re.sub(r'\s+uid="[^"]*"', "", d)
            bloque_desc = "\n" + proj.group(1) + d.lstrip()
        nuevo = nuevo[:proj.start()] + p + bloque_desc + nuevo[proj.end():]
    open(out, "w", encoding="utf-8").write(nuevo)
    escribir_md(estado, workdir, len(quedan), len(descartes), float(total))
    print(f"  Limpieza : {len(descartes)} clips fuera "
          f"({sum(1 for c in estado['clips'] if c['id'] in fuera and c['motivo'].startswith('golpe'))} golpes, "
          f"{sum(1 for b in estado['bloques'] if b['decision'] == 'fuera')} bloques de retomas/ruido)")
    print(f"  Tomas    : {os.path.join(workdir, 'tomas.md')}")

def fmt(s):
    m = int(s // 60); return f"{m}:{s - m*60:05.2f}"

def escribir_md(estado, workdir, n_q, n_f, total):
    L = [f"# Tomas · {os.path.basename(estado['video'])}", "",
         f"Quedan {n_q} clips ({fmt(total)}), fuera {n_f}. "
         "Para cambiar algo: `limpiar.py aplicar <workdir> <out> --quitar B7 --mantener B9,s40`.", "",
         "| bloque | tiempo | clips | decisión | texto |", "|---|---|---|---|---|"]
    clips = {c["id"]: c for c in estado["clips"]}
    for b in estado["bloques"]:
        dec = "✓" if b["decision"] == "queda" else f"✗ {b['motivo']}"
        if b.get("aviso") and b["decision"] == "queda" and b["motivo"] != "a mano": dec = f"⚠ {b['aviso']}"
        sueltos = [cid for cid in b["clips"] if clips[cid].get("final") != ("fuera" if b["decision"] == "fuera" else "queda")]
        if sueltos: dec += f" (a mano: {', '.join(sueltos)})"
        rango = b["clips"][0] if len(b["clips"]) == 1 else f"{b['clips'][0]}–{b['clips'][-1]}"
        L.append(f"| {b['id']} | {fmt(b['a'])} | {rango} | {dec} | {b['texto'].replace('|', '/')} |")
    golpes = [c for c in estado["clips"] if c["decision"] == "fuera" and not c.get("bloque")]
    if golpes:
        L += ["", "Golpecitos fuera: " + ", ".join(f"{c['id']} ({fmt(c['a'])}, {c['b']-c['a']:.2f} s)" for c in golpes)]
    open(os.path.join(workdir, "tomas.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")

# --- preview ----------------------------------------------------------------
def preview(workdir, video, mp4):
    estado = json.load(open(os.path.join(workdir, "tomas.json"), encoding="utf-8"))
    tramos = [(c["a"], c["b"]) for c in estado["clips"] if c.get("final", c["decision"]) == "queda"]
    expr = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in tramos)
    script = os.path.join(workdir, "preview.filtro")
    open(script, "w").write(
        f"[0:v]select='{expr}',setpts=N/FRAME_RATE/TB,scale=trunc(iw/4)*2:trunc(ih/4)*2[v];"
        f"[0:a]aselect='{expr}',asetpts=N/SR/TB[a]")
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-filter_complex_script", script,
                        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast",
                        "-crf", "23", "-c:a", "aac", mp4])
    os.remove(script)
    sys.exit(r.returncode)

# --- main -------------------------------------------------------------------
def lista(flag, argv):
    if flag in argv:
        i = argv.index(flag)
        if i + 1 >= len(argv): die(1, f"Falta el valor de {flag}")
        return [x.strip() for x in argv[i + 1].split(",") if x.strip()]
    return []

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__ or open(__file__).read().split("# ===")[1]); sys.exit(0)
    cmd = a[0]
    if cmd == "analizar" and len(a) >= 5:
        idioma = lista("--idioma", a)
        analizar(a[1], a[2], a[3], a[4], idioma[0] if idioma else "es")
    elif cmd == "aplicar" and len(a) >= 3:
        aplicar(a[1], a[2], lista("--quitar", a), lista("--mantener", a))
    elif cmd == "preview" and len(a) >= 4:
        preview(a[1], a[2], a[3])
    else:
        die(1, "uso: limpiar.py analizar <silencios.fcpxml> <video> <workdir> <out.fcpxml> [--idioma es]\n"
               "     limpiar.py aplicar <workdir> <out.fcpxml> [--quitar B3,s17] [--mantener B5]\n"
               "     limpiar.py preview <workdir> <video> <out.mp4>")
