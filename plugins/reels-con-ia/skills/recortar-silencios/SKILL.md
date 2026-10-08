---
name: recortar-silencios
description: "Recorta todos los silencios de un vídeo talking-head y te lo entrega YA TRIMADO como timeline de Final Cut Pro: un .fcpxml no destructivo que referencia tu media original (cero reencode, no toca el archivo) con los cortes ya hechos, listo para importar y afinar en FCP. Envuelve auto-editor con presets agresivos por defecto (umbral 8%, margen 0.1s, cortes mínimos 0.1s,0.05s: cero aire) para que no tengas que tocar ni un flag, con overrides opcionales, un nombre de proyecto a tu gusto (p.ej. dia-0018), un MP4 de preview a 1080p para revisar los cortes a ojo antes de importar, y un reporte limpio de duración antes→después, tiempo recortado y número de segmentos. Úsala cuando el usuario tenga una grabación hablando a cámara (tutorial, clase, reel, vlog, take largo) llena de pausas y muletillas y quiera dejar solo cuando habla y montarlo en Final Cut sin cortar a mano. Dispara con: recorta los silencios de este vídeo, quítame las pausas, déjame solo cuando hablo, pásamelo a Final Cut ya cortado, limpia el talking-head, auto-editor a fcpxml."
argument-hint: "[ruta al vídeo] [--molde export.fcpxmld] [--agresivo] [--umbral 8%] [--margen 0.1s] [--smooth 0.1s,0.05s] [--fps auto] [--nombre dia-0018] [--legacy] [--mp4] [--out archivo.fcpxml]"
user-invocable: true
---

# Recortar silencios → Final Cut Pro

Coge una grabación talking-head llena de pausas y te devuelve un **timeline de Final Cut ya cortado**: un `.fcpxml` que referencia tu media original por ruta absoluta, con solo los trozos donde hablas. **No es destructivo**: no reencoda ni toca el vídeo original; genera una lista de cortes que FCP importa como proyecto editable.

Envuelve **`auto-editor`** (detecta los silencios por volumen de audio) con presets calibrados para que no tengas que tocar ni un flag. El entregable es el `.fcpxml`; el MP4 es solo un preview opcional.

## Qué hace / qué no

- **Hace:** detecta silencios por audio, elimina las pausas y exporta un `.fcpxml` (timeline FCP) que apunta al original. Opcionalmente un MP4 de preview a 1080p. Reporte de cuánto ha recortado.
- **No hace:** no reencoda el master (el corte fino y el render final los haces en FCP), no toca el archivo fuente, no está pensada para mezclas multipista complejas ni para edición fotograma a fotograma. No corta por contenido/palabras (es por volumen); para audio muy ruidoso, sube el umbral.

## Requisitos

- **auto-editor** por Homebrew (NO por pip, que da una versión vieja con flags obsoletos):
  ```bash
  brew install auto-editor
  ```
- **ffprobe** (viene con ffmpeg, ya instalado) para el "antes" del reporte, y **xmllint** (viene en macOS) para el "después". Si falta ffprobe, el reporte se degrada pero el `.fcpxml` sale igual.
- macOS + Final Cut Pro para importar.

Comprobación rápida: `command -v auto-editor` (si no imprime nada → falta instalarlo).

## Rutas fijas

- Script: `<carpeta-de-la-skill>/scripts/recortar.sh` (la carpeta donde vive este SKILL.md: Claude Code te la dice al cargar la skill como "Base directory")
- Salida por defecto (junto al vídeo): `<nombre>-cortado.fcpxml` y, con `--mp4`, `<nombre>-preview.mp4`.

## El flujo (en orden)

1. Localiza la ruta del vídeo (si está en un volumen externo, que esté montado).
2. Corre el script con los presets (o con overrides si el audio lo pide).
3. Lee el reporte: antes→después, % recortado, nº de segmentos.
4. (Opcional) `--mp4` para eyeballar los cortes antes de importar.
5. Importa el `.fcpxml` en Final Cut: **File > Import > XML…**. El timeline llega ya cortado.

## Uso (comandos literales)

Caso por defecto, el `.fcpxml` sale junto al vídeo:
```bash
<carpeta-de-la-skill>/scripts/recortar.sh "/ruta/al/video.mov"
```

Con nombre de episodio y ruta de salida concretos (así entra en FCP llamado `dia-0018`):
```bash
<carpeta-de-la-skill>/scripts/recortar.sh "/ruta/al/video.mov" \
  --out "/ruta/dia-0018.fcpxml" --nombre "dia-0018"
```

Audio con ruido de fondo (recorta menos, más conservador) y con preview MP4:
```bash
<carpeta-de-la-skill>/scripts/recortar.sh "/ruta/al/video.mov" \
  --umbral 5% --margen 0.3s --mp4
```

Que no quede ni rastro de silencio (preset extra sobre el default agresivo):
```bash
<carpeta-de-la-skill>/scripts/recortar.sh "/ruta/al/video.mov" --agresivo
```

Para una versión antigua de Final Cut (FCPXML 1.10):
```bash
<carpeta-de-la-skill>/scripts/recortar.sh "/ruta/al/video.mov" --legacy
```

Entrecomilla siempre las rutas (espacios, tildes, eñes).

## Presets y overrides

| Preset | Default | Cuándo tocarlo |
|---|---|---|
| `--umbral` | `8%` (agresivo por defecto) | Aún queda silencio → **súbelo** (10-12%, o usa `--agresivo`). Se come palabras flojas → **bájalo** (4-6%). |
| `--margen` | `0.1s` | Los cortes suenan bruscos o comen el inicio/fin de las palabras → **súbelo** (0.3-0.5s). Recortar aún más pegado → **bájalo** (0.05s). |
| `--smooth` | `0.1s,0.05s` | Corte y clip mínimos, ya sin apenas aire. Sube a `0.2s,0.1s` si quieres dejar algo de respiración entre frases. |
| `--agresivo` |, | Preset extra sobre el default: umbral 12%, margen 0.02s, cortes 0.05s,0.03s. Cero aire entre frases (más troceado). Solo pisa lo que no fijes tú. |

Regla: el default ya recorta agresivo (sin apenas aire). Si aún queda silencio, usa `--agresivo`; si sigue sin bastar, sube `--umbral` a mano (10-15%), salvo que el problema sea ruido de fondo fuerte (ver más abajo, ahí subir el umbral toca techo).

### Ojo: recorte por VOLUMEN, no por voz

auto-editor decide por **volumen de audio**, no reconoce voz. Si tienes **sonidos de fondo fuertes** en tramos donde no hablas (música, ruido, ambiente al nivel de tu voz), el volumen NO puede distinguirlos del habla: subir el umbral toca techo enseguida (probado: de 4% a 30% apenas cambia el recorte, y a partir de ahí trocea la voz). En ese caso el aire de fondo hay que cortarlo a mano en Final Cut, o marcar tú los tramos. La detección por voz real (whisper/VAD) tampoco los aísla de forma fiable cuando el fondo es tan fuerte como la voz.

## El reporte

- **Antes / Después:** duración original vs. la del timeline cortado (`ffprobe` + suma de los `asset-clip` del `.fcpxml`).
- **Recortado (%):** cuánto silencio se ha ido.
- **Segmentos:** trozos de habla conservados (los "islotes" que verás en el timeline de FCP).

## Importar en Final Cut Pro

1. **File > Import > XML…** y elige el `.fcpxml`.
2. Aparece un proyecto (con el nombre que le diste con `--nombre`) con el timeline **ya cortado**: cada trozo de habla es un clip, las pausas ya no están.
3. La media enlaza al vídeo original por ruta absoluta. **No lo enlaza si lo has movido/renombrado** después de generar el `.fcpxml` → FCP pedirá relink.
4. FCPXML 1.11 por defecto (FCP reciente). Si tu Final Cut es antiguo y no importa, reejecuta con `--legacy` (1.10).

### Si Final Cut se cierra inesperadamente al importar

La skill ya blinda las **dos** causas típicas de crash, en automático:

1. **Orientación (la más traicionera, para vídeo vertical).** auto-editor escribe las dimensiones CODIFICADAS del vídeo (p.ej. 3840×2160). Si grabaste en vertical, el vídeo lleva rotación de 90° y Final Cut espera las de VISUALIZACIÓN (2160×3840); declarar el `<format>` horizontal cuando la media es vertical **hace crashear a FCP** al importar. La skill detecta la rotación con ffprobe y corrige el `<format>` a las dimensiones reales (y le quita el `name`, como hace el propio FCP).
2. **Frame rate no estándar.** Si auto-editor mide un rate raro (p.ej. ProRes de cámara a 59,99 fps) escribe `frameDuration="100/5999s"`, que también crashea. La skill **auto-conforma** al rate nominal (60/1 → `frameDuration="1/60s"`). Fuérzalo a mano con `--fps 60` (o `30`, `25`, `24`, `30000/1001`…) si hace falta.

Si un clip raro aún diera guerra, existe el **modo `--molde`, a prueba de crash** (ver abajo): importa sí o sí porque reutiliza el asset real de tu propio Final Cut, con su bookmark.

## Modo `--molde`, a prueba de crash (recomendado)

El motivo último del crash: Final Cut necesita que el `<asset>` lleve **su propio bookmark** (un marcador de seguridad de macOS que FCP genera al importar la media). No se puede fabricar a mano de forma fiable, un bookmark inventado también crashea. La solución robusta es dejar que FCP cree ese bookmark él mismo y reutilizarlo:

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

## Errores y exit codes

| code | significado |
|---|---|
| 0 | OK, `.fcpxml` generado |
| 1 | uso / argumento inválido |
| 2 | el vídeo de entrada no existe |
| 3 | auto-editor no instalado (→ `brew install auto-editor`), o falta python3 en modo `--molde` |
| 4 | modo `--molde`: molde inválido (sin `<asset>`/`<format>`, o ningún clip casa con el vídeo) |
| 5 | sin habla detectada / timeline vacío (baja el umbral) |
| 6 | auto-editor falló al exportar (¿vídeo sin pista de audio?) |
