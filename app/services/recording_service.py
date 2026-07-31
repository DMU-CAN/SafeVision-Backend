import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings


@dataclass
class RecorderState:
    camera_id: int
    rtsp_url: str
    process: subprocess.Popen
    started_at: float
    last_exit_code: int | None = None

    @property
    def is_alive(self) -> bool:
        return self.process.poll() is None


# Keyed by camera_id. Each recorder is a plain ffmpeg subprocess writing a
# rolling ring of segment files for that camera — independent of whether
# anyone is watching the WebRTC/MJPEG stream, so "last N minutes" is always
# available regardless of viewer activity.
_recorders: dict[int, RecorderState] = {}


def _buffer_dir(camera_id: int) -> Path:
    return Path(get_settings().recordings_dir) / "buffer" / str(camera_id)


def _clips_dir() -> Path:
    return Path(get_settings().recordings_dir) / "clips"


def _timeshift_dir() -> Path:
    return Path(get_settings().recordings_dir) / "timeshift"


def start_recording(camera_id: int, rtsp_url: str) -> None:
    recorder = _recorders.get(camera_id)
    if recorder is not None:
        if recorder.is_alive:
            return
        recorder.last_exit_code = recorder.process.poll()

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
    _recorders[camera_id] = RecorderState(
        camera_id=camera_id,
        rtsp_url=rtsp_url,
        process=process,
        started_at=time.time(),
        last_exit_code=recorder.last_exit_code if recorder is not None else None,
    )


def stop_recording(camera_id: int) -> None:
    recorder = _recorders.pop(camera_id, None)
    if recorder and recorder.is_alive:
        recorder.process.terminate()
        try:
            recorder.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            recorder.process.kill()
            recorder.process.wait(timeout=5)
    if recorder:
        recorder.last_exit_code = recorder.process.poll()


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


def build_timeshift_clip(camera_id: int, minutes_ago: float) -> str | None:
    """Concatenates whatever buffer segments fall within the requested
    look-back window into a scratch file, regenerated fresh on every call
    (not a permanent recording like extract_event_clip) — this is what lets
    the "how far back can I scrub" playback bar work regardless of when a
    viewer connects, up to however much the rolling buffer currently holds
    (recording_buffer_segment_count * recording_segment_seconds)."""
    buffer_dir = _buffer_dir(camera_id)
    if not buffer_dir.exists():
        return None

    all_segments = sorted(buffer_dir.glob("seg_*.mp4"), key=lambda path: path.stat().st_mtime)
    if not all_segments:
        return None

    settings = get_settings()
    cutoff = time.time() - minutes_ago * 60
    segment_grace_seconds = settings.recording_segment_seconds + 2
    segments = [segment for segment in all_segments if segment.stat().st_mtime >= cutoff - segment_grace_seconds]
    if not segments:
        segments = all_segments[-1:]  # requested window is older than the whole buffer — best effort

    timeshift_dir = _timeshift_dir()
    timeshift_dir.mkdir(parents=True, exist_ok=True)
    output_filename = f"camera_{camera_id}.mp4"
    output_path = timeshift_dir / output_filename
    concat_list = timeshift_dir / f"camera_{camera_id}.txt"

    output_path.unlink(missing_ok=True)
    concat_list.write_text("".join(f"file '{segment.resolve()}'\n" for segment in segments))
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-loglevel", "warning", "-y",
                "-f", "concat", "-safe", "0", "-i", str(concat_list),
                "-c", "copy", "-movflags", "+faststart", str(output_path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        concat_list.unlink(missing_ok=True)

    if result.returncode != 0 or not output_path.exists() or output_path.stat().st_size == 0:
        print(
            f"[BARO][RECORDING][TIMESHIFT_ERROR] camera_id={camera_id} "
            f"minutes_ago={minutes_ago} returncode={result.returncode} stderr={result.stderr.strip()}"
        )
        output_path.unlink(missing_ok=True)
        return None

    return f"timeshift/{output_filename}"
