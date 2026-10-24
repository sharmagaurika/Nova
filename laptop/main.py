"""Hey Guide – runs camera, memory, Nano serial, Gemini and the companion app."""
import threading
import time
import cv2

import config
from assistant import Assistant
from detector import Detector, draw
from memory import Memory
from voice import beep, record_wav, say
from web_server import create_app

memory = Memory(config.MEMORY_DIR)
assistant = Assistant(config.GEMINI_API_KEY, config.GEMINI_MODEL, config.OBJECTS)
nano = None

state = {
    "detections": [],
    "log": [],
    "live_jpg": None,
    "distance_cm": lambda: nano.distance_cm if nano else -1,
}
busy = threading.Lock()


def handle_question(wav=None, text=None, speak=True):
    intent, said = assistant.classify(wav_bytes=wav, text=text)
    answer = assistant.answer(intent, memory, state["live_jpg"])
    state["log"].append({"time": time.time(), "question": said, "answer": answer})
    if speak:
        say(answer)
    return answer


def on_wake():
    if not busy.acquire(blocking=False):
        return  # already answering
    try:
        beep()
        wav = record_wav(config.RECORD_SECONDS)
        beep(660)
        handle_question(wav=wav)
    except Exception as e:
        print("Error:", e)
        say("Sorry, something went wrong.")
    finally:
        busy.release()


def camera_loop():
    detectors = [Detector(config.MODEL_PATH, config.CONFIDENCE, config.TRACKED, config.MIN_CONF)]
    if config.USE_CUSTOM:
        detectors.append(Detector(config.CUSTOM_MODEL_PATH, config.CUSTOM_CONFIDENCE, config.CUSTOM_TRACKED))
    cap = cv2.VideoCapture(config.CAMERA_SOURCE)
    while True:
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.5)
            continue
        found = [f for d in detectors for f in d.detect(frame)]
        annotated = draw(frame, found)
        state["detections"] = [{"label": l, "conf": round(c, 2)} for l, c, _ in found]
        for label, _, _ in found:
            memory.remember(label, frame)
        state["live_jpg"] = cv2.imencode(".jpg", annotated)[1].tobytes()
        cv2.imshow("Hey Guide", annotated)
        key = cv2.waitKey(1) & 0xFF
        if key == ord(" "):  # spacebar = backup trigger
            threading.Thread(target=on_wake, daemon=True).start()
        elif key == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        from nano_serial import NanoSerial
        nano = NanoSerial(config.SERIAL_PORT, config.SERIAL_BAUD,
                          lambda: threading.Thread(target=on_wake, daemon=True).start())
        print("Nano connected on", config.SERIAL_PORT)
    except Exception as e:
        print("Nano not connected (press SPACE to ask instead):", e)

    app = create_app(state, memory, handle_question)
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000), daemon=True).start()
    print("Companion app: http://localhost:5000")
    camera_loop()
