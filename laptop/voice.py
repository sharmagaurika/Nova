"""Microphone recording and text-to-speech."""
import io
import threading
import wave
import numpy as np
import pyttsx3
import sounddevice as sd

RATE = 16000
_tts_lock = threading.Lock()


def record_wav(seconds):
    """Record from the default mic (earphone mic) and return WAV bytes."""
    audio = sd.rec(int(seconds * RATE), samplerate=RATE, channels=1, dtype="int16")
    sd.wait()
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(audio.tobytes())
    return buf.getvalue()


def beep(freq=880, ms=150):
    t = np.linspace(0, ms / 1000, int(RATE * ms / 1000), False)
    sd.play(0.3 * np.sin(2 * np.pi * freq * t), RATE)
    sd.wait()


def say(text):
    print("🔊", text)
    with _tts_lock:
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
