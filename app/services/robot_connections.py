import asyncio
import json

from fastapi import WebSocket

# Robots may be on a different network than the backend (same problem as
# camera pull vs push — see SafeVision-CameraNode's push migration), so the
# backend can't reliably dial a robot's own address for commands. Instead
# each robot holds an outbound WebSocket connection open to the backend,
# and commands are pushed down that connection instead of POSTed to the
# robot. This registry tracks the one active connection per robot_id.
_connections: dict[int, tuple[WebSocket, asyncio.AbstractEventLoop]] = {}


def register(robot_id: int, websocket: WebSocket) -> None:
    _connections[robot_id] = (websocket, asyncio.get_running_loop())


def unregister(robot_id: int, websocket: WebSocket) -> None:
    # Only clear the slot if it's still this exact connection — a newer
    # reconnect may have already replaced it.
    connection = _connections.get(robot_id)
    if connection is not None and connection[0] is websocket:
        del _connections[robot_id]


def is_connected(robot_id: int) -> bool:
    return robot_id in _connections


async def send_command(robot_id: int, command: dict) -> bool:
    """Pushes a JSON command to the robot's open WebSocket connection.
    Mirrors motor_controller.py's philosophy: a robot being unreachable
    must never raise — it's reported back as `sent: false` so the caller
    can show that in the UI."""
    connection = _connections.get(robot_id)
    if connection is None:
        print(f"[BARO][ROBOT] robot_id={robot_id} has no active connection")
        return False

    websocket, loop = connection

    try:
        running_loop = asyncio.get_running_loop()
        if running_loop is loop:
            return await _send_on_connection(robot_id, websocket, command)

        future = asyncio.run_coroutine_threadsafe(_send_on_connection(robot_id, websocket, command), loop)
        return await asyncio.wrap_future(future)
    except Exception as exc:
        print(f"[BARO][ROBOT] Failed to send to robot_id={robot_id}: {exc}")
        unregister(robot_id, websocket)
        return False


def send_command_threadsafe(robot_id: int, command: dict, timeout: float = 2.0) -> bool:
    connection = _connections.get(robot_id)
    if connection is None:
        print(f"[BARO][ROBOT] robot_id={robot_id} has no active connection")
        return False

    websocket, loop = connection
    try:
        future = asyncio.run_coroutine_threadsafe(_send_on_connection(robot_id, websocket, command), loop)
        return future.result(timeout=timeout)
    except Exception as exc:
        print(f"[BARO][ROBOT] Failed to send to robot_id={robot_id}: {exc}")
        unregister(robot_id, websocket)
        return False


async def _send_on_connection(robot_id: int, websocket: WebSocket, command: dict) -> bool:
    await websocket.send_text(json.dumps(command))
    print(f"[BARO][ROBOT] robot_id={robot_id} <- {command}")
    return True
