# -*- coding: utf-8 -*-
"""verifica-bordes.py: dónde arranca y dónde muere el audio DE VERDAD.

El primer y el último subtítulo NO se dan por buenos: whisper mete el ruido de sala
en el arranque. Y no basta con "el primer pico que supera un umbral": una silla, una
respiración o un chasquido de labios pasan de -22 dB durante 1-2 ventanas y engañan
(ejemplo típico: pico de -21,9 dB en 0,14 con la voz empezando en 0,28).

Por eso se exige ENERGÍA SOSTENIDA: la mediana de la ventana siguiente tiene que
mantenerse alta. Un chasquido no la sostiene; una sílaba sí.

Imprime la línea FIRST_START= / LAST_END= lista para blocks.py, y la envolvente
alrededor de cada borde para que la mires tú.
"""
import wave, struct, math

WIN      = 0.02     # ventana RMS
UMBRAL   = -24.0    # dB: por encima de esto puede ser voz
SOSTEN   = 0.12     # s que debe sostenerse para no ser un chasquido
COLA     = -32.0    # dB: hasta dónde se alarga la última sílaba

w = wave.open('audio16k.wav'); n = w.getnframes(); sr = w.getframerate()
d = struct.unpack('<%dh' % n, w.readframes(n))
dur = n / sr
NW = int(SOSTEN / WIN)

def db(t):
    a = int(t*sr); b = min(a + int(WIN*sr), n)
    s = d[a:b]
    if not s or a >= n: return -99.0
    return 20*math.log10(math.sqrt(sum(x*x for x in s)/len(s))/32768.0 + 1e-9)

E = [db(k*WIN) for k in range(int(dur/WIN))]

def sostenido(k, paso):
    """¿la energía se mantiene alta en las NW ventanas siguientes (mediana)?"""
    v = sorted(E[k:k+NW] if paso > 0 else E[max(0,k-NW+1):k+1])
    return v[len(v)//2] > UMBRAL if v else False

# --- arranque: primera ventana con energía SOSTENIDA, luego bajar al pie de la subida
first = next((k for k in range(len(E)-NW) if E[k] > UMBRAL and sostenido(k, +1)), 0)
while first > 0 and E[first-1] > E[first] - 12 and E[first-1] > -32:
    first -= 1

# --- final: última ventana sostenida, + la cola de la sílaba
last = next((k for k in range(len(E)-1, NW, -1) if E[k] > UMBRAL and sostenido(k, -1)), len(E)-1)
while last + 1 < len(E) and E[last+1] > COLA:
    last += 1

fs, le = first*WIN, min((last+1)*WIN, dur)
env = lambda k: " ".join(f"{E[k+j]:.0f}" for j in range(-2, 3) if 0 <= k+j < len(E))

print(f"fichero        {dur:.3f} s")
print(f"ARRANQUE       {fs:.3f}    envolvente [-2..+2 ventanas]: {env(first)} dB")
print(f"FINAL          {le:.3f}    envolvente [-2..+2 ventanas]: {env(last)} dB")
print()
print("Míralo antes de fiarte: si en los 300 ms previos al arranque hay un pico suelto")
print("(silla, respiración, chasquido), NO es voz: el sostén ya lo descarta, pero")
print("un audio con música de fondo o ruido continuo puede necesitar subir UMBRAL.")
print()
print(f"  FIRST_START={fs:.2f} LAST_END={le:.2f} python3 blocks.py")
