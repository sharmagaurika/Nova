"""Reads messages from the Nano: 'DIST:120' and 'WAKE'."""
import threading
import serial


class NanoSerial:
    def __init__(self, port, baud, on_wake):
        self.distance_cm = -1
        self.on_wake = on_wake
        self.ser = serial.Serial(port, baud, timeout=1)
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            line = self.ser.readline().decode(errors="ignore").strip()
            if line.startswith("DIST:"):
                try:
                    self.distance_cm = int(line[5:])
                except ValueError:
                    pass
            elif line == "WAKE":
                self.on_wake()
