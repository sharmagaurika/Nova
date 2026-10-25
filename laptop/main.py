"""Hey Guide – runs camera, memory, Nano serial, Gemini and the companion app."""
import os
import threading
import time
import cv2

import config
from assistant import Assistant
from camera import Camera
from depth import DepthWatcher
import scene
from detector import Detector, draw
from finder import Finder
from memory import Memory
from speech import Transcriber
import voice
from voice import beep, record_wav, say
from web_server import create_app

memory = Memory(config.MEMORY_DIR)
assistant = Assistant(config.GEMINI_API_KEY, config.GEMINI_MODEL, config.OBJECTS, config.GEMINI_FAST_MODEL,
                      Transcriber(config.WHISPER_MODEL, config.OBJECTS))
nano = None

state = {
    "detections": [],       # tracked objects in view, for the companion app
    "all_detections": [],   # everything the models see: (label, conf, box)
    "frame": None,          # latest raw camera frame
    "log": [],
    "live_jpg": None,
    "obstacle": None,       # nearest thing in the walking path: (name, metres, direction)
    "distance_cm": lambda: (nano.distance_cm if nano else
                            state["obstacle"][1] * 100 if state["obstacle"] else -1),
    "mic": lambda: voice.status["mic"],
    "warnings_on": lambda: alerts["on"],
}
alerts = {"beep": 0, "said": 0, "said_what": None, "quiet_until": 0, "on": True}
finder = Finder(state, config.FINDER_SECONDS, config.FINDER_EVERY_S)
assistant.describe_in_background(memory)
depth_watch = (DepthWatcher(state, config.DEPTH_MODEL, config.DEPTH_SIZE, config.DEPTH_SCALE)
               if config.USE_DEPTH else None)
busy = threading.Lock()


def handle_question(wav=None, text=None, speak=True):
    alerts["quiet_until"] = time.time() + 30  # no obstacle chatter while answering
    voice.hush()
    intent, said = assistant.classify(wav_bytes=wav, text=text)
    print(f"Heard: {said!r} -> {intent}")
    if wav:  # keep the last recording, handy for checking what the mic picked up
        with open(os.path.join(config.MEMORY_DIR, "last_question.wav"), "wb") as f:
            f.write(wav)
    answer = assistant.answer(intent, memory, state, finder)
    state["log"].append({"time": time.time(), "question": said, "answer": answer})
    if speak:
        say(answer)
    alerts["quiet_until"] = time.time() + 6
    return answer


def on_wake():
    if not busy.acquire(blocking=False):
        return  # already answering
    try:
        voice.hush()  # stop obstacle warnings first, so the mic doesn't hear Nova talking
        wav = record_wav(config.RECORD_SECONDS)  # beeps once the mic is on
        beep(660)
        if wav is None:
            say("I didn't hear anything.")
        else:
            handle_question(wav=wav)
    except Exception as e:
        print("Error:", e)
        say("Sorry, something went wrong.")
    finally:
        if voice.status["mic"] == "thinking":
            voice.status["mic"] = "idle"
        alerts["quiet_until"] = time.time() + 6  # give the answer room before warnings resume
        busy.release()


def warn_obstacle(obstacle):
    """Say what's in the way (and "Stop" when very close); beep as an early heads-up."""
    now = time.time()
    if (not obstacle or not alerts["on"] or busy.locked() or now < alerts["quiet_until"]
            or voice.status["mic"] != "idle" or finder.colour):
        return  # muted, or don't talk over questions, answers or friend-finder guidance
    name, metres, where = obstacle
    # Unnamed obstacles (depth model) are only spoken when very close; sitting at a desk they're everywhere
    say_below = config.OBSTACLE_STOP_M if name == "obstacle" else config.OBSTACLE_SAY_M
    if metres < say_below:
        stop = metres < config.OBSTACLE_STOP_M
        key = (name, stop)  # not direction: it flickers as you move
        # Speak when the obstacle or its zone changes, otherwise repeat now and then
        if voice.busy():
            return
        if key != alerts["said_what"] or now - alerts["said"] > (4 if stop else 8):
            alerts.update(said=now, said_what=key, beep=now)
            text = (f"Stop. {name.capitalize()} {where}, {metres:.1f} metres." if stop
                    else f"{name.capitalize()} {where}, {metres:.1f} metres.")
            threading.Thread(target=say, args=(text,), daemon=True).start()
        return
    if metres < config.OBSTACLE_WARN_M and now - alerts["beep"] > 2:
        alerts["beep"] = now
        threading.Thread(target=beep, args=(1200, 120), daemon=True).start()


def camera_loop():
    stock = Detector(config.MODEL_PATH, config.CONFIDENCE)  # every COCO object
    custom = (Detector(config.CUSTOM_MODEL_PATH, config.CUSTOM_CONFIDENCE, config.CUSTOM_TRACKED)
              if config.USE_CUSTOM else None)
    cam, seq = Camera(config.CAMERA_SOURCE), -1
    while True:
        seq, frame = cam.read(seq)  # always the newest frame, so the view never lags behind
        everything = [(config.TRACKED.get(l, l), c, b) for l, c, b in stock.detect(frame)
                      if c >= config.MIN_CONF.get(config.TRACKED.get(l, l), 0)]
        if custom:
            everything += custom.detect(frame)
        found = [f for f in everything if f[0] in config.OBJECTS]
        people = [f for f in everything if f[0] == "person"]
        state["frame"], state["all_detections"] = frame, everything
        annotated = draw(frame, found + people)
        state["detections"] = [{"label": l, "conf": round(c, 2)} for l, c, _ in found]
        for label, _, box in found:
            memory.remember(label, frame, scene.near(label, box, everything))
        state["obstacle"] = scene.merge_obstacles(
            scene.nearest_obstacle(everything, frame.shape, config.CAMERA_HFOV_DEG),
            depth_watch.nearest if depth_watch and depth_watch.ok else None)
        warn_obstacle(state["obstacle"])
        if state["obstacle"] and state["obstacle"][1] < config.OBSTACLE_WARN_M:
            name, metres, _ = state["obstacle"]
            cv2.putText(annotated, f"{name} {metres} m", (15, annotated.shape[0] - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 255), 3)
        mic = voice.status["mic"]
        if mic != "idle":  # big banner so it's obvious when the mic is on
            colour = {"listening": (0, 0, 255), "thinking": (0, 200, 255), "speaking": (0, 200, 0)}[mic]
            cv2.rectangle(annotated, (0, 0), (annotated.shape[1], 50), colour, -1)
            cv2.putText(annotated, mic.upper(), (15, 36), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 3)
        state["live_jpg"] = cv2.imencode(".jpg", annotated)[1].tobytes()
        cv2.imshow("Nova", annotated)
        key = cv2.waitKey(1) & 0xFF
        if key == ord(" "):  # spacebar = backup trigger
            threading.Thread(target=on_wake, daemon=True).start()
        elif key == ord("m"):  # mute / unmute obstacle warnings
            alerts["on"] = not alerts["on"]
            print("Obstacle warnings", "on" if alerts["on"] else "muted")
        elif key == ord("q"):
            break
    cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        from nano_serial import NanoSerial
        nano = NanoSerial(config.SERIAL_PORT, config.SERIAL_BAUD,
                          lambda: threading.Thread(target=on_wake, daemon=True).start())
        print("Nano connected on", config.SERIAL_PORT)
    except Exception as e:
        print("Nano not connected (press SPACE to ask instead):", e)

    app = create_app(state, memory, handle_question,
                     lambda: threading.Thread(target=on_wake, daemon=True).start(),
                     lambda: alerts.update(on=not alerts["on"]))
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000), daemon=True).start()
    print("Companion app: http://localhost:5000")
    camera_loop()
