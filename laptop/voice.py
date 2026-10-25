"""Microphone recording and text-to-speech."""
import io
import queue
import threading
import time
import wave
import numpy as np
import pyttsx3
import sounddevice as sd

RATE = 16000
BLOCK = RATE // 10  # 100 ms

# What the voice side is doing right now, shown in the camera window and companion app
status = {"mic": "idle"}  # idle | listening | thinking | speaking


def record_wav(max_seconds=7, silence_s=1.5, wait_s=4):
    """Beep, then record from the default mic until the user stops talking.
    Returns WAV bytes, or None if nobody spoke."""
    status["mic"] = "listening"
    chunks, spoke, quiet, noise = [], False, 0, None
    try:
        with sd.InputStream(samplerate=RATE, channels=1, dtype="int16", blocksize=BLOCK) as stream:
            # Mic is already on when the beep plays, so words said right after it aren't cut off
            threading.Thread(target=beep, daemon=True).start()
            for i in range(int(max_seconds * 10)):
                block, _ = stream.read(BLOCK)
                chunks.append(block.copy())
                level = np.sqrt(np.mean(block.astype(np.float32) ** 2))
                if i < 3:  # skip the beep itself
                    continue
                # Background noise = the quietest moment so far, so talking right away doesn't skew it
                noise = level if noise is None else min(noise, level)
                if level > max(noise * 3, 250):
                    spoke, quiet = True, 0
                elif spoke:
                    quiet += 1
                    if quiet >= silence_s * 10:
                        break
                elif i >= wait_s * 10:
                    break  # nobody spoke
    finally:
        status["mic"] = "thinking" if spoke else "idle"
    if not spoke:
        return None
    audio = np.concatenate(chunks)
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


# One speech thread so sentences never overlap. A fresh engine per sentence: on Windows,
# reusing a pyttsx3 engine silently skips everything after the first runAndWait().
_speech = queue.Queue()


def _speaker():
    while True:
        text, done = _speech.get()
        status["mic"] = "speaking"
        try:
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
            engine.stop()
            del engine
        except Exception as e:
            print("Speech failed:", e)
        finally:
            if _speech.empty():
                status["mic"] = "idle"
            done.set()


threading.Thread(target=_speaker, daemon=True).start()


def busy():
    """True while something is being said or waiting to be said."""
    return status["mic"] == "speaking" or not _speech.empty()


def hush(timeout=6):
    """Drop anything waiting to be said and wait for the current sentence to finish."""
    while True:
        try:
            _, done = _speech.get_nowait()
            done.set()
        except queue.Empty:
            break
    end = time.time() + timeout
    while status["mic"] == "speaking" and time.time() < end:
        time.sleep(0.05)


def say(text):
    """Speak text and wait until it has been said."""
    print("🔊", text)
    done = threading.Event()
    _speech.put((text, done))
    done.wait()
