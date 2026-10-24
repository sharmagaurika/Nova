"""Runs our trained YOLO model on camera frames."""
from ultralytics import YOLO


class Detector:
    def __init__(self, model_path, confidence):
        self.model = YOLO(model_path)
        self.confidence = confidence

    def detect(self, frame):
        """Returns (list of (label, confidence, box), annotated frame)."""
        result = self.model(frame, conf=self.confidence, verbose=False)[0]
        found = []
        for box in result.boxes:
            label = result.names[int(box.cls)]
            found.append((label, float(box.conf), box.xyxy[0].tolist()))
        return found, result.plot()
