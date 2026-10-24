# Hey Guide 👁️‍🗨️

A wearable assistant for blind and low-vision people that **warns about obstacles** and **remembers where you left your things**.

> "Hey Guide, where are my keys?" → "On the desk, next to the laptop. Seen 3 minutes ago."

## What it does
1. **Obstacle alerts** – an ultrasonic sensor on the wrist beeps faster as you get closer to something.
2. **Object memory** – a chest camera runs our trained model to spot keys, wallet and glasses, and remembers where it last saw each one.
3. **Ask anything** – say "Hey Guide" (wake word model running *on the Arduino*), ask your question, and Gemini answers in your earphones.
4. **Companion app** – a web page showing the live view, object memory and conversation log, for the user or a caregiver.

## The AI
| Model | Where it runs | What it does |
|---|---|---|
| Wake word ("Hey Guide") | Arduino Nano 33 BLE Sense Lite | Trained by us in Edge Impulse, fully on-device |
| Object detector (keys / wallet / glasses) | Laptop | YOLOv8 trained by us on our own photos |
| Gemini Flash | Cloud | Understands the question and describes where the object is |

## Hardware
- Arduino Nano 33 BLE Sense Lite (TinyML kit)
- HC-SR04P ultrasonic sensor
- Passive buzzer
- Phone as chest camera (DroidCam / IP Webcam)
- Laptop + earphones with mic

## Repo layout
```
firmware/
  obstacle_beeper/     Step 1 – ultrasonic + buzzer
  hey_guide_wrist/     Step 2 – beeper + wake word model (final firmware)
laptop/
  main.py              runs everything
  config.py            settings (camera URL, serial port, API key)
  nano_serial.py       reads DIST / WAKE messages from the Nano
  detector.py          YOLO object detection on the camera feed
  memory.py            remembers where each object was last seen
  assistant.py         Gemini: understand question + describe location
  voice.py             mic recording + text-to-speech
  web_server.py        API for the companion app
web/
  index.html           companion app
models/                put trained best.pt here
data/photos/           training photos (not committed)
memory/                saved last-seen frames (not committed)
docs/                  wiring + demo script
```

## Setup
```bash
cd laptop
pip install -r requirements.txt
cp .env.example .env      # add your GEMINI_API_KEY
python main.py
```
Then open http://localhost:5000 for the companion app.

## Team
- Person A – firmware + wake word
- Person B – object model + memory
- Person C – Gemini + companion app
