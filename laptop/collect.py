"""Take labelled photos of our own items for training.

Press 1 / 2 / 3 to pick keys / wallet / phone, SPACE to freeze a frame,
drag a box around the item, then ENTER to save (C to cancel). Q quits.
"""
import os
import time
import cv2

import config

NAMES = ["keys", "wallet", "phone"]
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "own")
os.makedirs(os.path.join(OUT, "images"), exist_ok=True)
os.makedirs(os.path.join(OUT, "labels"), exist_ok=True)


def count(cls):
    n = 0
    for f in os.listdir(os.path.join(OUT, "labels")):
        with open(os.path.join(OUT, "labels", f)) as fh:
            n += any(line.split()[0] == str(cls) for line in fh if line.strip())
    return n


cap = cv2.VideoCapture(config.CAMERA_SOURCE)
cls = 0
while True:
    ok, frame = cap.read()
    if not ok:
        continue
    view = frame.copy()
    counts = "  ".join(f"{i + 1}:{n}={count(i)}" for i, n in enumerate(NAMES))
    cv2.putText(view, f"Item: {NAMES[cls]}   (SPACE = take photo, Q = quit)", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    cv2.putText(view, counts, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    cv2.imshow("Collect", view)
    key = cv2.waitKey(1) & 0xFF
    if key in (ord("1"), ord("2"), ord("3")):
        cls = key - ord("1")
    elif key == ord("q"):
        break
    elif key == ord(" "):
        x, y, w, h = cv2.selectROI("Collect", frame, showCrosshair=False)
        if w and h:
            H, W = frame.shape[:2]
            name = f"{NAMES[cls]}_{int(time.time() * 1000)}"
            cv2.imwrite(os.path.join(OUT, "images", name + ".jpg"), frame)
            with open(os.path.join(OUT, "labels", name + ".txt"), "w") as f:
                f.write(f"{cls} {(x + w / 2) / W:.6f} {(y + h / 2) / H:.6f} {w / W:.6f} {h / H:.6f}\n")
            print("Saved", name)
cap.release()
cv2.destroyAllWindows()
