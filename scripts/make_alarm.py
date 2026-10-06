"""Generate a tiny original alarm WAV; no downloaded audio dependency."""
import math
import struct
import wave
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "assets/sounds/alarm.wav"
path.parent.mkdir(parents=True, exist_ok=True)
with wave.open(str(path), "wb") as sound:
    sound.setnchannels(1)
    sound.setsampwidth(2)
    sound.setframerate(22050)
    samples = []
    for index in range(22050):
        t = index/22050
        frequency = 880 if t < .4 else 660
        volume = .22 if t < .8 else 0
        samples.append(struct.pack("<h", int(32767*volume*math.sin(2*math.pi*frequency*t))))
    sound.writeframes(b"".join(samples))
print(f"Created {path.name}")
