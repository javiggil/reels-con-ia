#!/usr/bin/env python3
"""check.py <dir-snapshots> [alfa]: hoja de contacto con la ZONA SEGURA de Reels (azul)
y la BANDA DE SUBTITULOS (rojo) dibujadas encima. En clips ALFA compone antes sobre gris
oscuro para ver si la tinta se lee.
Espacio nativo 2160x3840; se reduce a 440x782 (factor 0.2037).
  zona segura 4K: (120,240)-(1800,3200)  -> (24,49)-(367,652)
  banda subs 4K:  y 2480-2660            -> y 505-542
"""
import sys, glob, os, subprocess
d = sys.argv[1]; alfa = len(sys.argv) > 2 and sys.argv[2] == 'alfa'
outs = []
for f in sorted(glob.glob(os.path.join(d, 'frame*.png'))):
    o = f.replace('.png', '-chk.png')
    pre = ['magick', f]
    if alfa:
        pre = ['magick', '-size', '2160x3840', 'xc:#241f1b', f, '-composite']
    subprocess.run(pre + ['-resize', '440x782',
        '-fill', 'none', '-stroke', '#00a0ff', '-strokewidth', '3',
        '-draw', 'rectangle 24,49 367,652',
        '-stroke', '#ff2d2d', '-draw', 'rectangle 0,505 440,542', o], check=True)
    outs.append(o)
rows, per = [], 4
for i in range(0, len(outs), per):
    r = os.path.join(d, 'row%d.png' % i)
    subprocess.run(['magick'] + outs[i:i+per] + ['-background', '#181818', '-gravity', 'north',
                    '+smush', '14', r], check=True)
    rows.append(r)
subprocess.run(['magick'] + rows + ['-background', '#181818', '-gravity', 'west',
                '-smush', '14', os.path.join(d, 'HOJA.png')], check=True)
print(os.path.join(d, 'HOJA.png'), len(outs), 'frames')
