# Estilo de ejemplo: "hecho a mano"

Un **sistema visual completo como EJEMPLO** para que la skill produzca algo coherente desde el
primer reel. Es editorial sobre papel crema, con tinta cálida y un único acento que grita,
inspirado en el diseño editorial impreso. **No es obligatorio**: la estructura del kit (rejilla,
cámara, superficies, odómetro, partículas, cursor, losa ALFA) funciona con cualquier sistema.
Al final tienes "cómo hacer el tuyo".

Los valores viven en `kit/base.css` y `kit/demo.css` (variables en `:root`).

## Reglas duras
1. **Maximalismo disciplinado, regla 90/10**: 90 % layout editorial riguroso y neutros, 10 % sucio.
   **Una anotación a mano por beat** (más es scrapbook cutre). Solo la textura y el lettering son
   crudos; la rejilla no.
2. **Un único acento que grita**: vermillón `#fe4629`, como mucho el 15 % del frame; es
   **puntuación** (palabra clave, cifra, cursor). Índigo `#354B98` solo como 2ª tinta (sombra,
   círculo). Verde `#2ece7d` SOLO para "verificado" o éxito.
3. **El número es el héroe.** Cifras que suben (dinero, cuentas, seguidores, suscriptores): odómetro
   con flash verde y partículas. Una frase o dato puntual que no sube: slam estático (escala
   1,5 a 1 + blur 24 a 0 + flash + micro-shake).
4. **Movimiento = expo/power, nunca back/elastic/bounce en UI** (son tells de IA). Excepción: el
   cuerpo de una mascota si la hay (`back.out` <= 2.2).
5. **Nada de blanco puro ni negro puro** en el diseño (look frío): papel crema y tinta cálida.
   **Papel limpio y liso**: sin grano, speckle ni viñeta full-frame (en 4K enturbian y agrisan).
   Sin gradiente lineal full-screen (banding H.264); radial suave y claro, sin bajar del stop
   exterior `#ECE3D2`.
6. **Determinismo**: `feTurbulence` con `seed` fijo; jitter por mulberry32. Cero `Math.random`,
   `Date.now`, `rAF`.
7. **Anti-slop**: sin mesh-gradients violeta/azul, glassmorphism por todas partes, blobs 3D,
   sopa de emojis, arcoíris de secundarios ni glitch RGB. El riso es una 2ª tinta plana
   desplazada pocos píxeles, no un channel-split.

## Paleta
| Rol | Hex |
|---|---|
| Papel base / borde (radial) | `#F4EFE6` a `#ECE3D2` |
| Crema tarjetas / sellos | `#FBF7EE` · newsprint `#E8DFC8` · tape kraft `#E2D5B8` |
| Tinta texto (cálida, no negra) | `#1C1A17` · media/metadatos `#6A5C55` |
| Acento vermillón (≤15 %) | `#fe4629` |
| 2ª tinta índigo | `#354B98` |
| Verde verificado / texto verde legible | `#2ece7d` / `#1f9e5e` |
| Terminal (contraste de soporte) | `#151515` |

## Tipografía
Todas con licencia **OFL** (libres). No van en la skill: descárgalas.

- **Fraunces** (variable; ejes `opsz`, `SOFT`, `WONK`): titular editorial de alto contraste
  cálido. Itálica para eyebrows y sellos; peso 600-700 enorme para el hero.
  `font-variation-settings: "opsz" 144, "SOFT" 30, "WONK" 1`.
- **Anton**: display condensada negra para el número (odómetro, slam).
- **Inter** (variable): labels, UI, subtítulos.
- **JetBrains Mono**: terminal, datos, `[fuente]`, timestamps (la mono es la prueba de que el dato
  es real). La resuelve sola el CLI de HyperFrames.
- Sellos y rótulos en **Fraunces itálica**, con la palabra acento en itálica vermillón. Evita las
  fuentes tipo rotulador para sellos; una manuscrita (Caveat) solo para una nota mínima.
- Jerarquía: nunca dos familias en el mismo bloque vivo. Sentence case en titulares, no all-caps.

### Descargar las fuentes
1. Ve a `https://fonts.google.com/specimen/Fraunces`, `.../Anton` e `.../Inter` (o a
   `github.com/googlefonts` de cada familia) y descarga las variables.
2. Conviértelas a woff2 si vienen en ttf (`pip install fonttools brotli` y
   `fonttools ttLib.woff2 compress Fraunces.ttf`).
3. Guárdalas con estos nombres en `~/reels/_fuentes/`: `Fraunces-var.woff2`,
   `Fraunces-Italic-var.woff2`, `Anton.woff2`, `inter-var.woff2`. `nuevo-reel.sh` las copia a cada
   proyecto (`_kit/fonts/` y `subtitulos/fonts/`). Si cambias nombres, cambia los `@font-face`
   de `kit/base.css`, `kit/demo.css` y `kit/subtitulos.tpl.html`.

## Texturas y superficies (todas planas, sin blur)
- **Tarjeta die-cut**: borde crema + sombra DURA offset.
- **Superficie UI** (`.ui-card`): contorno de tinta 3 px + sombra dura + sombra de ambiente.
- **Washi tape**: kraft, multiply, rotado, cae con `power3.out`.
- **Pegatina**: cadena de drop-shadows crema (borde) + sombra dura.
- **Riso misregister**: copia índigo detrás, desplazada 6 px que baja a 1,5 px.
- **Sombra de imprenta**: `text-shadow: 5px 5px 0 #354B98`, sin blur.
- **Censura/pixelado**: mosaico real en canvas con nearest-neighbor, monocromo; no una rejilla CSS.

## Anotaciones a mano (una por beat)
- **Marcador**: franja vermillón opacidad ~0,42 tras la palabra clave, `scaleX 0 a 1`, skewX -2.
- **Círculo a boli**: path de elipse irregular que se DIBUJA (`stroke-dashoffset` a 0,
  `power2.inOut`), tinta índigo. Sin `back.out`.
- **Subrayado ondulado** bajo un dato, `power1.inOut`.
- **Sello**: entra grande y asienta sin rebote (`scale 1,5 a 1`, `power4.out`).

## Motion (eases)
`expo.out` / `power3.out` (entradas, slams, reveals) · `power4.out` / `power2.out` (asiento) ·
`power3.in` (salidas) · `none` (loops, marquee, tecleo `steps(N)`) · `sine.inOut` (idle).
Reveal por máscara: palabra en wrapper `overflow:hidden`, span `yPercent 110 a 0` con `expo.out`.

## Cómo hacer el tuyo

1. **Elige 3 cosas**: un papel o fondo (claro, oscuro, color plano), UNA tinta de texto y UN
   acento que grite. Todo lo demás son neutros. Decide también una 2ª tinta y un verde/rojo
   semánticos si los necesitas.
2. **Elige 2-3 familias**: una display para el número, una de titular, una de interfaz. Verifica
   que tienen licencia libre (OFL) y que puedes llevarlas a woff2.
3. **Cambia los tokens**: las variables de `:root` en `kit/demo.css` (`--paper`, `--ink`, `--verm`,
   `--ind`, `--ok`...) y los `@font-face` de `kit/base.css` y `kit/demo.css`. Busca los hex
   sueltos en `demo.js` (`Burst`, `CURSOR`, avatares) y en `check.py`.
4. **Escribe 5-7 reglas duras** como las de arriba: qué nunca se hace (tu anti-slop), cuánto
   ocupa el acento, qué eases usas, qué número es héroe y cómo entra.
5. **Define tu superficie UI**: contorno, sombra, radio. Con `.ui-card` y `.slab` cambias el
   carácter de todo el clip.
6. **Valida con un hook**: monta el clip más difícil primero (`demo-opaco-hook.html` como
   plantilla), mira la `HOJA.png` y ajusta el sistema antes de repartir el resto.
7. **Anótalo en el brief** (`brief-plantilla.md`, sección Estilo) para que cada reel parta de él.

Si tu estilo no usa papel claro, ten en cuenta que los ALFA van sobre su propia losa: la losa
manda el contraste, no el fondo del vídeo del creador.
