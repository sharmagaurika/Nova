"""API + static files for the companion app."""
import os
import time
from flask import Flask, jsonify, request, send_from_directory, Response

WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "web")


def create_app(state, memory, handle_question, on_listen):
    app = Flask(__name__)

    @app.route("/")
    def index():
        return send_from_directory(WEB_DIR, "index.html")

    @app.route("/api/state")
    def api_state():
        return jsonify({
            "distance_cm": state["distance_cm"](),
            "obstacle": state["obstacle"],
            "mic": state["mic"](),
            "detections": state["detections"],
            "log": state["log"][-20:],
            "memory": memory.items,
            "now": time.time(),
        })

    @app.route("/memory/<path:name>")
    def memory_image(name):
        return send_from_directory(memory.folder, name)

    @app.route("/api/ask", methods=["POST"])
    def api_ask():
        text = request.json.get("question", "")
        return jsonify({"answer": handle_question(text=text, speak=True)})

    @app.route("/api/listen", methods=["POST"])
    def api_listen():
        on_listen()  # same as pressing SPACE / the wristband button
        return "", 204

    @app.route("/live.jpg")
    def live():
        jpg = state.get("live_jpg")
        if jpg is None:
            return "", 204
        return Response(jpg, mimetype="image/jpeg")

    return app
