# Nova ESP32 Wi-Fi hardware starter (no Cursor required)

This is a small **standalone** ESP32 + Mac hardware test, not a full clone of Nova. Existing frontend, ML, and spacebar controls remain untouched. The Mac-to-ESP32 ping passed earlier, but HTTP has not been tested yet.

## 1 — Add to your hardware branch
Copy `hardware/esp32` and `laptop/hardware_server.py` into the matching locations in your `Nova` checkout. Don't overwrite your partner's existing files.

## 2 — Configure secrets
From `hardware/esp32`, copy `include/secrets.example.h` to `include/secrets.h`, then edit the **Wi-Fi SSID**, **Wi-Fi password**, **MacBook LAN IP**, and **random private token**. `secrets.h` is gitignored. The ESP32 IP observed earlier was `10.38.208.33`, which is **not** necessarily the MacBook IP. Find Mac IP: `ipconfig getifaddr en0` (if Wi-Fi is en0). Keep your working buzzer polarity: code currently uses `BUZZER_ON HIGH`, `BUZZER_OFF LOW`; reverse only if your verified wiring used active-low. Button is GPIO18 to GND; signal output is GPIO19. Buzzer has its own verified 5 V power and must have a safely interfaced 3.3 V control input. Common GND required.

## 3 — Upload
`cd hardware/esp32` then `pio run -t upload` and `pio device monitor`. A USB cable is needed to flash and power, but not for runtime data. USB power bank is fine later.

## 4 — Start Mac server
`python3 -m pip install flask`
Generate a token: `python3 -c 'import secrets; print(secrets.token_hex(16))'`
Set `export NOVA_HW_TOKEN='SAME_TOKEN_AS_IN_SECRETS_H'`
Run `python3 laptop/hardware_server.py` from repo root. Allow incoming connection in macOS firewall if asked.

## 5 — Test over Wi-Fi (second terminal)
Set the token in the new terminal too, then:

`curl -H "X-Nova-Token: $NOVA_HW_TOKEN" http://127.0.0.1:5055/health`

`curl -X POST -H "X-Nova-Token: $NOVA_HW_TOKEN" -H 'Content-Type: application/json' -d '{"command":"FOUND"}' http://127.0.0.1:5055/alert`

Expected: ESP32 fetches FOUND and plays 3 beeps. Try `OBSTACLE` for two longer beeps. Press the button and check `curl -H "X-Nova-Token: $NOVA_HW_TOKEN" http://127.0.0.1:5055/events`: short press sends LISTEN, 1.5s hold sends CANCEL.

## 6 — Integrate with Nova later
From existing detection callback, POST to local `http://127.0.0.1:5055/alert` with JSON `{"command":"FOUND"}` and `X-Nova-Token` header. For push-to-talk, Nova should consume `/events` and map `LISTEN` to its existing recording callback, retaining spacebar. Your Android partner needs to handle browser mic gesture restrictions. Detection must be debounced and rate-limited by Nova so it does not beep every frame. `OBSTACLE` is a visual warning only and never reliable measured distance.

## Security
Plain HTTP exposes the shared token on the local network; use only temporarily on a trusted network or replace with TLS/authenticated MQTT before deploying. Do not expose port 5055 publicly. University network policies may prohibit device servers. Do not commit `secrets.h`.
