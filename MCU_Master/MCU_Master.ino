#include <Arduino_FreeRTOS.h>

volatile int cntPulse = 0;
float rpm;
float moment;

void readEncoder() {
  cntPulse++;
}

void serialEvent() {
  if (Serial.read() == 'm') {
    Serial.print(rpm, 2);
    Serial.print(",");
    Serial.println(moment, 2);
  }
}

void TaskReadMoment(void *pvParameters) {
  String data = "";
  double momentNum = 0;
  double momentBuffer[20];
  uint8_t bufferIndex = 0;

  for (;;) {
    if (Serial1.available()) {
      // Read data
      data = Serial1.readStringUntil('\n');

      // Ex: "M123V" take 123.0
      if (data.startsWith("M")) {
        String momentStr = "";
        for (int i = 1; i < data.length(); i++) {
          char c = data.charAt(i);
          if (c == 'V') break;
          momentStr += c;
        }
        if (momentStr.length() > 0) {
          momentNum = momentStr.toDouble();
          momentNum = ((momentNum + 167557) * 7.5) / 1103369;
        }
      }

      // Average Filter
      if (bufferIndex == 20)
        bufferIndex = 0;
      momentBuffer[bufferIndex] = momentNum;
      bufferIndex++;

      double sum = 0;
      for (int i = 0; i < 20; i++) {
        sum += momentBuffer[i];
      }
      moment = sum / 20;
    }
    vTaskDelay(pdMS_TO_TICKS(100));
  }
}

void TaskCalRpm(void *pvParameters) {
  for (;;) {
    TickType_t xLastWakeTime = xTaskGetTickCount();
    noInterrupts();
    // rpm = (cntPulse / (pulse per round) / period ) * (ms per s) * (s per minute)
    // rpm = (cntPulse / 2396 / 100) * 1000 * 60;
    rpm = ((float)cntPulse / 599) * 150;
    cntPulse = 0;
    interrupts();
    vTaskDelayUntil(&xLastWakeTime, pdMS_TO_TICKS(100));
  }
}

void setup() {
  Serial.begin(9600);
  Serial1.begin(38400);

  attachInterrupt(0, readEncoder, FALLING);

  xTaskCreate(
    TaskCalRpm,
    "Cal Rpm Task",
    1024,
    NULL,
    2,
    NULL);

  xTaskCreate(
    TaskReadMoment,
    "Read Moment Task",
    1024,
    NULL,
    2,
    NULL);
}

void loop() {
}
