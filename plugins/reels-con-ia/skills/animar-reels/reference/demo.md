# Estilo DEMO: el lenguaje de movimiento de los clips

Los clips del reel son **motion graphic tipo vídeo de demo de app**: grandes, muy dinámicos, con
cámara que viaja por un lienzo infinito. El **sistema visual** (colores, tipografías) es
intercambiable (`estilo-ejemplo.md`); lo que se describe aquí es el **lenguaje de movimiento** y
las herramientas del kit.

Kit: `kit/demo.css` + `kit/demo.js` (los copia `nuevo-reel.sh` a `_kit/` y `scaffold.sh` a cada
clip). Ejemplos con datos ficticios en `examples/`:

| Ejemplo | Qué enseña |
|---|---|
| `examples/demo-opaco-hook.html` | OPACO con ventana corta (hook: título arriba), cámara con giro y motion blur, escáner, avatares que vuelan en arco, copia del sistema arrastrada por el cursor |
| `examples/demo-opaco-prompt.html` | OPACO con ventana alta, texto largo quieto y legible |
| `examples/demo-alfa-losa.html` | ALFA: losa horizontal con cámara local, odómetro, monedas y billetes, prueba del cálculo en mono |

---

## 1 · Los ingredientes (todos en `demo.js`, todos seek-safe)

| Ingrediente | API | Para qué |
|---|---|---|
| Lienzo infinito con **rejilla de puntos** | `.dots` dentro de `#dotcam` | la rejilla viaja con la cámara: al hacer zoom los puntos crecen y se nota el espacio |
| **Cámara v2** | `D.Cam(el, FX, FY, init, mirror, mFY)` · `view.fly(tl, {cx,cy,s,r}, t, dur, ease, blur)` | prezi con **giro** (`r`) y **motion blur** en los whips (`blur` 1,2-3,2 px) |
| Superficies UI | `.ui-card` / `.ui-card.soft` · `.ui-bar` | contorno de tinta 3 px + sombra dura + sombra de ambiente. Grandes: llenan el ancho útil |
| **Entrada 3D** | `D.enter3d(tl, el, t, {rx, ry, z, x, y, dur})` | la superficie llega desde profundidad y se asienta plana |
| **Brillo** | `.sheen` + `D.sheen(tl, el, t, dur)` | barrido de luz sobre la superficie al asentarse |
| **Odómetro** | `D.Odometer(el, '000')` y `.render(v)` en `render()` | toda cifra que sube, dígito a dígito (tipografía display) |
| **Partículas** | `D.Burst(parent, {x,y,t0,n,shape,colors,...})` y `.update(t)` | monedas, chispas, billetes, puntos; mulberry32 con `seed` |
| Pulso | `.ring` + `D.pulse(tl, el, t)` | confirmar un impacto |
| Pop / sello | `D.pop` · `D.stamp` | chips, badges, ticks (sin rebote) |
| Trazo | `D.draw(tl, path, t, dur)` | cables, círculos a mano, subrayados |
| **Cursor** | `D.CURSOR` en `.cursor` + proxy `{x,y,show,press}` | clic real en la UI (publicar, suscribirse, arrastrar) |
| Avatares genéricos | `D.avatar(i)` | gente sin cara real ni nombre inventado |
| **Mascota (opcional)** | `D.Mascot(box, {x,y,w,talk})` y `.render(t)`; proxies `k, hop, sq, lean, look, boost` | un personaje que actúa con la voz: salta, se encoge, mira, "habla". Ver abajo |
| Estado inicial | `D.hide(tl, targets, vars)` | todo lo que entra después (ver trampa 1) |
| Resplandor local | `.glow` (`.amber`, `.green`, `.ind`) | nunca full-frame |

### Mascota opcional
Si el brief define una mascota: guarda su SVG o PNG como `kit/mascota.svg` (hay un
`kit/mascota-ejemplo.svg` para probar), pon `<div class="mascota-box" id="mbox"><!--MASCOT--></div>`
**fuera de `#cam`** y crea `var mas = D.Mascot($('mbox'), {x, y, w, talk:[[0.1,0.9]]})`; llama
`mas.render(t)` en `render()`. Anímala con tweens sobre `mas.k` (aparece/desaparece), `mas.hop`
(salto), `mas.sq` (encogerse con una mala noticia), `mas.look` (mirar a un lado), `mas.boost`
(propulsión). `x,y` es su centro en coordenadas de pantalla. Sin mascota, no pongas el
contenedor y omite la llamada: el resto del kit no depende de ella. `inject.py` quita el marcador
si no hay `mascota.svg`.

## 2 · Cómo se ve un buen clip demo

- **Grande.** El elemento principal ocupa 700-840 px de ancho en espacio 1080. Si en la hoja hay
  mucho papel vacío alrededor, está pequeño.
- **Una idea por beat de voz, y se ve pasar.** Cada frase dispara una acción visible (algo entra,
  vuela, se enciende, se cuenta). La cámara viaja entre ellas sin cortes.
- **Tiene física.** Cosas que vuelan en arco de A a B (`sin(pi*u)`), que se apilan, que se
  conectan con cables que se dibujan, que se sacuden al impactar (micro-shake), monedas que caen.
- **UI de verdad, sin texto de relleno.** Barras en vez de frases falsas; rótulos solo de interfaz
  y en el idioma del reel. Logos vectoriales en `kit/parts/`.
- **Poco texto, extremadamente visual:** la voz ya explica.
- **Remate con zoom out** que enseña cómo encaja todo.
- **Cero cortes ni wipes**: es UN lienzo y una cámara. Cada zoom debe relacionar (entras a un
  detalle que ya se veía; sales y ves dónde encajaba). Eases suaves y largos (`power2.inOut`,
  `power3.inOut`); nunca back/elastic en la cámara ni en UI.
- **Una anotación a mano por beat**, no más.

## 3 · Las dos plantillas

### OPACO (tapa la cara)

```html
<div class="paper"></div>
<div class="world">
  <div id="dotcam"><div class="dots"></div></div>          <!-- rejilla a pantalla completa -->
  <div id="vp">                                              <!-- ventana con bordes fundidos -->
    <div id="cam"><div id="canvas"> ... todo el lienzo ... <div class="mascota-box" id="mbox"><!--MASCOT--></div></div></div>
  </div>
  <div class="cursor" id="cur"></div>                        <!-- el cursor, en coords de PANTALLA -->
</div>
```
```js
var VPTOP = 190, FX = 480, FY = 710;                         // clip normal: ventana alta
var view = D.Cam($('cam'), FX, FY - VPTOP, {cx:..., cy:..., s:1}, $('dotcam'), FY);
```
- **Clip normal:** `#vp{top:190px;height:1040px}`, `FY = 710`.
- **Hook:** si el creador pone un título arriba, ventana corta, `#vp{top:570px;height:660px}` (es
  el default de `demo.css`), `FY = 900`. Nada por encima de y 570.
- La ventana deja **siempre** libre la banda de subtítulos (y > 1240) y, en el hook, el título.

### ALFA (sobre su cara): HORIZONTAL

```html
<!-- html,body{background:transparent}; sin .paper, sin #dotcam ni #vp -->
<div class="world">
  <div class="slab" id="slab" style="left:60px;top:400px;width:840px;height:470px">
    <div class="dots" ...></div>
    <div id="cam"> ... </div>                                <!-- cámara LOCAL: FX 420, FY 235 -->
  </div>
</div>
```
- La losa es **más ancha que alta** y la animación **se desarrolla de izquierda a derecha**
  (paneos horizontales).
- En t = 0 la losa ya está; solo se asienta (`scale .975 a 1`, `y 12 a 0`).
- La mascota va dentro de la losa o asomando por su borde (x 60-900, y 330-940).

## 4 · Trampas del estilo

1. **`tl.set(..., 0)` solo no pinta el fotograma 0.** El render arranca con el cabezal en 0 y ese
   set no se aplica: lo que debía estar oculto sale en el primer fotograma (el lint lo marca como
   `gsap_timeline_set_initial_hide`). Estados iniciales con **`D.hide(tl, ...)`** (`gsap.set`
   inmediato + `tl.set` para rebobinar). Compruébalo en el MP4 real, fotograma 0.
2. **Trazo con `linecap:round` pinta un punto antes de dibujarse.** Con `strokeDashoffset =
   longitud`, el remate redondo asoma como un punto suelto. Ocúltalo con `opacity:0` y enciéndelo
   (`tl.set opacity:1`) justo cuando empieza a dibujarse.
3. **Clonar DOM (una "copia del sistema")**: el clon pierde los `id`. Todo el estilo tiene que ir
   por **clase**, y los selectores de la timeline acotados al original (`#cms .cm`, no `.cm`), o
   animas también el clon.
4. **`D.Burst` con `n:0`** saca 18 partículas en versiones viejas del kit. Para apagar una
   ráfaga, `t0` fuera del clip (`t0:99`).
5. **Motion blur solo en el vuelo.** `view.fly(..., blur)` lo sube y lo baja en la misma ventana;
   un `mb` que se queda > 0 deja el plano borroso.
6. **El cursor vive fuera de `#cam`** (coordenadas de pantalla): conviértelo con
   `toScreen(px,py) = {x: FX + s*(px-cx), y: FYpantalla + s*(py-cy)}` en `render()`.
7. **Odómetro a medio rodar**: en snapshot parece roto, en movimiento se lee bien. Que la cifra
   final quede **quieta >= 0,4 s**.
8. **Cifras de dinero o cuentas que suben:** odómetro (+ flash verde y partículas si procede), no
   un slam estático. Un dato puntual que no sube (un "0") sí puede entrar con slam.

## 5 · Cómo se reparte el trabajo (12 clips en ~1 h)

1. El agente principal hace los subtítulos, el reparto (`duraciones.py`), los assets de marca (un
   subagente aparte) y **el hook él mismo**: fija el listón visual y ajusta el kit si hace falta.
2. Con el hook bueno, **subagentes en paralelo de 2-3 clips cada uno**, con un brief común (las
   reglas de §3 y §4, geometría OPACO/ALFA, "autora en `_src/index.src.html`, no toques `_kit/`")
   y por clip: tipo, duración, tiempos de voz relativos y qué se ve en cada beat.
3. El agente principal **mira cada `HOJA.png`** (y pide sus propios fotogramas si la del subagente
   es corta) y va renderizando por tandas con `_kit/render-some.sh <clip> ...` mientras llegan los
   demás.
4. Al final: `verifica-render.sh`, **hoja de fotogramas 0 reales** de todos los clips y preview
   global.
