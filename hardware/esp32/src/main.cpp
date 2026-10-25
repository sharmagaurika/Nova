#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "secrets.h"

#define BUTTON_PIN 18
#define BUZZER_PIN 19
// Use the polarity that passed your physical buzzer test.
#define BUZZER_ON HIGH
#define BUZZER_OFF LOW

// Change these locally. Do not commit real credentials or tokens to GitHub.

bool rawButton = HIGH, stableButton = HIGH, longSent = false;
unsigned long lastBounce = 0, pressedAt = 0, lastPoll = 0, lastReconnect = 0;
String currentAlert = "NONE";
int beatsLeft = 0;
unsigned long patternChanged = 0;
int onDuration = 100, offDuration = 120;
bool sounding = false;

void stopBuzzer() {
  beatsLeft = 0;
  sounding = false;
  digitalWrite(BUZZER_PIN, BUZZER_OFF);
}
void beginAlert(int count, int onMs, int offMs) {
  stopBuzzer();
  beatsLeft = count;
  onDuration = onMs;
  offDuration = offMs;
  sounding = true;
  digitalWrite(BUZZER_PIN, BUZZER_ON);
  patternChanged = millis();
}
void serviceBuzzer() {
  if (beatsLeft <= 0) return;
  unsigned long elapsed = millis() - patternChanged;
  if (sounding && elapsed >= (unsigned long)onDuration) {
    digitalWrite(BUZZER_PIN, BUZZER_OFF);
    sounding = false;
    beatsLeft--;
    patternChanged = millis();
  } else if (!sounding && beatsLeft > 0 && elapsed >= (unsigned long)offDuration) {
    sounding = true;
    digitalWrite(BUZZER_PIN, BUZZER_ON);
    patternChanged = millis();
  }
}
void sendButton(const char* eventName) {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.setTimeout(700);
  http.begin(String(NOVA_SERVER) + "/button");
  http.addHeader("X-Nova-Token", NOVA_TOKEN);
  http.addHeader("Content-Type", "application/json");
  int code = http.POST(String("{\"event\":\"") + eventName + "\"}");
  Serial.printf("BUTTON %s HTTP %d\n", eventName, code);
  http.end();
}
void fetchAlert() {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.setTimeout(700);
  http.begin(String(NOVA_SERVER) + "/next");
  http.addHeader("X-Nova-Token", NOVA_TOKEN);
  int code = http.GET();
  if (code == 200) {
    String cmd = http.getString();
    cmd.trim();
    if (cmd == "FOUND") beginAlert(3, 100, 150);
    else if (cmd == "OBSTACLE") beginAlert(2, 300, 200);
    else if (cmd == "READY") beginAlert(1, 80, 80);
    else if (cmd == "STOP") stopBuzzer();
  } else if (code > 0) {
    Serial.printf("ALERT HTTP %d\n", code);
  }
  http.end();
}
void readButton() {
  bool reading = digitalRead(BUTTON_PIN);
  if (reading != rawButton) lastBounce = millis();
  rawButton = reading;
  if (millis() - lastBounce >= 35 && reading != stableButton) {
    stableButton = reading;
    if (stableButton == LOW) {
      pressedAt = millis();
      longSent = false;
    } else if (!longSent) {
      sendButton("LISTEN");
    }
  }
  if (stableButton == LOW && !longSent && millis() - pressedAt >= 1500) {
    longSent = true;
    sendButton("CANCEL");
  }
}
void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(BUZZER_PIN, OUTPUT);
  stopBuzzer();
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.println("NOVA WIFI STARTING");
}
void loop() {
  serviceBuzzer();
  readButton();
  if (WiFi.status() != WL_CONNECTED && millis() - lastReconnect > 5000) {
    lastReconnect = millis();
    WiFi.reconnect();
  }
  if (millis() - lastPoll >= 250) {
    lastPoll = millis();
    fetchAlert();
  }
  delay(2);
}
