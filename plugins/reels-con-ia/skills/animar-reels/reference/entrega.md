# Qué se entrega y en qué orden

Todo en `~/reels/<nombre>/ENTREGA/`.

```
<reel>-SUBTITULOS-ALFA.mov      ProRes 4444 · entra en 00:00:00:00
<reel>-clip-NN-slug.mp4         OPACO · cutaway a pantalla completa
<reel>-clip-NN-slug-ALFA.mov    ALFA  · overlay sobre su cara
_preview-sincronia.mp4          540x960 con su audio · para revisar, no para montar
MONTAJE.md · RECONCILIACION.md  (y VEO-PROMPTS.md si se usa un generador de vídeo)
```

Orden en la timeline del editor, de arriba abajo: **subtítulos, clips ALFA, su cara, clips
OPACOS**. Los OPACOS tapan la cara; los ALFA la dejan ver. Final Cut, Premiere y DaVinci
leen ProRes 4444 con alfa; en CapCut comprueba que tu versión respeta el alfa. Si no, usa solo
OPACOS o pide en el brief otro formato con alfa (por ejemplo WebM VP9).

## Antes de dar nada por bueno

```bash
bash <skill>/scripts/verifica-render.sh ~/reels/<nombre>
```
Caza los dos fallos que pasan lint, validate y snapshot:
- **clip congelado**: si GSAP no cargó, se renderiza un frame fijo y todo lo demás pasa. Cuatro
  frames con md5 distinto por clip, o hay que mirarlo.
- **alfa perdido**: `pix_fmt` tiene que ser `yuva444p12le` en los MOV.

Y las duraciones: `nb_frames` ≈ `data-duration` x 60, clip a clip.

Y el **fotograma 0 real** de cada clip, en una sola hoja (los ALFA compuestos sobre gris):
```bash
ffmpeg -i clip.mov -vf "select=eq(n\,0),scale=270:480" -frames:v 1 -pix_fmt rgba f0.png
```
Ninguno vacío, ninguno con algo que debía entrar después.

Luego el **preview global** (`_kit/preview.sh`) y una hoja de contacto de ~12 fotogramas
repartidos, comprobando que cada uno cuadra con el subtítulo que le toca.

---

## MONTAJE.md

Lo que el creador lee para montar. Cinco secciones:

1. **Subtítulos**: archivo, formato, entra en, dura.
2. **Animaciones**: tabla `# · archivo · ALFA/OPACO · entra (s) · TC 60 fps · dura · qué cuenta`.
   El TC en `00:MM:SS:FF` es lo que se teclea en el editor.
3. **Lo que NO se anima**: con sus timecodes, para que sepa qué hueco llena él.
4. **Antes de publicar**: las derivas que exigen decisión suya, marcadas "CRÍTICO" y "ATENCIÓN".
   Directo, sin suavizar: si se cayó un beat, se dice y se dice qué cuesta.
5. **Origen de lo que se ve en pantalla**: cada cifra y cada cita con su fuente, y lo que
   deliberadamente NO se puso.

## VEO-PROMPTS.md (opcional)

Solo si el brief prevé un generador de vídeo para planos sueltos. Ajustes comunes (9:16, máxima
resolución, 8 s, silenciar la pista), tabla de planos con frase que cubre + timecode + duración, y
un bloque de prompt por plano (vertical, sin texto, sin logos, sin diálogo ni música). Cierra con
los planos opcionales para tramos sin animar, indicando **debajo de qué clip** irían.

## RECONCILIACION.md

El registro del reel. Seis secciones:

1. Lo que dijo, literal.
2. Las correcciones al ASR, con **cómo se decidió cada una** (recorte, score, gramática).
3. Lo que se cayó respecto al guion.
4. Lo que cambió respecto al guion.
5. Las cifras con su origen y estado: verificado / cálculo propio / no entró.
6. Nota sobre elementos raster o externos usados (logos, fotos recortadas) y su procedencia.

Es lo que hace auditable la entrega meses después. No se resume.

## Derivas de grabación

El creador cambia cosas al grabar. La entrega sigue **lo que dijo**, no lo que estaba escrito, pero
todo se registra en `RECONCILIACION.md` y se avisa en `MONTAJE.md`:

- **Beat caído al final** (una pregunta, un gancho al siguiente vídeo): se reporta, no se
  compensa. Solo entra regrabando.
- **Aviso o letra pequeña caída**: se compensa en pantalla, en el clip donde aplica.
- **Beat caído a mitad de guion** que presentaba a una persona: no se compensa; meter a alguien
  que la voz no ha presentado deja un rótulo huérfano.
- **Herramienta cambiada** respecto al guion: la pantalla muestra lo dicho.
