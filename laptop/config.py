import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

_cam = os.getenv("CAMERA_SOURCE", "0")
CAMERA_SOURCE = int(_cam) if _cam.isdigit() else _cam

SERIAL_PORT = os.getenv("SERIAL_PORT", "COM3")
SERIAL_BAUD = 115200

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "best.pt")
MEMORY_DIR = os.path.join(os.path.dirname(__file__), "..", "memory")

OBJECTS = ["keys", "wallet", "glasses"]
CONFIDENCE = 0.5
RECORD_SECONDS = 4
