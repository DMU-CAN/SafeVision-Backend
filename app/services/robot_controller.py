import json
import urllib.error
import urllib.request

from app.core.config import get_settings


def send_robot_command(control_address: str, command: dict) -> bool:
    """POSTs a JSON command to a device's onboard HTTP receiver
    (`control_address` is host:port). Used for NETWORK-protocol equipment
    (see equipment_controller.py) reachable directly on the local network.
    Robots use robot_connections.send_command instead — see that module's
    docstring for why (they may be behind NAT the backend can't reach
    inbound). Mirrors motor_controller.py's philosophy: unreachable must
    never raise — it's logged and reported back as `sent: false`."""
    settings = get_settings()
    url = f"http://{control_address}/command"
    body = json.dumps(command).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=settings.robot_command_timeout_seconds) as response:
            sent = 200 <= response.status < 300
            print(f"[BARO][ROBOT] {control_address} <- {command} (status={response.status})")
            return sent
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        print(f"[BARO][ROBOT] Failed to reach {control_address}: {exc}")
        return False
