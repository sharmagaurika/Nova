"""Runs YOLO on camera frames and keeps only the objects we track."""
import cv2
from ultralytics import YOLO


class Detector:
    def __init__(self, model_path, confidence, tracked, min_conf=None):
        """tracked: {model class name: name we use}, e.g. {"cell phone": "phone"}.
        min_conf: optional stricter cut-off per name we use, e.g. {"phone": 0.6}."""
        self.model = YOLO(model_path)
        self.confidence = confidence
        self.min_conf = min_conf or {}
        name_to_id = {n: i for i, n in self.model.names.items()}
        self.labels = {name_to_id[n]: ours for n, ours in tracked.items()}

    def detect(self, frame):
        """Returns a list of (label, confidence, box)."""
        result = self.model(frame, conf=self.confidence, classes=list(self.labels), verbose=False)[0]
        found = [(self.labels[int(b.cls)], float(b.conf), b.xyxy[0].tolist()) for b in result.boxes]
        return [f for f in found if f[1] >= self.min_conf.get(f[0], 0)]


def draw(frame, found):
    """Returns a copy of the frame with a labelled box around each detection."""
    annotated = frame.copy()
    for label, conf, (x1, y1, x2, y2) in found:
        p1, p2 = (int(x1), int(y1)), (int(x2), int(y2))
        cv2.rectangle(annotated, p1, p2, (255, 255, 0), 2)
        cv2.putText(annotated, f"{label} {conf:.2f}", (p1[0], p1[1] - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
    return annotated
