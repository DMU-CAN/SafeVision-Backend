from functools import lru_cache

from app.core.config import get_settings


class MotorController:
    """Sends line-based text commands (STOP / SLOW / RESUME) to the Arduino
    stepper motor controller over USB serial. Safe to use even when no
    Arduino is connected (e.g. on a dev machine) — errors are logged, never
    raised, since a missing motor controller must never crash detection."""

    def __init__(self, port: str, baudrate: int) -> None:
        self.port = port
        self.baudrate = baudrate
        self._serial = None

    def _get_connection(self):
        if self._serial is not None and self._serial.is_open:
            return self._serial

        import serial  # imported lazily so pyserial isn't required to just run detection

        try:
            self._serial = serial.Serial(self.port, self.baudrate, timeout=1)
        except Exception as exc:
            print(f"[BARO][MOTOR] Could not open serial port {self.port}: {exc}")
            self._serial = None
        return self._serial

    def _send(self, command: str) -> bool:
        settings = get_settings()
        if not settings.motor_control_enabled:
            return False

        connection = self._get_connection()
        if connection is None:
            return False

        try:
            connection.write(f"{command}\n".encode("ascii"))
            connection.flush()
            print(f"[BARO][MOTOR] sent {command}")
            return True
        except Exception as exc:
            print(f"[BARO][MOTOR] Failed to send {command}: {exc}")
            self._serial = None
            return False

    def stop(self) -> bool:
        return self._send("STOP")

    def slow(self) -> bool:
        return self._send("SLOW")

    def resume(self) -> bool:
        return self._send("RESUME")


@lru_cache(maxsize=1)
def get_motor_controller() -> MotorController:
    settings = get_settings()
    return MotorController(settings.motor_serial_port, settings.motor_serial_baud)
