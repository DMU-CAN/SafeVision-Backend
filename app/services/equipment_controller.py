import time

from app.core.config import get_settings
from app.services.robot_controller import send_robot_command


class SerialEquipmentController:
    """Same line-based text protocol (STOP/SLOW/RESUME) as the legacy
    single-equipment MotorController, but keyed by port so multiple serial
    devices can be controlled independently. Never raises — a disconnected
    or missing device must not crash the caller."""

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
            time.sleep(2)  # let the Arduino bootloader finish resetting after DTR toggle
        except Exception as exc:
            print(f"[BARO][EQUIPMENT] Could not open serial port {self.port}: {exc}")
            self._serial = None
        return self._serial

    def send(self, command: str) -> bool:
        connection = self._get_connection()
        if connection is None:
            return False
        try:
            connection.write(f"{command}\n".encode("ascii"))
            connection.flush()
            print(f"[BARO][EQUIPMENT] {self.port} <- {command}")
            return True
        except Exception as exc:
            print(f"[BARO][EQUIPMENT] Failed to send {command} to {self.port}: {exc}")
            self._serial = None
            return False


_serial_controllers: dict[str, SerialEquipmentController] = {}


def _get_serial_controller(port: str) -> SerialEquipmentController:
    controller = _serial_controllers.get(port)
    if controller is None:
        settings = get_settings()
        controller = SerialEquipmentController(port, settings.motor_serial_baud)
        _serial_controllers[port] = controller
    return controller


def send_equipment_command(control_protocol: str, control_address: str, command: str) -> bool:
    """command is one of STOP/SLOW/RESUME regardless of protocol — SERIAL
    sends it as-is over the line protocol, NETWORK wraps it as JSON matching
    the robot control channel's shape."""
    if control_protocol == "SERIAL":
        return _get_serial_controller(control_address).send(command)
    if control_protocol == "NETWORK":
        return send_robot_command(control_address, {"type": "equipment", "command": command})
    print(f"[BARO][EQUIPMENT] Unknown control_protocol: {control_protocol}")
    return False
