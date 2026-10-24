"""Offline speech-to-text (English) with Whisper, so voice questions don't need Gemini."""
import io
import threading
import wave
import numpy as np
from faster_whisper import WhisperModel

RATE = 16000


class Transcriber:
    def __init__(self, model_size, objects=()):
        self.model = None
        # Example questions nudge Whisper towards the words we expect
        self.prompt = (f"Where are my keys? Where is my {', my '.join(objects)}? "
                       "What's in front of me? Find my friend in the blue shirt. Stop.")
        self._ready = threading.Event()
        # Loading takes a few seconds, so do it in the background at startup
        threading.Thread(target=self._load, args=(model_size,), daemon=True).start()

    def _load(self, model_size):
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self._ready.set()

    def transcribe(self, wav_bytes):
        """WAV bytes -> text ('' if nothing was understood)."""
        self._ready.wait()
        with wave.open(io.BytesIO(wav_bytes)) as w:
            rate, channels = w.getframerate(), w.getnchannels()
            audio = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        if channels > 1:
            audio = audio.reshape(-1, channels).mean(axis=1)
        if rate != RATE:
            audio = np.interp(np.arange(0, len(audio), rate / RATE), np.arange(len(audio)), audio).astype(np.float32)
        segments, _ = self.model.transcribe(audio, language="en", beam_size=1, vad_filter=True,
                                            initial_prompt=self.prompt)
        return " ".join(s.text for s in segments).strip()
