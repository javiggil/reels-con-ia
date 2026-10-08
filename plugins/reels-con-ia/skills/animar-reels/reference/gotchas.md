# Gotchas técnicos (HyperFrames, GSAP, render)

Cada uno cuesta de media una hora si no se conoce. Los de layout/clip están además en
`layout-clips.md` y `demo.md` §4.

## Sincronía y texto
- **Timestamps de whisper: nunca.** Van adelantados y de forma errática. Solo el texto sale de
  whisper; los tiempos, del CTC (`align.py`).
- **`-nfa` en `whisper-cli`**, o desactiva los timestamps finos sin avisar.
- **Cifras, siglas y marcas en `SPOKEN`** (`align.py`) o descuadran su bloque y arrastran a los
  vecinos.
- **El primer subtítulo no es de fiar**: ruido de sala. `verifica-bordes.py` pide energía sostenida.
- **Índices de `words.json` que se desplazan** al insertar o fusionar: edita por contexto.

## Render
- **`--workers 1` siempre.** Con varios workers HyperFrames captura frames a disco (~33 MB por
  frame con alfa); un reel de un minuto llena el volumen.
- **`PRODUCER_ENABLE_CHUNKED_ENCODE=true`** para renders largos de 4K/60.
- **El render con alfa no admite `--resolution`** (`outputResolution cannot be combined with
  alpha output`): hay que renderizar **nativo a 2160x3840**. Truco: `data-width/height` a
  2160x3840 y todo el contenido dentro de `.world{width:1080px;height:1920px;transform:scale(2);
  transform-origin:0 0}`; autoras en 1080x1920 y el texto/SVG rasteriza nítido a 4K real.
- **`html,body{background:transparent}`** en los ALFA, y sin `.paper` full-frame. Los efectos
  `multiply` (textura) no se ven sobre transparente: van dentro de paneles opacos.
- **Un stinger/overlay alfa**: primer y último frame 100 % transparentes.
- **Verifica el archivo real**: un clip congelado (GSAP no cargó) o un alfa perdido pasan lint,
  validate y snapshot. `verifica-render.sh` los caza.
- **GSAP local**: el render no debería depender de la red. `nuevo-reel.sh` baja
  `gsap.min.js` del CDN a `_kit/` una vez y `scaffold.sh` lo copia a cada clip.

## Determinismo (seek-safe)
- Cero `Math.random`, `Date.now`, `requestAnimationFrame`. El azar es `D.rng(seed)` (mulberry32).
- `feTurbulence` con `seed` fijo.
- Todo lo que dibujes en `render()` es función pura de `tl.time()`; la timeline va `paused:true`
  y se registra en `window.__timelines["id"]`.
- Sin `overwrite:"auto"` en los defaults de la timeline.

## GSAP
- **`tl.set(x, {autoAlpha:0}, 0)` no se pinta en el fotograma 0**: usa `D.hide(tl, ...)`.
- **GSAP borra la rotación del CSS** cuando tweeneas `scale`: la rotación va en el tween.
- **Tweens solapados sobre la misma propiedad**: 0,01 s de hueco o `overlapping_gsap_tweens`.
- **Pivotes SVG**: en un personaje SVG con piezas articuladas (brazos, ojos), usa `transform-box:
  view-box` + `svgOrigin` en GSAP. Con `fill-box` GSAP lee mal el pivote y la pieza sale disparada
  sin error. Solo se ve en un snapshot del frame exacto.
- **Cámara prezi**: `transform-origin: 0 0` obligatorio con la fórmula `translate(FX - cx*s,
  FY - cy*s) scale(s)`. Sin él, el error crece al alejar la escala de 1.

## HTML/CSS
- **`<video>` dentro de un clip**: SIEMPRE hijo directo de la raíz `.clip` (nunca dentro de
  wrappers ni de `#cam`, o renderiza en negro), `muted playsinline`, y lo posicionas a mano en
  `paint()` replicando la transformada de cámara.
- **Fuentes**: el CLI de HyperFrames resuelve solas algunas (Inter, JetBrains Mono, EB Garamond,
  Playfair Display, Montserrat, Oswald, Roboto, Lato, Poppins...). Las demás (Fraunces, Anton,
  Caveat) se declaran con `@font-face` y woff2 propio. Si el lint dice
  `font_family_without_font_face`, falta el `@font-face`.
- **Sin gradientes lineales full-screen** (banding H.264 en 4K): radial suave y claro.
- **Sin grano, speckle ni viñeta full-frame** en 4K: enturbian el papel. Si quieres textura,
  dentro de paneles pequeños.
- **Eyebrows en versalitas con tracking**: miden el doble de lo que parece.
- **`scaleY` sobre barras con texto dentro** deforma el texto.
- **Clonar DOM** pierde los `id`: estilo por clase.
- **Trazo con `linecap:round`** pinta un punto antes de dibujarse.

## Snapshot
- `hyperframes snapshot` en `t = duration` sale vacío: `--no-end` y pide `duration - 0,01`.
- Los snapshots por clip no muestran los subtítulos reales: el preview global sí.

## Honestidad y datos
- Cifra sin verificar no entra; cálculo propio se rotula como tal.
- No inventes productos, rankings ni nombres. Listados genéricos.
- Una cara real solo si la voz la presentó.
