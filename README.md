# Reels con IA

Las dos skills de Claude Code con las que edito y animo los reels de mi serie diaria:

| Skill | Qué hace |
|---|---|
| **recortar-silencios** | Le pasas tu toma hablando a cámara y te devuelve un proyecto de Final Cut Pro (`.fcpxml`) sin silencios, sin golpecitos y sin las frases que repetiste porque te equivocaste (se queda el último intento). Lo quitado va a un proyecto aparte por si quieres recuperar algo. No toca tu vídeo original. |
| **animar-reels** | Le pasas el audio de tu toma y tu guion, y te devuelve los subtítulos en 4K con fondo transparente (bloques de 2-3 palabras, sincronizados al fotograma) y los clips de animación de apoyo, hechos con [HyperFrames](https://github.com/heygen-com/hyperframes), con la tabla de en qué segundo entra cada uno. |

Como referencia: una toma real de 2:26 queda en 0:56 tras recortar silencios y en 0:47 tras quitar golpecitos y repeticiones, lo mismo que el montaje hecho a mano.

## Instalar (con Claude Code)

Dentro de Claude Code, o en la terminal:

```bash
claude plugin marketplace add javiggil/reels-con-ia
claude plugin install reels-con-ia@javiggil
```

Y ya está. Después le hablas normal: *"recorta los silencios de este vídeo"* o *"anima este reel"* con la ruta de tu archivo.

Lo que necesita cada skill (Claude Code te lo instala si se lo pides):

- **recortar-silencios:** [auto-editor](https://github.com/WyattBlue/auto-editor) y [whisper.cpp](https://github.com/ggml-org/whisper.cpp) (`brew install auto-editor whisper-cpp`), con los modelos `large-v3` y el VAD `silero`, más FFmpeg y Python. Final Cut Pro para importar.
- **animar-reels:** Node 22 o superior, FFmpeg, whisper.cpp con el modelo `large-v3`, Python con `torch` y `torchaudio`, y las skills de HyperFrames (`claude plugin marketplace add heygen-com/hyperframes`). La lista completa está en su `SKILL.md`.

## Instalar a mano

Si prefieres no usar el gestor de plugins, descarga este repositorio (botón verde **Code**, **Download ZIP**) y copia las carpetas de `plugins/reels-con-ia/skills/` a `~/.claude/skills/`.

## Sin Claude Code

Las skills necesitan Claude Code, pero el método no. Puedes leer cada `SKILL.md` como una receta y hacer cada paso a mano en tu editor: cortar los silencios con la cuchilla, sacar los subtítulos automáticos de Final Cut o CapCut y revisarlos contra tu guion, y hacer las animaciones desde el chat de Claude o ChatGPT con el conector de HyperFrames de HeyGen.

## Antes de empezar

- **recortar-silencios** corta los silencios por volumen: graba sin música ni ruido de fondo. Las repeticiones las detecta por lo que dices, así que repite la frase desde el principio cuando te equivoques.
- **animar-reels** trae un sistema visual de ejemplo (`reference/estilo-ejemplo.md`). Cámbialo por el tuyo: es lo que hace que tus vídeos se parezcan a ti.
- El render en 4K con transparencia pesa mucho: renderiza de uno en uno.

## Licencia

MIT. Úsalo, cámbialo y compártelo.

Método de Javi Gil, [@javiggil](https://www.instagram.com/javiggil/).
