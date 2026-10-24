"""Works out what the user asked and answers it. Offline first; Gemini makes answers richer when available."""
import re
import threading
import time
import cv2
from google import genai
from google.genai import types

import scene
from memory import minutes_ago

SCENE_WORDS = ("in front", "around me", "what do you see", "what can you see", "what's ahead", "what is ahead",
               "describe", "where am i")
PERSON_WORDS = ("friend", "person", "someone", "somebody", "him", "her", "them", "wearing", "shirt", "top",
                "jacket", "hoodie", "guy", "girl")
STOP_WORDS = ("stop", "cancel", "never mind", "nevermind")


class Assistant:
    def __init__(self, api_key, model, objects, fast_model=None, transcriber=None):
        self.client = genai.Client(api_key=api_key) if api_key else None
        self.model = model
        self.fast_model = fast_model or model  # for understanding questions, where speed matters most
        self.objects = objects
        self.transcriber = transcriber  # offline speech-to-text; without it, audio goes to Gemini

    def _ask(self, parts, model=None):
        if not self.client:
            raise RuntimeError("no Gemini key")
        return self.client.models.generate_content(model=model or self.model, contents=parts).text.strip()

    def parse(self, text):
        """Offline intent from a typed or transcribed question: object name, 'scene', 'find:<colour>', 'stop' or None."""
        t = text.lower()
        if any(w in t for w in STOP_WORDS):
            return "stop"
        words = re.findall(r"[a-z]+", t)
        colours = [scene.COLOUR_WORDS[w] for w in words if w in scene.COLOUR_WORDS]
        if colours and any(w in words for w in PERSON_WORDS):
            return f"find:{colours[0]}"
        for obj in self.objects:
            # "key" anywhere counts, since speech-to-text often blurs "my keys" into words like "Mikey's"
            if re.search(rf"\b{obj}s?\b", t) or (obj == "keys" and "key" in t and "keyboard" not in t):
                return obj
        if any(w in t for w in SCENE_WORDS):
            return "scene"
        return None

    def classify(self, wav_bytes=None, text=None):
        """Returns (intent, transcript). Intent is an object name, 'scene', 'find:<colour>', 'stop' or 'unknown'."""
        if wav_bytes and self.transcriber:
            text = self.transcriber.transcribe(wav_bytes)
            if not text:
                return "unknown", ""
            wav_bytes = None  # Gemini only needs the text from here on
        if text and not wav_bytes:
            intent = self.parse(text)
            if intent:
                return intent, text
        prompt = (
            "The user is blind and asked their assistant a question. "
            f"If they are asking where something is, reply with exactly one of: {', '.join(self.objects)}. "
            "If they want to find a person wearing a colour, reply 'find:<colour>' with one colour word. "
            "If they are asking what is around them, reply 'scene'. If they want to stop, reply 'stop'. "
            "Otherwise reply 'unknown'. Format: <answer>|<what the user said, in English, with no timestamps>"
        )
        parts = [prompt]
        if wav_bytes:
            parts.append(types.Part.from_bytes(data=wav_bytes, mime_type="audio/wav"))
        if text:
            parts.append(f"User question: {text}")
        try:
            reply = self._ask(parts, self.fast_model)
        except Exception as e:
            print("Gemini unavailable:", str(e)[:120])
            return "unknown", text or ""
        intent, _, said = reply.partition("|")
        intent, said = intent.strip().lower(), said.strip() or text or ""
        if intent.startswith("find:"):
            intent = "find:" + scene.COLOUR_WORDS.get(intent[5:].strip(), intent[5:].strip())
        if intent not in self.objects and intent not in ("scene", "stop") and not intent.startswith("find:"):
            intent = self.parse(said) or "unknown"  # second opinion from the offline parser
        return intent, said

    def describe_location(self, label, image_bytes):
        """One-sentence location, or None if the item isn't actually in the photo (a false detection)."""
        prompt = (f"Where is the {label} in this photo? Answer in one short sentence for someone "
                  "who can't see, using nearby objects as landmarks (e.g. 'on the desk, left of the laptop'). "
                  f"If there is no {label} in the photo, reply exactly NOT_VISIBLE.")
        reply = self._ask([prompt, types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")])
        return None if "NOT_VISIBLE" in reply else reply

    def describe_scene(self, image_bytes):
        prompt = ("Describe what is in front of a blind person in one or two short sentences. "
                  "Mention obstacles and whether they are left, right or ahead.")
        return self._ask([prompt, types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")])

    def answer(self, intent, memory, state, finder):
        if intent == "stop":
            finder.stop()
            return "Okay, stopped."
        if intent.startswith("find:"):
            colour = intent[5:]
            if colour not in scene.COLOUR_WORDS.values():
                return "Which colour are they wearing?"
            finder.start(colour)
            return f"Looking for someone in {colour}. Turn slowly and I'll guide you."
        if intent == "scene":
            frame = state.get("frame")
            if frame is None:
                return "The camera isn't ready yet."
            try:
                return self.describe_scene(cv2.imencode(".jpg", frame)[1].tobytes())
            except Exception:
                return scene.describe(state.get("all_detections", []), frame.shape)
        if intent not in self.objects:
            return "Sorry, I didn't catch that. You can ask where something is, what's in front of you, or to find a friend."
        item = memory.get(intent)
        if not item:
            return f"I haven't seen your {intent} yet."
        # Answer straight away from the stored description (described in the background); only
        # ask Gemini now if we know nothing about this sighting
        where = memory.best_description(intent)
        if where == "":
            try:
                with open(memory.image_path(intent), "rb") as f:
                    where = self.describe_location(intent, f.read())
                memory.set_description(intent, where, item["time"])
            except Exception:
                where = "I saw it"
        if where is None:
            return f"I'm not sure where your {intent} is. I thought I saw it, but couldn't confirm. Try showing it to the camera."
        where = where.strip().rstrip(".")
        return f"{where[0].upper() + where[1:]}. Seen {minutes_ago(item['time'])}."

    def describe_in_background(self, memory, every_s=2, min_gap_s=60):
        """Keep Gemini descriptions of each item's latest sighting fresh, one item at a time."""
        def loop():
            while True:
                time.sleep(every_s)
                for label, item in list(memory.items.items()):
                    if item["time"] - item.get("described_at", 0) < min_gap_s:
                        continue
                    seen_at = item["time"]
                    try:
                        with open(memory.image_path(label), "rb") as f:
                            memory.set_description(label, self.describe_location(label, f.read()), seen_at)
                    except Exception as e:
                        print("Background description failed:", str(e)[:100])
                        time.sleep(30)  # likely quota or network; back off
                    break  # one per round keeps Gemini usage low
        if self.client:
            threading.Thread(target=loop, daemon=True).start()
