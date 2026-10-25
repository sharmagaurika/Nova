# Nova

**Your eyes, out loud.** Nova is a wearable assistant for blind and low-vision people. A phone on your chest is its camera; Nova watches the world, remembers where you left things, warns you before you walk into something, and helps you find your friends, all by voice.

> "Nova, where are my keys?"  →  "On the wooden table, next to the laptop. Seen 3 minutes ago."
>
> "Find my friend in the red hoodie."  →  "Slightly to your left… straight ahead… You've reached the person in red."
>
> *(walking)*  →  "Chair on your right, 1.7 metres." … "Stop. Obstacle straight ahead, 0.8 metres."

## What it does

| Feature | How it works |
|---|---|
| **Remembers your things** | Two YOLOv8 models watch the camera: a stock model (bottle, cup, backpack, laptop, umbrella) and one **we trained** on keys, wallets and phones, fine-tuned on our own photos. Nova saves where each item was last seen. |
| **Never makes up a location** | Gemini looks at each saved sighting in the background and describes it ("on the wooden table, near the white tag"). If the item isn't really in the photo, Nova says it isn't sure instead of guessing. |
| **Warns about obstacles, even walls** | A metric depth model (Depth Anything V2) estimates distance to anything in your walking path. Named things (people, chairs, tables) are announced from 2 m, and anything under 1 m triggers "Stop". |
| **Finds a friend by what they're wearing** | Nova finds people, reads their shirt colour, and guides you by voice until you reach them. |
| **Describes the scene** | "What's in front of me?" gets a short spoken description (Gemini, with an offline fallback built from what the camera detects). |
| **Understands you offline** | Speech-to-text runs on the laptop with Whisper, and an offline parser works out the question, so voice works without internet or API quota. |
| **Companion app** | A live dashboard at `http://localhost:5000` for caregivers and demos: Nova's animated orb (listening / thinking / speaking), live view, path-ahead gauge, belongings with verified/unconfirmed badges, and history. |

## How it works

```
Phone camera ──Wi-Fi──► Camera reader (always the newest frame, auto-reconnect)
                              │
          ┌───────────────────┼─────────────────────┐
          ▼                   ▼                     ▼
   YOLOv8 (stock)      YOLOv8 (ours:          Depth Anything V2
   people, furniture,  keys, wallet, phone)   (metric, indoor)
   everyday objects                           distance to anything
          └─────────┬─────────┘                     │
                    ▼                               ▼
        Memory: where each item was        Obstacle warnings: names what's
        last seen + Gemini check in        ahead, "Stop" under 1 m, quiet
        the background (flags false        while you're talking
        sightings)
                    │
Mic ──► Whisper (offline) ──► question parser ──► answer ──► text-to-speech
                                     │
                          friend finder (people + shirt colour)
                          scene description (Gemini, offline fallback)
```

- **Five models, one laptop.** Two YOLOv8 detectors, Depth Anything V2 and Whisper run locally, each on its own thread so nothing blocks the camera. Gemini is an optional cloud layer.
- **Offline first.** Finding items, obstacle warnings, the friend finder and voice questions all work with no internet. Gemini adds richer descriptions and fact-checks sightings when it's available.
- **Honest answers.** If Gemini can't see an item in the saved photo, Nova says it isn't sure rather than giving a made-up location.
- **Speech that doesn't collide.** Asking a question cancels queued warnings, waits for Nova to finish speaking before listening (so the mic doesn't record Nova), and keeps warnings quiet while it answers.

**Built with:** Python, Ultralytics YOLOv8, Hugging Face Transformers (Depth Anything V2), faster-whisper, Google Gemini, OpenCV, Flask, Roboflow + Google Colab for training.

## How to talk to Nova

Press **SPACE** in the camera window, or click the **orb** in the companion app, then speak after the beep. Recording stops when you stop talking.

- "Where are my keys?" / "Where's my wallet?" / "Where is my bottle?"
- "What's in front of me?"
- "Find my friend in the blue shirt" (any of: red, orange, yellow, green, blue, purple, pink, white, black, grey, brown)
- "Stop" to end a friend search

Other keys in the camera window: **M** mutes or unmutes spoken obstacle warnings (handy while sitting), **Q** quits.

## Setup (Windows)

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r laptop/requirements.txt
copy laptop\.env.example laptop\.env     # then edit it, see below
cd laptop
..\.venv\Scripts\python main.py
```

Then open **http://localhost:5000**. The first start downloads the YOLO, Whisper and depth models (a few hundred MB) and takes a minute; later starts take about 15 seconds.

**`laptop/.env`:**

| Setting | What it's for |
|---|---|
| `GEMINI_API_KEY` | From [Google AI Studio](https://aistudio.google.com/apikey). Optional: without it, scene descriptions and item checks fall back to offline versions. |
| `CAMERA_SOURCE` | The phone stream, e.g. `http://192.168.1.50:8080/video` from the **IP Webcam** app (1280×720, quality 50 works well), or `0` for a webcam. Phone and laptop must be on the same network. |
| `GEMINI_MODEL` | Optional. Defaults to `gemini-3.1-flash-lite`. |
| `DEPTH_SCALE` | Optional calibration. Stand 1 m from a wall; if Nova says 1.5 m, set `0.67`. |
| `USE_DEPTH` | Optional. Set to `0` to turn the depth model off on slower laptops. |

## Training our own model

1. `laptop/collect.py` takes labelled photos with the camera: press 1/2/3 for keys/wallet/phone, SPACE to freeze, drag a box, ENTER to save.
2. `models/train_nova.ipynb` trains on Roboflow keys, wallet and phone photos in Google Colab.
3. `models/finetune_nova.ipynb` tops it up with our own photos (about 5 minutes on a free GPU). The result goes in `models/best.pt`.

On our held-out photos, fine-tuning raised accuracy (mAP50) from 0.00 to 0.43 for keys, 0.19 to 0.54 for wallets and 0.00 to 0.99 for phones.

## Repo layout

```
laptop/
  main.py          runs everything: camera, detection, warnings, voice, app
  config.py        settings
  assistant.py     understands questions and answers them
  speech.py        offline speech-to-text (Whisper)
  voice.py         mic recording and text-to-speech
  scene.py         directions, distances, shirt colours, scene descriptions
  depth.py         depth model for walls and other obstacles
  finder.py        friend finder
  detector.py      YOLO detection
  memory.py        where each item was last seen
  camera.py        lag-free camera reading with auto-reconnect
  web_server.py    companion app API
  collect.py       photo labelling tool for training
web/index.html     companion app
models/            trained model and training notebooks
firmware/          optional Arduino obstacle-beeper (not needed: obstacles use the camera)
```

## Limitations

- Distances are estimates from a single camera, so they're less reliable for things partly out of view.
- Shirt colour is read from the chest, so a jacket counts as the jacket's colour; dim or coloured light can confuse it.
- English only.
