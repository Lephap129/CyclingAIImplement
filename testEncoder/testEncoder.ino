volatile int pulse = 0;

void readEncoder() {
  pulse++;
}

void setup() {
  Serial.begin(9600);
  pinMode(2, INPUT_PULLUP);
  attachInterrupt(0, readEncoder, FALLING); // pin 2  
}

void loop() {
  Serial.println(pulse);
  
  if (Serial.available()) {
    char cmd = Serial.read();
    if (cmd == 'r') {  
      pulse = 0;
      Serial.println("Pulse reset!");
    }
  }
  
  delay(1000); 
}
