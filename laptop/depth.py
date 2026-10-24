"""Finds anything close in the walking path (walls, doors, pillars...) with a metric depth model.

Runs on its own thread a couple of times a second. If the model can't load, it just stays off.
"""
import threading
import time
import cv2
import numpy as np


class DepthWatcher:
    def __init__(self, state, model_id, size=252, scale=1.0, width=384):
        """size: model input (252 ~0.7 s/check on a laptop CPU; 518 is sharper but ~6 s).
        scale: multiply distances by this to calibrate (walk toward a wall at a known distance)."""
        self.state = state
        self.model_id = model_id
        self.size = size
        self.scale = scale
        self.width = width
        self.nearest = None  # (metres, direction) of the closest thing in the path, or None
        self.ok = False
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        try:
            from PIL import Image
            from transformers import pipeline
            pipe = pipeline("depth-estimation", model=self.model_id, device="cpu")
            pipe.image_processor.size = {"height": self.size, "width": self.size}
            self.ok = True
            print("Depth model ready - walls and other obstacles will be detected")
        except Exception as e:
            print("Depth model unavailable, obstacle warnings use object detection only:", str(e)[:120])
            return
        while True:
            frame = self.state.get("frame")
            if frame is None:
                time.sleep(0.2)
                continue
            try:
                h = int(frame.shape[0] * self.width / frame.shape[1])
                rgb = cv2.cvtColor(cv2.resize(frame, (self.width, h)), cv2.COLOR_BGR2RGB)
                depth = pipe(Image.fromarray(rgb))["predicted_depth"].squeeze().numpy() * self.scale
                self.nearest = self._nearest(depth)
            except Exception as e:
                print("Depth failed:", str(e)[:120])
                time.sleep(1)

    @staticmethod
    def _nearest(depth):
        """Closest point in the path. Uses the upper-middle of the frame, so the floor doesn't count."""
        H, W = depth.shape
        band = depth[int(H * 0.15):int(H * 0.65)]
        zones = [("on your left", 0.0, 0.3), ("straight ahead", 0.3, 0.7), ("on your right", 0.7, 1.0)]
        best = None
        for name, a, b in zones:
            metres = float(np.percentile(band[:, int(W * a):int(W * b)], 10))  # near edge, ignoring specks
            if name != "straight ahead":
                metres += 0.4  # things to the side matter a bit less
            if best is None or metres < best[0]:
                best = (metres, name)
        metres, name = best
        if name != "straight ahead":
            metres -= 0.4
        return round(metres, 1), name
