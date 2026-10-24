"""Remembers the latest frame and time each object was seen."""
import json
import os
import time
import cv2


class Memory:
    def __init__(self, folder):
        self.folder = folder
        os.makedirs(folder, exist_ok=True)
        self.index_path = os.path.join(folder, "index.json")
        self.items = {}
        if os.path.exists(self.index_path):
            with open(self.index_path) as f:
                self.items = json.load(f)

    def remember(self, label, frame, near=""):
        """Save the latest sighting. near = quick offline location from other detections."""
        # Save at most once a second per object to keep it light
        old = self.items.get(label, {})
        if time.time() - old.get("time", 0) < 1:
            return
        path = os.path.join(self.folder, f"{label}.jpg")
        cv2.imwrite(path, frame)
        self.items[label] = {**old, "time": time.time(), "image": f"{label}.jpg", "near": near or old.get("near", "")}
        self._save()

    def set_description(self, label, text, seen_at):
        """Store a Gemini description of the sighting taken at seen_at (None = Gemini couldn't see the item)."""
        if label in self.items:
            self.items[label].update(description=text, verified=text is not None, described_at=seen_at)
            self._save()

    def best_description(self, label):
        """Gemini's description if it matches the latest sighting, else the offline one.
        Returns None if Gemini checked this sighting and the item wasn't really there."""
        item = self.items.get(label, {})
        if item.get("described_at", 0) >= item.get("time", 0) - 90:
            if not item.get("verified", True):
                return None
            if item.get("description"):
                return item["description"]
        return item.get("near", "")

    def _save(self):
        with open(self.index_path, "w") as f:
            json.dump(self.items, f)

    def get(self, label):
        return self.items.get(label)

    def image_path(self, label):
        return os.path.join(self.folder, f"{label}.jpg")


def minutes_ago(timestamp):
    mins = int((time.time() - timestamp) / 60)
    if mins < 1:
        return "just now"
    return f"{mins} minute{'s' if mins != 1 else ''} ago"
