// Step 1: Obstacle beeper
// Arduino Nano 33 BLE Sense Lite + HC-SR04P ultrasonic + passive buzzer
//
// Wiring:
//   HC-SR04P VCC  -> 3.3V
//   HC-SR04P GND  -> GND
//   HC-SR04P Trig -> D2
//   HC-SR04P Echo -> D3
//   Buzzer +      -> D5   (longer leg, or the side marked +)
//   Buzzer -      -> GND
//
// Open Tools > Serial Monitor at 115200 baud to see "DIST:xx" readings (in cm).

const int TRIG_PIN = 2;
const int ECHO_PIN = 3;
const int BUZZER_PIN = 5;

const int CLOSE_CM = 40;   // closer than this: constant tone
const int FAR_CM = 200;    // farther than this: silent

unsigned long lastBeep = 0;

// Take one distance reading in cm. Returns -1 if nothing was detected.
long readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000);  // give up after 30 ms (~5 m)
  if (duration == 0) return -1;
  return duration / 58;  // convert echo time to centimetres
}

// Average 5 readings to smooth out jitter.
long averageDistanceCm() {
  long total = 0;
  int count = 0;
  for (int i = 0; i < 5; i++) {
    long d = readDistanceCm();
    if (d > 0) {
      total += d;
      count++;
    }
    delay(10);
  }
  if (count == 0) return -1;
  return total / count;
}

void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
}

void loop() {
  long d = averageDistanceCm();

  // Send distance to the laptop (used later by the Python script)
  Serial.print("DIST:");
  Serial.println(d);

  unsigned long now = millis();

  if (d > 0 && d < CLOSE_CM) {
    // Very close: constant high tone
    tone(BUZZER_PIN, 2000);
  } else if (d > 0 && d < FAR_CM) {
    // In range: beep faster and higher as you get closer
    unsigned long interval = map(d, CLOSE_CM, FAR_CM, 100, 800);  // ms between beeps
    int pitch = map(d, CLOSE_CM, FAR_CM, 1800, 800);              // Hz
    if (now - lastBeep >= interval) {
      tone(BUZZER_PIN, pitch, 50);  // short 50 ms beep
      lastBeep = now;
    }
  } else {
    // Nothing nearby: silent
    noTone(BUZZER_PIN);
  }

  delay(20);
}
