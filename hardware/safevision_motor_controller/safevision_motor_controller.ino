// SafeVision conveyor motor controller
//
// Drives a stepper motor through a STEP/DIR driver module (A4988, DRV8825,
// TMC2208/2209 in legacy mode, etc.) and listens on USB serial for
// line-terminated ('\n') text commands sent by the SafeVision backend:
//
//   STOP    -> disable the driver immediately (cuts coil current, hard stop)
//   SLOW    -> keep running, but at a reduced step rate
//   RESUME  -> re-enable the driver and return to normal step rate
//
// Each command gets an "OK\n" (or "ERR unknown command\n") reply on serial
// so the backend can confirm the Arduino actually received it.
//
// Wiring (adjust pins below to match your driver board):
//   STEP_PIN  -> driver STEP
//   DIR_PIN   -> driver DIR
//   ENABLE_PIN -> driver ENABLE (most STEP/DIR drivers are ENABLE-active-LOW:
//                 LOW = driver on, HIGH = driver off / no holding torque)

const int STEP_PIN = 3;
const int DIR_PIN = 4;
const int ENABLE_PIN = 5;

const bool ENABLE_ACTIVE_LOW = true;   // true for most A4988/DRV8825 boards
const bool RUN_DIRECTION = HIGH;       // conveyor only runs one way

const unsigned long NORMAL_STEP_INTERVAL_US = 800;   // ~1250 steps/sec
const unsigned long SLOW_STEP_INTERVAL_US = 2400;    // 1/3 speed
const unsigned long STEP_PULSE_WIDTH_US = 5;

enum MotorState { STATE_RUNNING, STATE_SLOW, STATE_STOPPED };
MotorState motorState = STATE_RUNNING;

unsigned long stepIntervalUs = NORMAL_STEP_INTERVAL_US;
unsigned long lastStepAt = 0;

String inputBuffer = "";

void setDriverEnabled(bool enabled) {
  bool pinState = ENABLE_ACTIVE_LOW ? !enabled : enabled;
  digitalWrite(ENABLE_PIN, pinState ? HIGH : LOW);
}

void applyState(MotorState state) {
  motorState = state;
  switch (state) {
    case STATE_RUNNING:
      stepIntervalUs = NORMAL_STEP_INTERVAL_US;
      setDriverEnabled(true);
      break;
    case STATE_SLOW:
      stepIntervalUs = SLOW_STEP_INTERVAL_US;
      setDriverEnabled(true);
      break;
    case STATE_STOPPED:
      setDriverEnabled(false);
      break;
  }
}

void handleCommand(const String& command) {
  if (command == "STOP") {
    applyState(STATE_STOPPED);
    Serial.println("OK");
  } else if (command == "SLOW") {
    applyState(STATE_SLOW);
    Serial.println("OK");
  } else if (command == "RESUME") {
    applyState(STATE_RUNNING);
    Serial.println("OK");
  } else if (command.length() > 0) {
    Serial.print("ERR unknown command: ");
    Serial.println(command);
  }
}

void readSerialCommands() {
  while (Serial.available() > 0) {
    char incoming = (char)Serial.read();
    if (incoming == '\n') {
      inputBuffer.trim();
      handleCommand(inputBuffer);
      inputBuffer = "";
    } else if (incoming != '\r') {
      inputBuffer += incoming;
    }
  }
}

void stepMotorIfDue() {
  if (motorState == STATE_STOPPED) return;

  unsigned long now = micros();
  if (now - lastStepAt < stepIntervalUs) return;
  lastStepAt = now;

  digitalWrite(STEP_PIN, HIGH);
  delayMicroseconds(STEP_PULSE_WIDTH_US);
  digitalWrite(STEP_PIN, LOW);
}

void setup() {
  Serial.begin(9600);

  pinMode(STEP_PIN, OUTPUT);
  pinMode(DIR_PIN, OUTPUT);
  pinMode(ENABLE_PIN, OUTPUT);

  digitalWrite(DIR_PIN, RUN_DIRECTION);
  applyState(STATE_RUNNING);
}

void loop() {
  readSerialCommands();
  stepMotorIfDue();
}
