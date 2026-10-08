# Reels con IA

Las dos skills de Claude Code con las que edito y animo los reels de mi serie diaria:

| Skill | Qué hace |
|---|---|
| **recortar-silencios** | Le pasas tu toma hablando a cámara y te devuelve un proyecto de Final Cut Pro (`.fcpxml`) con los silencios ya quitados. No toca tu vídeo original. |
| **animar-reels** | Le pasas el audio de tu toma y tu guion, y te devuelve los subtítulos en 4K con fondo transparente (bloques de 2-3 palabras, sincronizados al fotograma) y los clips de animación de apoyo, hechos con [HyperFrames](https://github.com/heygen-com/hyperframes), con la tabla de en qué segundo entra cada uno. |

Como referencia: una toma real de 5:12 queda en 2:09 tras recortar silencios (88 trozos), y en un reel de 0:59 tras elegir las frases buenas.

## Instalar (con Claude Code)

Dentro de Claude Code, o en la terminal:

```bash
claude plugin marketplace add javiggil/reels-con-ia
claude plugin install reels-con-ia@javiggil
```

Y ya está. Después le hablas normal: *"recorta los silencios de este vídeo"* o *"anima este reel"* con la ruta de tu archivo.

Lo que necesita cada skill (Claude Code te lo instala si se lo pides):

- **recortar-silencios:** [auto-editor](https://github.com/WyattBlue/auto-editor) (`brew install auto-editor`) y FFmpeg. Final Cut Pro para importar.
- **animar-reels:** Node 22 o superior, FFmpeg, whisper.cpp con el modelo `large-v3`, Python con `torch` y `torchaudio`, y las skills de HyperFrames (`claude plugin marketplace add heygen-com/hyperframes`). La lista completa está en su `SKILL.md`.

## Instalar a mano

Si prefieres no usar el gestor de plugins, descarga este repositorio (botón verde **Code**, **Download ZIP**) y copia las carpetas de `plugins/reels-con-ia/skills/` a `~/.claude/skills/`.

## Sin Claude Code

Las skills necesitan Claude Code, pero el método no. Puedes leer cada `SKILL.md` como una receta y hacer cada paso a mano en tu editor: cortar los silencios con la cuchilla, sacar los subtítulos automáticos de Final Cut o CapCut y revisarlos contra tu guion, y hacer las animaciones desde el chat de Claude o ChatGPT con el conector de HyperFrames de HeyGen.

## Antes de empezar

- **recortar-silencios** corta por volumen, no por voz: graba sin música ni ruido de fondo.
- **animar-reels** trae un sistema visual de ejemplo (`reference/estilo-ejemplo.md`). Cámbialo por el tuyo: es lo que hace que tus vídeos se parezcan a ti.
- El render en 4K con transparencia pesa mucho: renderiza de uno en uno.

## Licencia

MIT. Úsalo, cámbialo y compártelo.

Método de Javi Gil, [@javiggil](https://www.instagram.com/javiggil/).
