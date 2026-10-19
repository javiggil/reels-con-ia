---
name: recortar-silencios
description: "Recorta los silencios de un vídeo talking-head y además lo LIMPIA: quita los golpecitos y ruidos sin voz y las RETOMAS (cuando te equivocas y repites la frase, se queda solo el último intento), y te lo entrega como timeline de Final Cut Pro: un .fcpxml no destructivo que referencia tu media original (cero reencode, no toca el archivo), listo para importar y afinar en FCP, con un segundo proyecto «· descartes» con lo quitado por si hay que recuperar algo. Silencios con auto-editor en agresivo por defecto (umbral 12%, margen 0.02s, cortes 0.05s,0.03s); golpecitos con el VAD de voz de whisper.cpp; retomas transcribiendo cada bloque de habla por separado con whisper y comparando con los siguientes; y una revisión de Claude sobre la tabla de tomas antes de entregar. Nombre de proyecto a tu gusto (p.ej. dia-0018), MP4 de preview a 1080p del montaje limpio, reporte antes→sin pausas→limpio. Úsala cuando el usuario tenga una grabación hablando a cámara (reel, tutorial, clase, take largo) con pausas, intentos repetidos y golpes y quiera el hilo limpio montado en Final Cut sin cortar a mano. Dispara con: recorta los silencios de este vídeo, quítame las pausas, quítame las repeticiones, déjame solo las tomas buenas, pásamelo a Final Cut ya cortado, limpia el talking-head, auto-editor a fcpxml."
argument-hint: "[ruta al vídeo] [--nombre dia-0018] [--out archivo.fcpxml] [--molde export.fcpxmld] [--mp4] [--solo-silencios] [--suave] [--umbral 12%] [--margen 0.02s] [--smooth 0.05s,0.03s] [--idioma es] [--fps auto] [--legacy]"
user-invocable: true
---

# Recortar silencios y retomas → Final Cut Pro

Coge una grabación talking-head con pausas, intentos fallidos y golpecitos y te devuelve un **timeline de Final Cut con el hilo limpio**: un `.fcpxml` que referencia tu media original por ruta absoluta, solo con los trozos buenos. **No es destructivo**: no reencoda ni toca el vídeo original.

Lo que harías a mano después de recortar silencios (ir borrando los clips que no son definitivos) lo hace la skill en tres capas:

1. **Silencios**: `auto-editor` por volumen, en agresivo por defecto.
2. **Golpecitos**: los clips de 0,05-0,15 s que deja auto-editor por un golpe en la mesa, un chasquido o un roce. Se quitan los que caen fuera de voz según el VAD silero de whisper.cpp (un golpe da 0 % de voz; una sílaba corta de verdad, como el «fac-» de «factura», cae dentro y se queda).
3. **Retomas**: cuando te equivocas y vuelves a decir la frase, **se queda el último intento** y fuera los anteriores. Cada bloque de habla (clips seguidos sin pausa de 0,4 s) se transcribe **por separado** con whisper, y un bloque cuyo texto reaparece al arranque de uno de los 4 siguientes es un intento fallido. Por separado a propósito: whisper sobre el audio entero deduplica las repeticiones y las esconde.

Después **Claude revisa la tabla de tomas** (ver abajo) y corrige lo que la heurística no ve, antes de entregar.

Calibrado contra una toma real (bruto de 2:26, montado a mano en 0:47): la skill quitó los mismos 8 golpecitos y las mismas 5 retomas que el montaje a mano, y solo dejó «De todas formas,» (un arranque en falso sin repetición), que sale marcado con ⚠ para la revisión.

## Qué hace / qué no

- **Hace:** recorta silencios, quita golpecitos y retomas, exporta el `.fcpxml` con dos proyectos (`<nombre>` limpio y `<nombre> · descartes` con lo quitado, cada clip rotulado con el motivo), la tabla de tomas y, con `--mp4`, un preview a 1080p del montaje limpio.
- **No hace:** no corta dentro de un clip. Si repites una frase **sin pausa** entre medias (en el mismo clip de auto-editor), la retoma no se separa: queda para FCP. No reencoda el master ni toca el fuente. No elige entre dos versiones distintas de una frase dichas con otras palabras: eso lo ve la revisión.

## Requisitos

- **auto-editor** por Homebrew (NO por pip, que da una versión vieja con flags obsoletos): `brew install auto-editor`
- **ffmpeg/ffprobe**, **xmllint** (viene en macOS) y **python3**.
- **whisper.cpp** (`brew install whisper-cpp`: trae `whisper-cli` y `whisper-vad-speech-segments`) con el modelo `ggml-large-v3.bin` y el VAD `ggml-silero-*.bin`. Los busca en `~/.cache/hyperframes/whisper/models`, `~/whisper-models` y `/opt/homebrew/share/whisper-cpp`; otra ruta con `RECORTAR_WHISPER_MODEL` / `RECORTAR_WHISPER_DIR`. Sin el VAD, los golpecitos se detectan solo por duración (<0,1 s).
- macOS + Final Cut Pro para importar.

Si falta whisper o python3, la skill avisa y entrega solo el recorte de silencios.

## Rutas fijas

- Scripts: ``<carpeta-de-la-skill>/scripts/recortar.sh` (todo el flujo) y `limpiar.py` (la limpieza y sus ajustes). La carpeta es donde vive este SKILL.md: Claude Code te la dice al cargar la skill como "Base directory".
- Salida (junto al vídeo, o donde diga `--out`): `<nombre>.fcpxml` limpio, la carpeta `<nombre>-tomas/` con `tomas.md` (la tabla), `tomas.json` y `silencios.fcpxml` (el timeline solo-silencios, también importable), y con `--mp4`, `<nombre>-preview.mp4`.

## El flujo (en orden)

1. Localiza la ruta del vídeo (si está en un volumen externo, que esté montado).
2. Corre `recortar.sh` (≈40 s de whisper para un bruto de 2-3 min, más el preview si lo pides).
3. **Revisa las tomas** (la sección siguiente). No te la saltes: es lo que convierte la heurística en el hilo bueno.
4. Si cambias algo, `limpiar.py aplicar` y, si el usuario quiere preview, `limpiar.py preview`.
5. Dale al usuario: duración final, qué se ha quitado en una línea por retoma, y la ruta del `.fcpxml`. Se importa en Final Cut con **Archivo > Importar > XML…**.

## Revisión de tomas (la hace Claude, siempre)

Lee `<nombre>-tomas/tomas.md`. Cada fila es un bloque de habla: `✓` se queda, `✗` se va (con el motivo), `⚠` se queda pero hay que mirarlo. Debajo, los golpecitos quitados. Las retomas literales salen solas; las reformuladas y los arranques en falso salen como ⚠ y son trabajo de la revisión.

1. **Lee seguidos los bloques ✓.** Tienen que sonar como el vídeo de un tirón, sin una frase dicha dos veces. Si dos bloques ✓ dicen lo mismo con otras palabras (retoma reformulada que la similitud no pilla), quita el **primero**.
2. **Cada ✗ retoma:** comprueba que el bloque que la sustituye dice la frase completa. Si el intento quitado tenía un arranque que el bueno no repite (p.ej. el intento fallido es «y tú puedes copiarle el sis-» y el bueno empieza en «copiarle el sistema»), ese bloque se queda: `--mantener`.
3. **Cada ⚠ «¿arranque en falso?»:** un bloque de ≤3 palabras justo antes de una retoma. Si es una muletilla o un arranque que no engancha con lo que sigue («De todas formas,» antes de volver a empezar), quítalo. Si es parte de la frase («Y tú.» seguido de «puedes copiarle…»), déjalo.
4. **Cada ⚠ «¿retoma reformulada?»:** arranca con las mismas dos palabras que el bloque siguiente. Si es el mismo mensaje dicho otra vez con otras palabras, quita el primero; si son dos frases distintas que empiezan igual («Así que…»), déjalo.
5. **Bloques sueltos sin sentido** (una palabra rota, «Ya.», un «eh») que no pertenecen al hilo: fuera.
6. Si el usuario tiene el guion del vídeo y hay duda sobre cuál es el hilo, sirve de referencia. Al grabar se improvisa: **manda lo grabado**, el guion solo desempata.
7. Aplica los cambios por id (bloques `B12`, clips sueltos `s40`):
   ```bash
   python3 <carpeta-de-la-skill>/scripts/limpiar.py aplicar "<nombre>-tomas" "<nombre>.fcpxml" --quitar B24 --mantener B5
   ```
   Es idempotente (parte siempre de `silencios.fcpxml`) y guarda las decisiones a mano en `tomas.json`, así que se puede encadenar. Si se pidió preview, regenéralo después:
   ```bash
   python3 <carpeta-de-la-skill>/scripts/limpiar.py preview "<nombre>-tomas" "/ruta/al/video.mov" "<nombre>-preview.mp4"
   ```

En la duda entre quitar y dejar, **deja**: borrar un clip de más en FCP es un clic; recuperar uno quitado obliga a ir al proyecto de descartes.

## Uso (comandos literales)

Caso típico (nombre del episodio, salida concreta, todo limpio):
```bash
<carpeta-de-la-skill>/scripts/recortar.sh "/ruta/al/video.mov" \
  --out "/ruta/dia-0018.fcpxml" --nombre "dia-0018"
```

Con el molde de tu Final Cut (a prueba de crash, ver abajo) y preview:
```bash
<carpeta-de-la-skill>/scripts/recortar.sh "/ruta/al/video.mov" \
  --molde "$HOME/Downloads/export.fcpxmld" --out "/ruta/dia-0018.fcpxml" --nombre "dia-0018" --mp4
```

Solo silencios, sin tocar golpecitos ni retomas (el comportamiento antiguo):
```bash
<carpeta-de-la-skill>/scripts/recortar.sh "/ruta/al/video.mov" --solo-silencios
```

Audio con ruido de fondo o que se come palabras (recorte menos agresivo):
```bash
<carpeta-de-la-skill>/scripts/recortar.sh "/ruta/al/video.mov" --suave
```

Para una versión antigua de Final Cut (FCPXML 1.10): añade `--legacy`. Entrecomilla siempre las rutas (espacios, tildes, eñes).

## Presets y overrides

| Opción | Default | Cuándo tocarlo |
|---|---|---|
| `--umbral` | `12%` | Aún queda silencio → **súbelo** (15%). Se come palabras flojas → **bájalo** (8%, o `--suave`). |
| `--margen` | `0.02s` | Los cortes comen el inicio/fin de las palabras → **súbelo** (0.1-0.3s). |
| `--smooth` | `0.05s,0.03s` | Corte y clip mínimos: cero aire. `0.2s,0.1s` deja respiración entre frases. |
| `--suave` |: | El default antiguo: umbral 8%, margen 0.1s, cortes 0.1s,0.05s. Solo pisa lo que no fijes tú. |
| `--agresivo` |: | Ya es el default; se acepta por compatibilidad. |
| `--solo-silencios` |: | Sin limpieza de golpecitos ni retomas. |
| `--idioma` | `es` | Idioma de la grabación para whisper. |

Los umbrales de la limpieza viven arriba de `limpiar.py` (`HUECO_BLOQUE` 0,4 s, `VOZ_MIN` 30 %, `SIM_RETOMA` 0,72, `VENTANA` 4 bloques / 25 s). Calibrados con tomas reales; no los toques sin un caso que lo pida.

### Ojo: los silencios se recortan por VOLUMEN, no por voz

auto-editor decide por **volumen de audio**. Con **sonidos de fondo fuertes** en los tramos sin habla (música, ruido, ambiente al nivel de tu voz), el volumen no los distingue del habla: subir el umbral toca techo enseguida (probado: de 4% a 30% apenas cambia el recorte, y a partir de ahí trocea la voz). La capa de golpecitos (VAD de voz) quita los clips cortos sin voz, pero un tramo largo de ruido al nivel de la voz hay que cortarlo a mano en Final Cut.

## El reporte

- **Antes:** duración del bruto. **Sin pausas:** tras recortar silencios. **Después:** el timeline limpio.
- **Recortado (%):** cuánto se ha ido en total.
- **Segmentos:** clips del timeline limpio (los islotes que verás en FCP).
- **Limpieza:** cuántos clips fuera, cuántos por golpecito y cuántos bloques por retoma/ruido; y la ruta de `tomas.md`.

## Importar en Final Cut Pro

1. **File > Import > XML…** y elige el `.fcpxml`.
2. Aparecen dos proyectos en el mismo evento: `<nombre>` con el timeline **limpio** (sin pausas, golpecitos ni retomas) y `<nombre> · descartes` con lo quitado, cada clip rotulado con su id y su motivo (`s10 · retoma: lo repites en B6`). Si algo no debió irse, se copia de ahí.
3. La media enlaza al vídeo original por ruta absoluta. **No lo enlaza si lo has movido/renombrado** después de generar el `.fcpxml` → FCP pedirá relink.
4. FCPXML 1.11 por defecto (FCP reciente). Si tu Final Cut es antiguo y no importa, reejecuta con `--legacy` (1.10).

### Si Final Cut se cierra inesperadamente al importar

La skill ya blinda las **dos** causas típicas de crash, en automático:

1. **Orientación (la más traicionera, para vídeo vertical).** auto-editor escribe las dimensiones CODIFICADAS del vídeo (p.ej. 3840×2160). Si grabaste en vertical, el vídeo lleva rotación de 90° y Final Cut espera las de VISUALIZACIÓN (2160×3840); declarar el `<format>` horizontal cuando la media es vertical **hace crashear a FCP** al importar. La skill detecta la rotación con ffprobe y corrige el `<format>` a las dimensiones reales (y le quita el `name`, como hace el propio FCP).
2. **Frame rate no estándar.** Si auto-editor mide un rate raro (p.ej. ProRes de cámara a 59,99 fps) escribe `frameDuration="100/5999s"`, que también crashea. La skill **auto-conforma** al rate nominal (60/1 → `frameDuration="1/60s"`). Fuérzalo a mano con `--fps 60` (o `30`, `25`, `24`, `30000/1001`…) si hace falta.

Si un clip raro aún diera guerra, existe el **modo `--molde`, a prueba de crash** (ver abajo): importa sí o sí porque reutiliza el asset real de tu propio Final Cut, con su bookmark.

## Modo `--molde`: a prueba de crash (recomendado)

El motivo último del crash: Final Cut necesita que el `<asset>` lleve **su propio bookmark** (un marcador de seguridad de macOS que FCP genera al importar la media). No se puede fabricar a mano de forma fiable: un bookmark inventado también crashea. La solución robusta es dejar que FCP cree ese bookmark él mismo y reutilizarlo:

1. En Final Cut: **importa el clip** (Archivo > Importar > Media), **arrástralo a un proyecto nuevo** y luego **Archivo > Exportar XML…**. Guarda el `.fcpxmld` (p.ej. en Descargas).
2. Corre la skill pasándole ese export con `--molde`:
   ```bash
   <carpeta-de-la-skill>/scripts/recortar.sh "/ruta/al/video.mov" \
     --molde "$HOME/Downloads/export.fcpxmld" \
     --out "/ruta/dia-0020.fcpxml" --nombre "dia-0020"
   ```
3. La skill calcula los cortes con auto-editor e **injerta el timeline recortado sobre el asset real del molde** (con su bookmark, formato y orientación correctos). Sale un `.fcpxml` v1.14 validado contra el DTD de FCP.
4. Importa el `.fcpxml` resultante: **Archivo > Importar > XML…**. Entra sin cerrarse.

Notas del modo molde:
- El **export tiene que llevar el clip metido en un proyecto/timeline**. Si exportas la librería en seco (sin el clip colocado), el XML no trae `<asset>` ni bookmark y la skill avisa (`exit 4`): repite el export con el clip dentro.
- Si el molde tiene **varios clips**, la skill casa el asset por **nombre de fichero** (el del vídeo que le pasas). Con un solo clip no hay ambigüedad.
- En modo molde se **saltan** el renombrado y la corrección de orientación: el molde ya trae el `<format>` bueno. El nombre del proyecto lo pone `--nombre`.
- La limpieza (golpecitos y retomas) corre igual encima del timeline injertado: el proyecto de descartes reutiliza el mismo asset con su bookmark.
- Lo entrega en **FCPXML 1.14** (la versión del molde), no 1.11.

## Reglas de oro

- **No muevas ni renombres el vídeo original** entre generar el `.fcpxml` e importarlo: rompe el enlace de media.
- El `.fcpxml` es **no destructivo**: el original queda intacto; puedes regenerarlo mil veces con otros ajustes.
- Empieza por los presets; ajusta umbral/margen solo con motivo.
- El MP4 es un **preview** (media resolución): el render final lo saca FCP desde el original.
- Mover solo el `.fcpxml` a otra carpeta es seguro (la ruta de la media es absoluta).

## Casos borde

- **Vídeo sin silencios (todo habla):** conserva casi todo; el reporte lo dice ("apenas había silencios") y sale bien.
- **Sin habla / timeline vacío:** umbral demasiado alto o audio mudo → sale con aviso de bajar `--umbral`; no deja un `.fcpxml` vacío.
- **Audio multipista** (mic + cámara): auto-editor mide el audio principal; una segunda pista con ruido puede sesgar. Talking-head típico = una pista, no aplica.
- **Umbral desnudo** (`--umbral 4`): se auto-corrige a `4%` con aviso (un `4` a secas sería 400%).
- **Volumen externo:** que esté montado antes de correr (y de importar en FCP, porque la media vive ahí).
- **Falla la limpieza** (falta whisper, el modelo o python3): avisa y entrega el timeline solo con los silencios recortados (exit 0). `silencios.fcpxml` siempre queda en `<nombre>-tomas/`.
- **Retoma sin pausa** (repites dentro del mismo clip): no se separa; la verás en FCP. La revisión puede quitar el clip entero (`--quitar s40`) si el intento bueno está en otro.
- **Golpe pegado a una palabra** (dentro de un clip con voz): se queda; el VAD lo ve como voz.

## Errores y exit codes

| code | significado |
|---|---|
| 0 | OK, `.fcpxml` generado |
| 1 | uso / argumento inválido |
| 2 | el vídeo de entrada no existe |
| 3 | auto-editor no instalado (→ `brew install auto-editor`), o falta python3 en modo `--molde` (en `limpiar.py`: falta whisper-cli, ffmpeg o el modelo) |
| 4 | modo `--molde`: molde inválido (sin `<asset>`/`<format>`, o ningún clip casa con el vídeo) |
| 5 | sin habla detectada / timeline vacío (baja el umbral) |
| 6 | auto-editor falló al exportar (¿vídeo sin pista de audio?) |
