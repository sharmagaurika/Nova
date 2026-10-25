"""Wi-Fi link to the ESP32 wristband (hardware/esp32): button presses in, buzzer patterns out.

Same API as laptop/hardware_server.py, but built into Nova so a button press triggers
listening directly. Every request must carry the shared X-Nova-Token.
"""
import threading
import time
from collections import deque
from flask import Flask, Response, jsonify, request

COMMANDS = ("FOUND", "OBSTACLE", "READY", "STOP")


class Hardware:
    def __init__(self, token, port, on_listen, on_cancel):
        self.token = token
        self.alerts = deque(maxlen=16)
        self.events = deque(maxlen=32)
        self.last_seen = 0  # when the ESP32 last polled us
        self._lock = threading.Lock()
        app = Flask("nova_hardware")

        @app.before_request
        def auth():
            if request.headers.get("X-Nova-Token") != self.token:
                return jsonify(error="Unauthorized"), 401
            self.last_seen = time.time()

        @app.get("/health")
        def health():
            return jsonify(ok=True, service="nova-hardware")

        @app.post("/button")
        def button():
            event = (request.get_json(silent=True) or {}).get("event")
            if event not in ("LISTEN", "CANCEL"):
                return jsonify(error="Invalid event"), 400
            with self._lock:
                self.events.append({"event": event, "timestamp": time.time()})
            print("Wristband button:", event)
            (on_listen if event == "LISTEN" else on_cancel)()
            return jsonify(ok=True)

        @app.get("/events")
        def events():
            with self._lock:
                result = list(self.events)
                self.events.clear()
            return jsonify(events=result)

        @app.post("/alert")
        def alert():
            cmd = (request.get_json(silent=True) or {}).get("command")
            if cmd not in COMMANDS:
                return jsonify(error="Invalid command"), 400
            self.alert(cmd)
            return jsonify(ok=True)

        @app.get("/next")
        def next_alert():
            with self._lock:
                cmd = self.alerts.popleft() if self.alerts else "NONE"
            return Response(cmd, mimetype="text/plain")

        threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port, threaded=True),
                         daemon=True).start()
        print(f"Wristband link on port {port} (waiting for the ESP32)")

    def alert(self, cmd):
        """Queue a buzzer pattern for the ESP32 to pick up on its next poll."""
        with self._lock:
            self.alerts.append(cmd)

    def connected(self):
        return time.time() - self.last_seen < 3
