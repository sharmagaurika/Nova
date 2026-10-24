# Final wrist firmware (Step 2)

1. Train the "Hey Guide" model in Edge Impulse (classes: `hey_guide`, `noise`, `unknown`).
2. Deploy → Arduino library → in Arduino IDE: Sketch → Include Library → Add .ZIP Library.
3. Open the library's example: File → Examples → <your project> → nano_ble33_sense → **nano_ble33_sense_microphone_continuous**.
4. Save it into this folder as `hey_guide_wrist.ino`.
5. Paste in the ultrasonic + buzzer code from `../obstacle_beeper` (pins, `readDistanceCm`, beeping).
6. Where the example prints results, add:
   ```cpp
   if (result.classification[0].value > 0.8) {   // check index matches "hey_guide"
     Serial.println("WAKE");
   }
   ```
The laptop listens for `WAKE` and `DIST:<cm>` on serial.
