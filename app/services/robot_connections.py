import json

from fastapi import WebSocket

# Robots may be on a different network than the backend (same problem as
# camera pull vs push — see SafeVision-CameraNode's push migration), so the
# backend can't reliably dial a robot's own address for commands. Instead
# each robot holds an outbound WebSocket connection open to the backend,
# and commands are pushed down that connection instead of POSTed to the
# robot. This registry tracks the one active connection per robot_id.
_connections: dict[int, WebSocket] = {}


def register(robot_id: int, websocket: WebSocket) -> None:
    _connections[robot_id] = websocket


def unregister(robot_id: int, websocket: WebSocket) -> None:
    # Only clear the slot if it's still this exact connection — a newer
    # reconnect may have already replaced it.
    if _connections.get(robot_id) is websocket:
        del _connections[robot_id]


def is_connected(robot_id: int) -> bool:
    return robot_id in _connections


async def send_command(robot_id: int, command: dict) -> bool:
    """Pushes a JSON command to the robot's open WebSocket connection.
    Mirrors motor_controller.py's philosophy: a robot being unreachable
    must never raise — it's reported back as `sent: false` so the caller
    can show that in the UI."""
    websocket = _connections.get(robot_id)
    if websocket is None:
        print(f"[BARO][ROBOT] robot_id={robot_id} has no active connection")
        return False

    try:
        await websocket.send_text(json.dumps(command))
        print(f"[BARO][ROBOT] robot_id={robot_id} <- {command}")
        return True
    except Exception as exc:
        print(f"[BARO][ROBOT] Failed to send to robot_id={robot_id}: {exc}")
        unregister(robot_id, websocket)
        return False
