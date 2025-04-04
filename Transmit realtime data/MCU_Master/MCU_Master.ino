#include <Arduino_FreeRTOS.h>

volatile int cntPulse = 0;
float rpm;
float moment;

double reading = 0;
double sum = 0, avg = 0;
String dataS = "", m = "";
long ini[20];
double M = 0;

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
  for (;;) {
    if (Serial1.available()) {  // Nano - moment sensor
      dataS = "";

      while (Serial1.available()) dataS = dataS + (char)Serial1.read();
      if (dataS[0] == 'M') {
        m = "";
        for (int i = 1; i < dataS.length(); i++) {
          if (dataS[i] == 'V') {
            break;
          } else m = m + dataS[i];
        }
        reading = m.toDouble();
      }
    }

    /* Get moment sensor value */
    if (reading != 0) {
      M = ((reading - (-167557)) * 7.5) / 1103369;
    }

    /* Average Filter */
    for (int i = 0; i < 19; i++) {
      ini[i] = ini[i + 1];
    }
    ini[19] = M;
    sum = 0;
    for (int j = 0; j < 20; j++) {
      sum += ini[j];
    }
    avg = sum / 20;
    moment = avg;
    vTaskDelay(pdMS_TO_TICKS(100));
  }
}

void TaskCalRpm(void *pvParameters) {
  for (;;) {
    TickType_t xLastWakeTime = xTaskGetTickCount();

    // rpm = (cntPulse / (pulse per round) / period ) * (ms per s) * (s per minute)

    rpm = ((float)(cntPulse) / 2396 / 100) * 1000 * 60;

    cntPulse = 0;

    vTaskDelayUntil(&xLastWakeTime, pdMS_TO_TICKS(100));
  }
}

void setup() {
  Serial.begin(9600);
  Serial1.begin(38400);

  pinMode(2, INPUT_PULLUP);
  attachInterrupt(0, readEncoder, FALLING);

  xTaskCreate(
    TaskCalRpm,
    "Cal Rpm Task",
    2048,
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
