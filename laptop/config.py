import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")  # 2.5-flash isn't offered to new keys
GEMINI_FAST_MODEL = os.getenv("GEMINI_FAST_MODEL", GEMINI_MODEL)  # understanding questions

# Offline English speech-to-text for voice questions (tiny.en is faster, base.en hears better)
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base.en")

_cam = os.getenv("CAMERA_SOURCE", "0")
CAMERA_SOURCE = int(_cam) if _cam.isdigit() else _cam

SERIAL_PORT = os.getenv("SERIAL_PORT", "COM3")
SERIAL_BAUD = 115200

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "..", "memory")

# Stock YOLOv8 (trained on COCO) - fast, offline, no training needed
MODEL_PATH = os.getenv("MODEL_PATH", "yolov8s.pt")  # downloaded automatically on first run
CONFIDENCE = 0.4

# Objects we remember: {COCO class name: name we use}. The stock model also reports
# every other COCO object (people, chairs...) for scene descriptions and the friend finder.
TRACKED = {"bottle": "bottle", "cup": "cup", "backpack": "backpack", "laptop": "laptop", "umbrella": "umbrella"}
# Optional stricter cut-offs for objects that get confused, e.g. {"cup": 0.6}
MIN_CONF = {}

# Our own model (trained in models/train_nova.ipynb), run alongside the stock one
CUSTOM_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "best.pt")
CUSTOM_TRACKED = {"keys": "keys", "wallet": "wallet", "phone": "phone"}
CUSTOM_CONFIDENCE = 0.5
USE_CUSTOM = os.path.exists(CUSTOM_MODEL_PATH)
if not USE_CUSTOM:
    print("models/best.pt not found - keys/wallet/phone off until it's trained")

OBJECTS = list(TRACKED.values()) + (list(CUSTOM_TRACKED.values()) if USE_CUSTOM else [])
RECORD_SECONDS = 7  # longest a question can be; recording stops early once you go quiet

# Camera obstacle warnings: beeps start below WARN_M and speed up; spoken warning below SAY_M
CAMERA_HFOV_DEG = 65   # phone main camera's horizontal field of view
OBSTACLE_WARN_M = 2.5
OBSTACLE_SAY_M = 1.0
# Metric depth model, so walls, doors and anything else close are caught too (set USE_DEPTH=0 to turn off)
USE_DEPTH = os.getenv("USE_DEPTH", "1") == "1"
DEPTH_MODEL = "depth-anything/Depth-Anything-V2-Metric-Indoor-Small-hf"
DEPTH_SIZE = 252   # model input size: 252 checks ~1.4x a second on a laptop
DEPTH_SCALE = float(os.getenv("DEPTH_SCALE", "1.0"))  # calibrate: true distance / distance Nova shows

# Friend finder: how long to keep guiding, and how often to check
FINDER_SECONDS = 45
FINDER_EVERY_S = 1.5
