import subprocess
from pathlib import Path

from app.core.config import get_settings

# Keyed by camera_id. Each recorder is a plain ffmpeg subprocess writing a
# rolling ring of segment files for that camera — independent of whether
# anyone is watching the WebRTC/MJPEG stream, so "last N minutes" is always
# available regardless of viewer activity.
_recorders: dict[int, subprocess.Popen] = {}


def _buffer_dir(camera_id: int) -> Path:
    return Path(get_settings().recordings_dir) / "buffer" / str(camera_id)


def _clips_dir() -> Path:
    return Path(get_settings().recordings_dir) / "clips"


def start_recording(camera_id: int, rtsp_url: str) -> None:
    if camera_id in _recorders and _recorders[camera_id].poll() is None:
        return

    settings = get_settings()
    buffer_dir = _buffer_dir(camera_id)
    buffer_dir.mkdir(parents=True, exist_ok=True)

    command = [
        "ffmpeg", "-loglevel", "warning", "-nostdin",
        "-rtsp_transport", "udp", "-i", rtsp_url,
        "-c", "copy", "-an",
        "-f", "segment",
        "-segment_time", str(settings.recording_segment_seconds),
        "-segment_wrap", str(settings.recording_buffer_segment_count),
        "-reset_timestamps", "1",
        str(buffer_dir / "seg_%03d.mp4"),
    ]
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _recorders[camera_id] = process


def stop_recording(camera_id: int) -> None:
    process = _recorders.pop(camera_id, None)
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def stop_all_recordings() -> None:
    for camera_id in list(_recorders.keys()):
        stop_recording(camera_id)


def extract_event_clip(camera_id: int, event_id: int) -> str | None:
    """Concatenates whatever buffer segments currently exist for a camera
    into a permanent clip file. Called after a post-roll delay so the buffer
    includes footage from both before and after the event."""
    buffer_dir = _buffer_dir(camera_id)
    if not buffer_dir.exists():
        return None

    segments = sorted(buffer_dir.glob("seg_*.mp4"), key=lambda path: path.stat().st_mtime)
    if not segments:
        return None

    clips_dir = _clips_dir()
    clips_dir.mkdir(parents=True, exist_ok=True)
    clip_filename = f"event_{event_id}.mp4"
    clip_path = clips_dir / clip_filename
    concat_list = clips_dir / f"event_{event_id}.txt"

    concat_list.write_text("".join(f"file '{segment.resolve()}'\n" for segment in segments))
    try:
        subprocess.run(
            [
                "ffmpeg", "-loglevel", "warning", "-y",
                "-f", "concat", "-safe", "0", "-i", str(concat_list),
                "-c", "copy", str(clip_path),
            ],
            check=False,
        )
    finally:
        concat_list.unlink(missing_ok=True)

    return f"clips/{clip_filename}" if clip_path.exists() else None
