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

    def remember(self, label, frame):
        # Save at most once a second per object to keep it light
        last = self.items.get(label, {}).get("time", 0)
        if time.time() - last < 1:
            return
        path = os.path.join(self.folder, f"{label}.jpg")
        cv2.imwrite(path, frame)
        self.items[label] = {"time": time.time(), "image": f"{label}.jpg",
                             "description": self.items.get(label, {}).get("description", "")}
        with open(self.index_path, "w") as f:
            json.dump(self.items, f)

    def set_description(self, label, text):
        if label in self.items:
            self.items[label]["description"] = text
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
