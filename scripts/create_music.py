"""Create an original, deterministic instrumental score; no sampled recordings."""
from pathlib import Path
import wave
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RATE = 44100
DURATION = 144.12
audio = np.zeros((int(RATE * DURATION), 2), dtype=np.float64)

def note(start, duration, midi, gain, pan=0, pluck=False):
    first = int(start * RATE)
    n = min(int(duration * RATE), len(audio) - first)
    if n <= 0:
        return
    t = np.arange(n) / RATE
    freq = 440 * 2 ** ((midi - 69) / 12)
    tone = np.sin(2*np.pi*freq*t) + .22*np.sin(2*np.pi*2*freq*t) + .06*np.sin(2*np.pi*3*freq*t)
    envelope = np.minimum(t / (.025 if pluck else 1.2), 1) * np.minimum((n/RATE-t)/1.2, 1)
    if pluck:
        envelope *= np.exp(-t/1.5)
    wavelet = gain * tone * envelope
    audio[first:first+n, 0] += wavelet * np.sqrt((1-pan)/2)
    audio[first:first+n, 1] += wavelet * np.sqrt((1+pan)/2)

# D minor add9 -> Bb major7 -> F add9 -> C sus2. Sparse 80 BPM arpeggios.
chords = [(50,57,60,64),(46,53,57,62),(41,53,57,67),(48,55,62,64)]
for bar in range(24):
    start = bar * 6
    chord = chords[bar % 4]
    for i, pitch in enumerate(chord):
        note(start, 6.8, pitch, .075, (i-1.5)/3)
    for i in range(8):
        note(start+i*.75, 2.6, chord[i%4]+12, .045, (-1 if i%2 else 1)*.4, True)
fade = np.minimum(np.arange(len(audio))/RATE/3, 1) * np.minimum((len(audio)-np.arange(len(audio)))/RATE/5, 1)
audio *= fade[:, None]
audio *= .45 / max(np.max(np.abs(audio)), .001)
destination = ROOT / 'media' / 'original-score.wav'
with wave.open(str(destination), 'wb') as wav:
    wav.setnchannels(2)
    wav.setsampwidth(2)
    wav.setframerate(RATE)
    wav.writeframes((audio*32767).astype('<i2').tobytes())
print(destination)
