---
name: animar-reels
description: Anima un reel con HyperFrames a partir de un .wav (alguien hablando a cámara) y su guion. Genera los dos entregables para el editor (Final Cut, Premiere, DaVinci, CapCut) - (1) subtítulos 4K vertical con alfa, bloques de 2-3 palabras sincronizados por alineación forzada CTC (no por los timestamps de whisper) y (2) clips de animación cronológicos en estilo "demo de app" (lienzo infinito, cámara tipo prezi, UI grande en 3D, odómetros, partículas, cursor), opacos (mp4) o alfa en losa horizontal (mov ProRes 4444), sin audio ni subtítulos, más la tabla de montaje con timecodes y la reconciliación del guion. Úsala cuando digan "anima este reel", "hazme los subtítulos y las animaciones de este audio", "monta el reel de este audio", "subtítulos con alfa para Final Cut", "animaciones para poner encima de mi cara", "clips de motion graphic para mi reel" o pasen un .wav con su guion. Para la mecánica de HyperFrames usa /hyperframes.
user-invocable: true
---

# animar-reels

De un **.wav de alguien hablando a cámara + su guion** salen dos entregables independientes
para montar en el editor (Final Cut, Premiere, DaVinci, CapCut). Los dos son **4K vertical
(2160x3840), 60 fps y SIN audio**; el creador los coloca sobre su cara.

1. **Subtítulos**: un .mov ProRes 4444 con alfa. Caja negra con texto blanco, bloques de 2-3
   palabras, cortes secos. Sincronía por **alineación forzada CTC**, no por los tiempos de whisper.
2. **Animaciones**: clips cronológicos en estilo **demo de app** (movimiento prezi sobre un
   lienzo infinito). **OPACO** (mp4, tapa la cara) o **ALFA** (mov ProRes 4444, losa horizontal
   que se superpone a la cara). Sin audio ni subtítulos.

Más tres documentos: `MONTAJE.md` (tabla con timecodes), `RECONCILIACION.md` (qué cambió al
grabar respecto al guion) y, opcional, `VEO-PROMPTS.md` (si se usa un generador de vídeo).

Esta skill aporta el **pipeline** y un **sistema visual de ejemplo** (`reference/estilo-ejemplo.md`,
sustituible por el tuyo). La mecánica de HyperFrames (composiciones, `data-*`, lint, render) está
en las skills de HyperFrames: léelas antes de escribir HTML.

## Requisitos (comprueba antes de empezar)

| Qué | Para qué | Instalar |
|---|---|---|
| Node 22+ | HyperFrames (`npx hyperframes ...`) | nodejs.org |
| FFmpeg y ffprobe | audio a 16 kHz, previews, verificación | `brew install ffmpeg` |
| whisper.cpp (`whisper-cli`) + modelo `ggml-large-v3.bin` | el TEXTO del audio | `brew install whisper-cpp` y descargar el modelo (o `npx hyperframes transcribe`, que lo gestiona) |
| Python 3 con `torch` y `torchaudio` | alineación forzada CTC (`MMS_FA`) | `pip install torch torchaudio` |
| ImageMagick (`magick`) | hojas de contacto de `check.py` | `brew install imagemagick` |
| Skills de HyperFrames | composiciones y render | `claude plugin marketplace add heygen-com/hyperframes` y luego instalar el plugin |
| GSAP 3.12 | animación (lo baja `nuevo-reel.sh` del CDN) | `https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js` o `npm i gsap` |
| Fuentes del estilo de ejemplo | Fraunces, Anton, Inter (OFL) | ver `reference/estilo-ejemplo.md` |
| Opcional: `potrace` + Pillow | `scripts/vectorize.py` (bitmap a vector) | `brew install potrace` y `pip install pillow` |

## Antes de nada: el brief

El creador rellena **una sola vez** `reference/brief-plantilla.md` (formato, qué no se anima,
estilo, márgenes, mascota, editor) y a partir de ahí solo cambian el audio y el guion. Si no hay
brief, **pídelo o ábrelo con preguntas cortas** (qué editor usa, qué tramos del guion no se
animan, si hay estilo propio o usa el de ejemplo, si hay mascota). Lo que el brief no decide,
decídelo con criterio y anótalo en `RECONCILIACION.md`. Lo que el creador pida un día concreto
manda sobre el brief.

## Pipeline paso a paso

Convención: `R=~/reels/<nombre>`. Lo monta `scripts/nuevo-reel.sh`; todo lo de audio se corre
desde `$R/_assets/`.

```bash
S=<ruta de esta skill>
bash $S/scripts/nuevo-reel.sh mi-reel ~/Movies/mi-reel.wav     # REELS_DIR=... para otra carpeta madre
```
Deja `$R` con el kit en `_kit/`, el audio a 16 kHz mono (`audio16k.wav`), los scripts en
`_assets/`, la plantilla de subtítulos en `subtitulos/` y las herramientas `_kit/scaffold.sh` y
`_kit/ver.sh`.

| # | Qué | Cómo |
|---|---|---|
| 1 | Texto | `whisper-cli ... -nfa -ml 1 --split-on-word` + `mkwords.py` |
| 2 | Calibrar contra el guion | cada duda **decidida con el audio** (recorte), nunca a ojo · `score.py` |
| 3 | Tiempos | `align.py` (CTC forzado) con el diccionario de pronunciación `SPOKEN`. Los tiempos de whisper se tiran |
| 4 | Bordes | `verifica-bordes.py` contra la envolvente del audio |
| 5 | Bloques de 2-3 palabras | `blocks.py` y revisión a mano |
| 6 | Afinar fronteras | `snap.py` |
| 7 | Render de subtítulos | plantilla `subtitulos/index.html` a MOV alfa |
| 8 | Repartir clips | `duraciones.py` (edita `CLIPS`) a `mapa-clips.json` |
| 9 | Investigar y reunir material | datos con fuente, logos vectoriales en `_kit/parts/` |
| 10 | Construir clips | el **hook primero**, luego clips en **paralelo con subagentes** |
| 11 | Render y preview | `gen-render-preview.py`, `render-all.sh` / `render-some.sh`, `preview.sh` |
| 12 | Verificar | `verifica-render.sh`, fotograma 0 real de cada clip, preview global |
| 13 | Documentar | `MONTAJE.md`, `RECONCILIACION.md` (y `VEO-PROMPTS.md` si aplica) |

### 1 · Texto (solo el texto)
```bash
cd $R/_assets
whisper-cli -m "$WHISPER_MODEL" -f audio16k.wav -l es -nfa -ml 1 --split-on-word -oj -of words
mv words.json.json words.json.raw 2>/dev/null || mv words.json words.json.raw
python3 mkwords.py          # agrupa sub-tokens en palabras visibles: words.json
```
`-nfa` es obligatorio (sin él whisper desactiva los timestamps finos en silencio). Cambia `-l es`
por el idioma del audio. `$WHISPER_MODEL` es la ruta del `ggml-large-v3.bin`.

### 2 · Calibrar contra el guion con el audio como juez
Compara `words.json` con el guion. **Lo grabado manda**: si el creador cambió una frase al
hablar, la entrega sigue lo que dijo. Cada palabra que no case se decide **con el audio**:
```bash
ffmpeg -y -v error -i audio16k.wav -ss 32.50 -to 33.75 chk.wav
whisper-cli -m "$WHISPER_MODEL" -f chk.wav -l es -nt           # qué oye acotado
python3 score.py <<'EOT'                                        # qué prefiere el CTC
chk.wav | hipótesis A
chk.wav | hipótesis B
EOT
```
Fallos típicos de whisper: siglas oídas como palabras ("IA" como "guía"), marcas que parten en
dos, cifras largas troceadas ("100. 1.5" por 105), empates acústicos (decide la gramática). El
`score.py` promedia por carácter y favorece la cadena corta: si gana por poco la hipótesis más
corta, manda lo que oye whisper sobre el recorte. Las **palabras clave de llamadas a la acción**
(la palabra que el espectador debe comentar) van siempre en MAYÚSCULAS.
**Corrige el texto ANTES de alinear** y edita `words.json` buscando por contexto, no por índice
(los índices se desplazan al insertar o fusionar).

### 3 · Alinear (aquí salen los tiempos buenos)
Rellena `SPOKEN` en `align.py` con **cómo suena** todo lo que no se lee como se escribe: cifras
("3.200" a "tres mil doscientos"), marcas ("Brixly" a "briksli"), siglas. La clave es la palabra
EXACTA de `words.json`, con su puntuación pegada. Sin esto el número descuadra su bloque.
```bash
python3 align.py     # align.json: start/end por palabra + score CTC
```
Los `score<0.5` en números y palabras función cortas son normales; en una palabra larga y
aislada indican texto mal.

### 4 · Verificar los bordes
```bash
python3 verifica-bordes.py     # dónde arranca y muere la voz de verdad
```
El primer y último subtítulo **no se dan por buenos**: whisper mete ruido de sala en el arranque.
Mira la envolvente que imprime.

### 5 · Bloques
```bash
FIRST_START=0.28 LAST_END=58.44 python3 blocks.py
```
Programación dinámica: penaliza bloques de 1 y de 4+ palabras, cerrar en palabra función, líneas
de más de 22 caracteres y duraciones fuera de 0,30-1,60 s. **Lee la primera pasada y arregla lo
que chirríe** con `FORCE_BLOCKS` / `FORCE_CUTS`. Un precio no se parte ("a 12" / "o 15").

### 6 · Afinar fronteras
```bash
python3 snap.py
```
Cada corte cae dentro de un hueco real de la envolvente, o con lead-in de 100 ms si es habla
continua. Ningún bloque baja de 0,28 s.

### 7 · Subtítulos (entregable 1)
Detalle en `reference/subtitulos.md`. En `subtitulos/index.html` se tocan **solo**: el array
`STARTS` (sale de `blocks.json`), `LAST_END`, los dos `data-duration` y el comentario de cabecera
(el registro de qué se corrigió y por qué).
```bash
cd $R/subtitulos && npx hyperframes lint
PRODUCER_ENABLE_CHUNKED_ENCODE=true npx hyperframes render --workers 1 --format mov --fps 60 \
  --output ../ENTREGA/<reel>-SUBTITULOS-ALFA.mov
```
`--workers 1` siempre: sin él captura a disco (cientos de GB). Comprobar `pix_fmt = yuva444p12le`
y `nb_frames = duración x 60`.

### 8 · Repartir clips
Edita `CLIPS` en `duraciones.py` con las fronteras de `blocks.json`: `(nombre, ALFA|OPACO, inicio,
fin)`. Escribe `mapa-clips.json` e imprime, por clip, qué se dice y en qué segundo **relativo al
clip**; esos son los tiempos de la timeline. Sin `CLIPS` lista las fronteras disponibles.

**Qué NO se anima** lo decide el brief del creador (típicamente: la intro fija de la serie, las
llamadas a la acción, el cierre). Se deja hueco y se documenta en `MONTAJE.md` con timecodes.
**Alterna ALFA y OPACO con criterio** (`reference/layout-clips.md`).

### 9 · Reunir material con honestidad
Antes de dibujar, ten los datos y los logos. Regla de honestidad (abajo). Logos vectoriales de
fuentes oficiales o de librerías de iconos; si solo hay bitmap, `scripts/vectorize.py`. Cada logo
a `_kit/parts/<nombre>.svg` y se usa con `<!--PART:nombre-->`. Una cara real solo si la voz ya la
presentó.

### 10 · Construir los clips: hook primero, resto en paralelo
Estilo y receta en `reference/demo.md`; geometría y trampas en `reference/layout-clips.md`.
1. **El hook lo hace el agente principal primero** (es el `clip-00`, opaco): fija el listón
   visual y permite ajustar el kit antes de repartir.
2. Con el hook bueno, lanza **subagentes en paralelo de 2-3 clips cada uno**, con un brief común
   (reglas del estilo, geometría OPACO/ALFA, "autora en `_src/index.src.html`, no toques `_kit/`")
   y por clip: tipo, duración, tiempos de voz relativos y qué se ve en cada beat.
3. Para cada clip: `bash $R/_kit/scaffold.sh clip-03-nombre`, autorar en
   `animaciones/clip-03-nombre/_src/index.src.html` y `bash $R/_kit/ver.sh clip-03-nombre`
   (lint + snapshots + hoja de contacto `snapshots/HOJA.png` con zona segura y banda de
   subtítulos dibujadas). **Mira la hoja** antes de dar un clip por bueno.
4. El agente principal revisa cada hoja, pide sus propios fotogramas si la del subagente es corta
   y va renderizando por tandas mientras llegan los demás.

### 11 · Render
```bash
python3 $R/_assets/gen-render-preview.py $R     # escribe _kit/render-all.sh, render-some.sh y preview.sh
bash $R/_kit/render-some.sh clip-00-hook clip-01-x   # por tandas
bash $R/_kit/render-all.sh                            # o todo
bash $R/_kit/preview.sh                               # compone todo con tu audio a 540x960
```
**`--workers 1` siempre** (ya va en los scripts generados). ALFA: `--format mov` (ProRes 4444),
nativo 2160x3840 (el render con alfa no admite `--resolution`). OPACO: `--format mp4`.

### 12 · Verificar
```bash
bash $S/scripts/verifica-render.sh $R
```
Caza los dos fallos que pasan lint, validate y snapshot: **clip congelado** (GSAP no cargó y se
renderiza un frame fijo) y **alfa perdido** (`pix_fmt` distinto de `yuva444p12le`). Además:
`nb_frames` ≈ `data-duration` x 60, el **fotograma 0 real** de cada clip (ninguno vacío ni con algo
que debía entrar después) y el **preview global** frame a frame contra el subtítulo que toca.
Detalle en `reference/entrega.md`.

### 13 · Documentar y reconciliar
`MONTAJE.md` y `RECONCILIACION.md` (estructura en `reference/entrega.md`). Si el guion vive en
algún sitio (notas, repo), ofrece reescribirlo contra lo grabado dejando el plan original debajo.

## Qué se anima y qué no

- **Se anima** lo que la voz explica y se puede ver: cifras que suben, flujos, comparaciones,
  una app en acción. Un beat de voz = una acción visible.
- **No se anima** lo que el brief diga (configurable): intro fija, llamadas a la acción (comentar,
  guardar, compartir), cierre o gancho al siguiente vídeo, tramos puramente personales.
- **El hook sí** se anima (opaco, sin palabras ni cifras) salvo que el brief lo excluya.
- Si el creador cambia algo al grabar (se cae un beat, cambia una herramienta), **se anima lo que
  dijo** y se registra en la reconciliación. Un beat caído a mitad del guion no se compensa
  metiendo una persona o dato que la voz no ha presentado.

## Márgenes de Instagram Reels (SIEMPRE)

En lienzo 1080x1920 la UI de Reels tapa: arriba ~120 px, derecha ~180 px (like, comentar,
compartir, audio), abajo ~420 px (usuario, caption, CTA), izquierda ~60 px. **Zona segura
~840x1380, de (60,120) a (900,1500).** El centro útil es **x = 480, no 540**. En 2160x3840 todo x2.
Los subtítulos ocupan la banda y 1240-1330 (1080 base): nada de los clips puede caer ahí. Diagrama
en `assets/reels-safe-zone.svg`. Los márgenes se pueden ajustar en el brief.

## OPACO o ALFA

- **OPACO** (mp4): cutaway a pantalla completa, **tapa la cara**. Para explicaciones densas.
- **ALFA** (mov ProRes 4444): **losa horizontal** (más ancha que alta) sobre su cara; la
  animación se desarrolla de izquierda a derecha. Para remates cortos, un dato que rubrica, un
  sello. Un ~35 % de clips en alfa funciona bien. El ALFA va **entero sobre su propia losa
  opaca**: sobre vídeo oscuro, la tinta sin losa se queda hueca.

## Honestidad en pantalla (no negociable)

- Una cifra **no verificada** no entra. Si es un cálculo propio, se rotula "cálculo propio" dentro
  del clip, con su supuesto.
- Un claim de una marca va entrecomillado y atribuido.
- Lo que el creador afirma sin fuente se dibuja **sin badge de fuente**.
- No se inventan productos, rankings ni nombres: los listados van genéricos.
- No se mete la cara de nadie que la voz no haya presentado.
- Los datos de los ejemplos del kit son ficticios y así deben seguir si se reutilizan.

## Gotchas que cuestan horas

Lista completa en `reference/gotchas.md`. Los cinco que más duelen:
1. Usar los timestamps de whisper (van adelantados y de forma errática; no se arregla con un offset).
2. Render sin `--workers 1` (captura a disco, llena el volumen).
3. Dar un clip por bueno sin mirar `snapshots/HOJA.png` ni el preview global.
4. Estados iniciales con `tl.set(..., 0)` a secas: no se pintan en el fotograma 0 (usar `D.hide`).
5. No verificar el MP4/MOV real: un clip congelado o un alfa perdido pasan todos los gates.

## Mapa de archivos

```
SKILL.md                      este documento
reference/subtitulos.md       entregable 1 en detalle (CTC, bloques, plantilla)
reference/demo.md             el estilo de movimiento "demo de app" y sus ingredientes
reference/layout-clips.md     geometría, zona segura, trampas de layout, ritmo
reference/entrega.md          qué se entrega, verificación, MONTAJE y RECONCILIACION
reference/gotchas.md          trampas técnicas de HyperFrames/GSAP/render
reference/estilo-ejemplo.md   sistema visual "hecho a mano" como EJEMPLO + cómo hacer el tuyo
reference/brief-plantilla.md  brief fijo que rellena cada creador
scripts/                      pipeline (align, blocks, snap, duraciones, render, verificación...)
kit/                          base.css, demo.css, demo.js, plantilla de subtítulos, inject, check
examples/                     composiciones de ejemplo con datos ficticios
assets/reels-safe-zone.svg    diagrama de márgenes
```
