# Layout de los clips: lo que cuesta iteraciones si no lo sabes

Espacio de autoría **1080x1920** dentro de `.world` (escala x2 a 2160x3840). Todas las
coordenadas de abajo están en ese espacio. Los valores son los del brief de ejemplo: ajústalos a
tus subtítulos y márgenes (`brief-plantilla.md`).

## El mapa de la pantalla

| Zona | y | Qué es |
|---|---|---|
| fuera | 0-120 | recorte de Instagram |
| **útil** | **200-1200** | aquí va TODO el contenido |
| banda de subtítulos | 1240-1330 | la caja negra. **Nada puede caer aquí** |
| cola | 1330-1920 | rail de likes, caption, UI de IG |

Horizontal: **x 60-900**. El centro seguro es **x = 480, no 540**: el rail de likes come la
derecha, así que la cámara prezi usa `FX = 480`. Ni el lint ni el `validate` cazan esto.

Un ALFA además va **entero sobre losa opaca**: sobre vídeo oscuro, la tinta sin losa se queda
hueca.

**Geometría del estilo demo** (detalle en `demo.md` §3):

| Tipo | Dónde vive el contenido | Cámara |
|---|---|---|
| OPACO normal | ventana `#vp` y 190-1230 | `FX 480`, `FY 710` |
| OPACO hook | ventana `#vp` y 570-1230 (título del creador arriba) | `FX 480`, `FY 900` |
| ALFA | losa horizontal x 60-900, y 400-870 | local a la losa: `FX 420`, `FY 235` |

## Las siete trampas

**1 · El frame 0 sale vacío (o con lo que debía estar oculto).** Un `fromTo(..., {opacity:0})` en
`t=0` deja el primer frame vacío, y en un corte duro eso se ve. El contenido principal **ya tiene
que estar puesto** en t=0: se anima solo un asiento (`fromTo("#slab", {scale:.975, y:12},
{scale:1, y:0})`), y lo que entra después son los hijos. Y al revés: un `tl.set(x, {autoAlpha:0}, 0)`
**no se pinta en el fotograma 0 del render**, así que lo que debía estar oculto asoma un
fotograma. Estados iniciales con `D.hide(tl, ...)` (gsap.set inmediato + tl.set). Los snapshots a
0,02 s no lo ven: se comprueba en el fotograma 0 del MP4/MOV.

**2 · GSAP borra la rotación del CSS.** `transform: scaleX(0) rotate(24deg)` + `gsap.to(scaleX)`
= la rotación desaparece sin error. Un tachón así **no se pinta y el lint pasa**. La rotación va
en el tween, no en el CSS:
```js
tl.fromTo("#tachon", { scaleX:0, rotation:24 }, { scaleX:1, rotation:24, ... })
```

**3 · `scaleY` sobre una barra deforma su texto.** Una barra que se aplasta a `scaleY:0.16` aplasta
la cifra que lleva dentro. El valor va **fuera** de la barra, y las barras comparten base con un
contenedor de altura fija:
```css
.pit { height:200px; position:relative }              /* la base común */
.bar { position:absolute; bottom:0; height:200px; transform-origin:50% 100% }
```

**4 · El eyebrow en versalitas mide el doble de lo que parece.** `letter-spacing:.16em` +
`uppercase`: un rótulo de 20 caracteres a 30 px se come 600 px, no 340. Si hay algo a su derecha,
chocan. Mídelo en el snapshot, no a ojo.

**5 · La cámara prezi deja elementos fuera de cuadro.** Con `translate(FX - cx*s, FY - cy*s)
scale(s)` y `transform-origin: 0 0`, el plano final tiene que **abarcar todo lo visible**:
`cx = (x_min + x_max)/2` y `s ≈ 840 / (x_max - x_min)`. Un `cx` copiado del plano anterior deja el
primer nodo fuera por la izquierda.

**6 · La mascota va FUERA de `#cam`** (si la usas). Sus `left`/`top` son coordenadas de
**pantalla**, no del canvas, así que la cámara no la mueve, pero por eso mismo choca con lo que sí
se mueve. Colócala mirando el **último** frame, donde todo está puesto. `D.Mascot` usa x,y como su
**centro**.

**7 · El último frame del snapshot sale vacío.** `hyperframes snapshot` en `t = duration` exacto
cae fuera del clip. Usa `--no-end` y pide el último a `duration - 0,01`.

## El bucle de trabajo

```bash
bash _kit/ver.sh clip-06-nombre                    # 5 frames repartidos
bash _kit/ver.sh clip-06-nombre "" "0.05,1.6,3.4"  # los beats que te interesan
bash _kit/ver.sh clip-08-nombre alfa               # compone sobre gris antes (ALFA)
```
Deja `snapshots/HOJA.png`: hoja de contacto con **la zona segura en azul y la banda de subtítulos
en rojo** dibujadas encima. Míralo en cada clip antes de renderizar.

**El preview global no es opcional.** Los snapshots por clip **no muestran la banda de subtítulos
con su texto real**: el único sitio donde ves si un rótulo choca es `_kit/preview.sh`, que
compone todo con tu audio. Ahí se comprueba también la sincronía, frame a frame contra el
subtítulo que toca.

## Ritmo

Un beat de voz = un elemento que entra. Los tiempos son **relativos al clip** (los da
`duraciones.py`). Entradas de 0,16-0,28 s, `expo.out` / `power3.out`. Los slams de cifra:
`power4.out` en 0,22-0,26 s + micro-shake del canvas (`x:-11, duration:0.05, yoyo:true, repeat:5`).

Encadenados sobre la misma propiedad: **deja 0,01 s de hueco** entre un tween y el siguiente, o el
lint saca `overlapping_gsap_tweens`.
