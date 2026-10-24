"""Gemini: work out what the user asked and answer it."""
from google import genai
from google.genai import types

from memory import minutes_ago


class Assistant:
    def __init__(self, api_key, model, objects):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.objects = objects

    def _ask(self, parts):
        return self.client.models.generate_content(model=self.model, contents=parts).text.strip()

    def classify(self, wav_bytes=None, text=None):
        """Returns (object_name or 'scene', transcript)."""
        prompt = (
            "The user is blind and asked their assistant a question. "
            f"If they are asking where something is, reply with exactly one of: {', '.join(self.objects)}. "
            "If they are asking what is around them, reply 'scene'. "
            "Format: <answer>|<what the user said>"
        )
        parts = [prompt]
        if wav_bytes:
            parts.append(types.Part.from_bytes(data=wav_bytes, mime_type="audio/wav"))
        if text:
            parts.append(f"User question: {text}")
        reply = self._ask(parts)
        intent, _, said = reply.partition("|")
        return intent.strip().lower(), said.strip() or text or ""

    def describe_location(self, label, image_bytes):
        prompt = (f"Where are the {label} in this photo? Answer in one short sentence for someone "
                  "who can't see, using nearby objects as landmarks (e.g. 'on the desk, left of the laptop').")
        return self._ask([prompt, types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")])

    def describe_scene(self, image_bytes):
        prompt = ("Describe what is in front of a blind person in one or two short sentences. "
                  "Mention obstacles and whether they are left, right or ahead.")
        return self._ask([prompt, types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")])

    def answer(self, intent, memory, live_frame_jpg):
        if intent == "scene":
            if live_frame_jpg is None:
                return "The camera isn't ready yet."
            return self.describe_scene(live_frame_jpg)
        if intent not in self.objects:
            return "Sorry, I didn't catch that. Try asking where something is."
        item = memory.get(intent)
        if not item:
            return f"I haven't seen your {intent} yet."
        with open(memory.image_path(intent), "rb") as f:
            where = self.describe_location(intent, f.read())
        memory.set_description(intent, where)
        return f"{where} Seen {minutes_ago(item['time'])}."
