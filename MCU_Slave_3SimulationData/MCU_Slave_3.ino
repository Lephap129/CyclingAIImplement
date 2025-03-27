#include "HX711.h"
#include "slave_data.h"

const int LOADCELL_DOUT_PIN1 = 10;
const int LOADCELL_SCK_PIN1 = 11;
const int LOADCELL_DOUT_PIN2 = 12;
const int LOADCELL_SCK_PIN2 = 13;
float reading1;
float reading2;
double M1 = 0, M2 = 0;
double Zero_Momen1 = -1807135;
double Zero_Momen2 = -28519.00;
double Cur1[10];
double Cur2[10];
double sum1 = 0, sum2 = 0, avg1 = 0, avg2 = 0;

HX711 scale1, scale2;

int currentIndex = 0;

void serialEvent() {
  if (Serial.read() == 'm') {
    Serial.print(slaveData[currentIndex]);

    currentIndex++;
    if (currentIndex >= slaveDataSize) {
      currentIndex = 0; 
    }
  }
}

void setup() {
  Serial.begin(9600);

  scale1.begin(LOADCELL_DOUT_PIN1, LOADCELL_SCK_PIN1);
  scale2.begin(LOADCELL_DOUT_PIN2, LOADCELL_SCK_PIN2);
}

void loop() {
  if ((scale1.is_ready() && scale2.is_ready())) {
    reading1 = scale1.read();
    reading2 = scale2.read();

    if ((reading1 != 0 && reading2 != 0)) {
      M1 = ((reading1 - Zero_Momen1) * 20) / 9260000;
      M2 = ((reading2 - Zero_Momen2) * 20) / 926000;
    }
    sum1 = 0;
    sum2 = 0;
    for (int i = 0; i < 9; i++) {
      Cur1[i] = Cur1[i + 1];
      Cur2[i] = Cur2[i + 1];
      sum1 = sum1 + Cur1[i];
      sum2 = sum2 + Cur2[i];
    }
    Cur1[9] = M1;
    Cur2[9] = M2;
    sum1 = sum1 + Cur1[9];
    sum2 = sum2 + Cur2[9];

    // Moment sensor value apply Average Filter
    avg1 = sum1 / 10;
    avg2 = sum2 / 10;

    Serial.print("M1: ");
    Serial.println(avg1);
    Serial.print("M2: ");
    Serial.println(avg2);
  }
}
