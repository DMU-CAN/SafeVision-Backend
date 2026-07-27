# hardware/

Arduino firmware for the SafeVision motor controller.

`safevision_motor_controller/safevision_motor_controller.ino` — flash this to
the Arduino wired to the main Raspberry Pi over USB. It drives a stepper
motor through a STEP/DIR driver module (A4988/DRV8825/TMC in legacy mode)
and listens for `STOP` / `SLOW` / `RESUME` commands from the backend
(see `app/services/motor_controller.py`).

## Wiring

| Arduino pin | Driver pin |
|---|---|
| 3 | STEP |
| 4 | DIR |
| 5 | ENABLE |

Adjust the pin numbers and step timing constants at the top of the `.ino`
file to match your actual driver board and motor.

## Backend setup

1. Flash the sketch (Arduino IDE: open the `.ino`, select your board, Upload).
2. Find the serial device once plugged into the Pi: `ls /dev/ttyACM* /dev/ttyUSB*`.
3. Set `MOTOR_SERIAL_PORT` in the backend's `.env` (or `docker-compose.yml`
   environment) to that device, e.g. `/dev/ttyACM0`.
4. If running in Docker, add the device to `docker-compose.yml`:
   ```yaml
   devices:
     - /dev/hailo0:/dev/hailo0
     - /dev/ttyACM0:/dev/ttyACM0
   ```
   Only add this once the Arduino is actually connected — Docker refuses to
   start a container that references a device path that doesn't exist.

## Testing without the backend

```bash
python3 -c "
import serial, time
s = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
time.sleep(2)  # allow the Arduino to reset after the port opens
s.write(b'STOP\n')
print(s.readline())
"
```
