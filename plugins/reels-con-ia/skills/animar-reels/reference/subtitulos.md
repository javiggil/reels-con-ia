# Entregable 1: subtítulos que cuadran PERFECTO

Regla que lo explica todo: **los tiempos de whisper no se usan**. Whisper pone el TEXTO; los
tiempos salen de una **alineación forzada CTC**. En una prueba real, el DTW de whisper iba
**+0,15 s de mediana y hasta +0,57 s**, con casi un 35 % de las palabras desviadas más de 0,20 s,
y **no se arregla con un offset global**: tras desplazar todo la mediana, seguían más de un 30 %
con más de 0,15 s de error. El desfase es errático, no constante.

Salida: MOV ProRes 4444 con alfa, 2160x3840, 60 fps, sin audio, caja negra + texto blanco.

---

## Los seis pasos

Todo se corre desde `_assets/` (lo monta `nuevo-reel.sh`).

### 1 · Texto (solo el texto)
```bash
whisper-cli -m "$WHISPER_MODEL" -f audio16k.wav -l es -nfa -ml 1 --split-on-word -oj -of words
mv words.json.json words.json.raw 2>/dev/null || mv words.json words.json.raw   # según versión, whisper-cli escribe words.json o words.json.json
python3 mkwords.py
```
`-nfa` es obligatorio: sin él whisper desactiva los timestamps finos **en silencio**.
`mkwords.py` agrupa los sub-tokens en palabras visibles y escribe `words.json`.

### 2 · Calibrar contra el guion, y verificar cada duda por RECORTE
Compara `words.json` con el guion. Cada palabra que no case **se decide con el audio, nunca a
ojo ni por el guion**:

```bash
ffmpeg -y -v error -i audio16k.wav -ss 32.50 -to 33.75 chk.wav
whisper-cli -m "$WHISPER_MODEL" -f chk.wav -l es -nt            # qué oye acotado
python3 score.py <<'EOT'                                         # y qué prefiere el CTC
chk.wav | Le pides a tu IA un dictado
chk.wav | Piensa tú ir a un dictado
EOT
```

Fallos recurrentes:

| Oye | Es | Señal |
|---|---|---|
| "guía" / "vida" | **IA** | las siglas cortas se oyen como palabras; el mismo modelo la escribe bien en otras frases |
| "como brix" | **como Brixly** (una marca inventada) | el recorte acotado sí oye la /s/ |
| "100. 1.5" | **105** | los números largos se parten; el recorte los saca enteros |
| "el local" | **en local** | empate acústico exacto: decide la gramática |

Ojo con `score.py`: la media es **por carácter**, así que favorece la cadena corta. Si una
hipótesis es más corta y gana por poco, manda lo que oye whisper sobre el recorte.

La palabra clave de una llamada a la acción (la que el espectador debe comentar) va **SIEMPRE EN
MAYÚSCULAS**.

**Corrige el texto ANTES de alinear.** El CTC alinea contra lo que le des: un texto malo arrastra
el error a las palabras vecinas. Al editar `words.json` por índice, **los índices se desplazan**
en cuanto insertas o fusionas: busca por contexto, no por número.

### 3 · Alinear (aquí salen los tiempos buenos)
Rellena el diccionario `SPOKEN` de `align.py` con **cómo suena** todo lo que no se lee como se
escribe: cifras (`"3.200"` a `"tres mil doscientos"`), marcas (`"Brixly"` a `"briksli"`, `"Nuvo.ai,"` a `"nuvo ei ai"`), siglas. Si te lo saltas, el número descuadra su bloque.
```bash
python3 align.py     # align.json: start/end por palabra + score CTC
```
Usa el modelo multilingüe `MMS_FA` de torchaudio, que trabaja sobre letras romanizadas: sirve para
español y otros idiomas con alfabeto latino. Para otros alfabetos, romaniza el texto en `SPOKEN`.
Los `score<0.5` en números y palabras función cortas son normales (el `SPOKEN` aproxima) y no
rompen nada: van rodeados de palabras con buen score. Un score bajo en una palabra larga y
aislada sí es señal de que el texto está mal.

### 4 · Bordes contra la envolvente
```bash
python3 verifica-bordes.py
```
El primer y el último subtítulo **no se dan por buenos**: whisper mete el ruido de sala en el
arranque. Un arranque real se ve como una subida sostenida de energía (por ejemplo −34 dB, −17 dB,
−9 dB en tres ventanas seguidas), no como un pico suelto de una silla o un chasquido de labios.

### 5 · Bloques de 2-3 palabras
```bash
FIRST_START=0.28 LAST_END=58.44 python3 blocks.py
```
Programación dinámica: penaliza bloques de 1 y de 4+ palabras, cerrar en palabra función, líneas
de más de 22 caracteres y duraciones fuera de 0,30-1,60 s. **Lee la primera pasada y arregla a
mano lo que chirríe** con `FORCE_BLOCKS` / `FORCE_CUTS` (índices de `align.json`): un bloque de 4
palabras está bien cuando la unidad semántica lo pide ("fuera de Estados Unidos,"), y partir un
precio en "a 12" / "o 15" está mal aunque el coste salga menor. La lista `FUNC` de `blocks.py` son
las palabras función del español: adáptala si trabajas en otro idioma.

### 6 · Afinar cada frontera a la envolvente
```bash
python3 snap.py
```
En `[-0,20 s, +0,05 s]`: si hay un hueco real (< −25 dB) el corte cae **dentro del silencio**; si
es habla continua, lead-in fijo de 100 ms. Ningún bloque baja de 0,28 s. Esto evita ver un bloque
cambiar a media sílaba.

---

## Montar el MOV

`kit/subtitulos.tpl.html` (ya copiada a `subtitulos/index.html`) es la plantilla. Solo se tocan:

- el array `STARTS` (lo escupe `blocks.json`, con comentarios `// HOOK`, `// DATO`... de marcadores)
- `LAST_END` y los dos `data-duration` (= final + ~0,06 s de cola)
- el comentario de cabecera: **qué se corrigió y por qué** (es el registro del reel)

Nada más. La caja negra va a `y = 2480 px`, Inter Variable peso 390 a 120 px, cortes secos
encadenados (`tl.set` opacity 1 en su start, 0 en el start del siguiente). **Sin fade**: un
fundido en subtítulos se lee como retraso. La banda de subtítulos es una decisión de estilo: si
cambias su posición o tipografía, cambia también la banda reservada en `layout-clips.md` y en
`kit/check.py`.

```bash
cd subtitulos && npx hyperframes lint
PRODUCER_ENABLE_CHUNKED_ENCODE=true npx hyperframes render \
  --workers 1 --format mov --fps 60 --output ../ENTREGA/<reel>-SUBTITULOS-ALFA.mov
```
Sin `--workers 1` captura a disco (~100 GB en un reel de un minuto).

Comprobación final: `pix_fmt` debe ser `yuva444p12le` (si sale `yuv420p`, el alfa se perdió) y
`nb_frames` = duración x 60.
