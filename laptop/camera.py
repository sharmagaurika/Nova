"""Reads the camera on its own thread and keeps only the newest frame, so there's no backlog lag."""
import threading
import time
import cv2


class Camera:
    def __init__(self, source):
        self.source = source
        self.frame = None
        self._seq = 0
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            cap = cv2.VideoCapture(self.source)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            fails = 0
            while fails < 20:  # ~2 s of failed reads: the stream dropped, reconnect
                ok, frame = cap.read()
                if ok:
                    self.frame, fails = frame, 0
                    self._seq += 1
                else:
                    fails += 1
                    time.sleep(0.1)
            cap.release()
            print("Camera stream lost - reconnecting...")
            time.sleep(1)

    def read(self, last_seq=-1):
        """Wait for a frame newer than last_seq. Returns (seq, frame)."""
        while self._seq == last_seq or self.frame is None:
            time.sleep(0.005)
        return self._seq, self.frame
