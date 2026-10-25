"""Nova standalone hardware API; run on Mac alongside your existing Nova app.
Only for a trusted local test network. Protect with NOVA_HW_TOKEN.
"""
from collections import deque
from threading import Lock
from flask import Flask, request, jsonify, Response
import os
import time

app = Flask(__name__)
lock = Lock()
alerts = deque(maxlen=16)
events = deque(maxlen=32)
TOKEN = os.getenv("NOVA_HW_TOKEN", "")

def allowed():
    return bool(TOKEN) and request.headers.get("X-Nova-Token") == TOKEN

@app.before_request
def auth():
    if not allowed():
        return jsonify(error="Unauthorized or token not configured"), 401

@app.get("/health")
def health():
    return jsonify(ok=True, service="nova-hardware")

@app.post("/button")
def button():
    event = (request.get_json(silent=True) or {}).get("event")
    if event not in ("LISTEN", "CANCEL"):
        return jsonify(error="Invalid event"), 400
    with lock:
        events.append({"event": event, "timestamp": time.time()})
    print("BUTTON", event, flush=True)
    return jsonify(ok=True)

@app.get("/events")
def get_events():
    with lock:
        result = list(events)
        events.clear()
    return jsonify(events=result)

@app.post("/alert")
def alert():
    cmd = (request.get_json(silent=True) or {}).get("command")
    if cmd not in ("FOUND", "OBSTACLE", "READY", "STOP"):
        return jsonify(error="Invalid command"), 400
    with lock:
        alerts.append(cmd)
    print("ALERT", cmd, flush=True)
    return jsonify(ok=True)

@app.get("/next")
def next_alert():
    with lock:
        cmd = alerts.popleft() if alerts else "NONE"
    return Response(cmd, mimetype="text/plain")

if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("Set NOVA_HW_TOKEN before starting the server")
    app.run(host="0.0.0.0", port=5055, debug=False, threaded=True)
