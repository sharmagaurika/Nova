"""Offline scene understanding from detections: directions, distances, shirt colours."""
import math
import cv2
import numpy as np

COLOUR_WORDS = {
    "red": "red", "maroon": "red", "orange": "orange", "yellow": "yellow",
    "green": "green", "blue": "blue", "navy": "blue", "teal": "blue", "purple": "purple",
    "violet": "purple", "pink": "pink", "white": "white", "black": "black",
    "grey": "gray", "gray": "gray", "brown": "brown",
}


def direction(box, width):
    x = (box[0] + box[2]) / 2 / width
    if x < 0.3:
        return "on your left"
    if x < 0.43:
        return "slightly to your left"
    if x <= 0.57:
        return "straight ahead"
    if x <= 0.7:
        return "slightly to your right"
    return "on your right"


def distance(box, height):
    """Rough distance for a person from how tall they look in the frame."""
    h = (box[3] - box[1]) / height
    if h > 0.85:
        return "right in front of you"
    if h > 0.55:
        return "about 1 to 2 metres away"
    if h > 0.3:
        return "a few metres away"
    return "far away"


def shirt_colour(frame, box):
    """Dominant colour of the torso (upper-middle part of a person box)."""
    x1, y1, x2, y2 = map(int, box)
    w, h = x2 - x1, y2 - y1
    crop = frame[y1 + int(h * 0.2):y1 + int(h * 0.5), x1 + int(w * 0.3):x2 - int(w * 0.3)]
    if crop.size == 0:
        return None
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV).reshape(-1, 3).astype(int)
    hue, sat, val = hsv[:, 0], hsv[:, 1], hsv[:, 2]
    names = np.full(len(hsv), "gray", dtype=object)
    names[val > 190] = "white"
    names[val < 60] = "black"
    colourful = (sat >= 70) & (val >= 60)
    for name, lo, hi in [("red", 0, 9), ("orange", 9, 20), ("yellow", 20, 34), ("green", 34, 85),
                         ("blue", 85, 128), ("purple", 128, 148), ("pink", 148, 170), ("red", 170, 181)]:
        names[colourful & (hue >= lo) & (hue < hi)] = name
    names[colourful & (hue >= 9) & (hue < 20) & (val < 150)] = "brown"
    values, counts = np.unique(names, return_counts=True)
    return values[counts.argmax()]


def describe(detections, shape):
    """Short spoken description of what the camera sees, e.g. 'Straight ahead: a person ...'."""
    height, width = shape[:2]
    if not detections:
        return "I can't see anything I recognise right now."
    groups = {}
    for label, _, box in sorted(detections, key=lambda d: -(d[2][3] - d[2][1])):
        thing = f"a {label}"
        if label == "person":
            thing += f" {distance(box, height)}"
        groups.setdefault(direction(box, width), []).append(thing)
    order = ["straight ahead", "slightly to your left", "slightly to your right", "on your left", "on your right"]
    parts = [f"{d.capitalize()}: {', '.join(groups[d][:3])}." for d in order if d in groups]
    return " ".join(parts)


# Typical real heights (m) of things you might walk into, for estimating distance from the camera
OBSTACLE_HEIGHTS = {
    "person": 1.7, "chair": 0.9, "dining table": 0.75, "couch": 0.85, "bench": 0.5, "bed": 0.6,
    "bicycle": 1.0, "motorcycle": 1.1, "car": 1.5, "potted plant": 0.6, "suitcase": 0.6, "backpack": 0.5,
    "dog": 0.6, "tv": 0.6, "refrigerator": 1.7, "fire hydrant": 0.8, "stop sign": 2.0, "toilet": 0.8,
}


def nearest_obstacle(detections, shape, hfov_deg):
    """Closest obstacle in the walking path (middle of the frame): (name, metres, direction) or None."""
    height, width = shape[:2]
    focal = (width / 2) / math.tan(math.radians(hfov_deg / 2))  # focal length in pixels
    best = None
    for label, _, (x1, y1, x2, y2) in detections:
        if label not in OBSTACLE_HEIGHTS:
            continue
        if x2 < width * 0.2 or x1 > width * 0.8:  # off to the side, not in your way
            continue
        metres = OBSTACLE_HEIGHTS[label] * focal / max(y2 - y1, 1)
        if y1 <= 2 and y2 >= height - 2:  # fills the frame top to bottom: it's very close
            metres = min(metres, 0.7)
        if best is None or metres < best[1]:
            name = "table" if label == "dining table" else label
            best = (name, round(metres, 1), direction((x1, y1, x2, y2), width))
    return best


def merge_obstacles(named, depth):
    """Combine the object-detection estimate (named) with the depth model's (metres, direction).
    Depth sees walls and anything else; a named object close to the same distance keeps its name."""
    if not depth:
        return named
    metres, where = depth
    if named and named[1] <= metres + 0.5:
        return named[0], min(named[1], metres), named[2]
    return "obstacle", metres, where


SURFACES = {"dining table": "table", "bed": "bed", "couch": "couch", "chair": "chair", "bench": "bench"}


def near(label, box, detections, min_conf=0.6):
    """Offline location for a remembered object, e.g. 'on the table, next to the laptop'.
    Only uses confident detections, since guesses about furniture are often wrong."""
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    sure = [(l, b) for l, c, b in detections if c >= min_conf and l not in (label, "person")]
    on = next((SURFACES[l] for l, b in sure if l in SURFACES and b[0] <= cx <= b[2] and b[1] <= cy <= b[3]), None)
    others = sorted((abs((b[0] + b[2]) / 2 - cx) + abs((b[1] + b[3]) / 2 - cy), l) for l, b in sure if l not in SURFACES)
    names = list(dict.fromkeys(l for _, l in others))[:1]
    parts = ([f"on the {on}"] if on else []) + ([f"next to the {names[0]}"] if names else [])
    return ", ".join(parts)
