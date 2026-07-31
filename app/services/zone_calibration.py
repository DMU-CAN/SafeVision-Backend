from pathlib import Path

import cv2
import numpy as np

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.zone import Zone
from app.services.zone_service import ZONE_SPACE_HEIGHT, ZONE_SPACE_WIDTH

# A camera nudged out of place is common (bumped mount, vibration). For the
# demo path we track stable corner points from the saved reference frame with
# Lucas-Kanade optical flow, then apply a partial affine transform to zones.
# This avoids the wild perspective warping that whole-frame ORB homography can
# produce in low-texture scenes.
AUTO_CORRECT_LIMIT_PX = 320.0
LOW_CONFIDENCE_AUTO_CORRECT_LIMIT_PX = 360.0
FLAG_LIMIT_PX = 1200.0
MAX_TRACK_POINTS = 100
MIN_TRACKED_POINTS = 8
MAX_FLOW_ERROR = 38.0
MIN_AFFINE_INLIER_RATIO = 0.45
MAX_SCALE_CHANGE_RATIO = 2.0
DRIFT_IGNORE_LIMIT_PX = 5.0
LK_WINDOW_SIZE = (41, 41)
LK_PYRAMID_LEVELS = 3
RANSAC_REPROJ_THRESHOLD = 8.0
MIN_PHASE_CORRELATION_RESPONSE = 0.10
LOW_PHASE_CORRELATION_RESPONSE = 0.02
LOW_PHASE_CONFIRM_DISTANCE_PX = 25.0

_pending_low_confidence_translations: dict[int, tuple[float, float]] = {}


def _reference_path(camera_id: int) -> Path:
    return Path(get_settings().recordings_dir) / "zone_calibration" / f"camera_{camera_id}.jpg"


def has_reference_frame(camera_id: int) -> bool:
    return _reference_path(camera_id).exists()


def save_reference_frame(camera_id: int, frame_bgr) -> None:
    path = _reference_path(camera_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), frame_bgr)


def capture_frame_from_buffer(camera_id: int):
    """Grabs the most recent frame from this camera's rolling recording
    buffer (see recording_service.py) — reused here instead of opening a
    fresh RTSP connection just to snapshot one frame."""
    buffer_dir = Path(get_settings().recordings_dir) / "buffer" / str(camera_id)
    if not buffer_dir.exists():
        return None
    segments = sorted(buffer_dir.glob("seg_*.mp4"), key=lambda path: path.stat().st_mtime)
    if not segments:
        return None

    # The newest segment can still be open for writing, which often makes
    # OpenCV/ffmpeg report "moov atom not found". Walk backward through a few
    # recent files and use the newest one that is actually readable.
    for segment in reversed(segments[-5:]):
        capture = cv2.VideoCapture(str(segment))
        try:
            if not capture.isOpened():
                continue
            total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames > 1:
                capture.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 1)
            ok, frame = capture.read()
            if ok and frame is not None:
                return frame
        finally:
            capture.release()
    return None


def _estimate_affine_from_tracked_points(reference_bgr, current_bgr):
    reference_gray = cv2.cvtColor(reference_bgr, cv2.COLOR_BGR2GRAY)
    current_gray = cv2.cvtColor(current_bgr, cv2.COLOR_BGR2GRAY)

    reference_points = cv2.goodFeaturesToTrack(
        reference_gray,
        maxCorners=MAX_TRACK_POINTS,
        qualityLevel=0.01,
        minDistance=18,
        blockSize=7,
    )
    if reference_points is None or len(reference_points) < MIN_TRACKED_POINTS:
        count = 0 if reference_points is None else len(reference_points)
        return None, f"not enough reference track points points={count}"

    current_points, status, errors = cv2.calcOpticalFlowPyrLK(
        reference_gray,
        current_gray,
        reference_points,
        None,
        winSize=LK_WINDOW_SIZE,
        maxLevel=LK_PYRAMID_LEVELS,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
    )
    if current_points is None or status is None or errors is None:
        return None, "optical flow failed"

    valid_mask = (status.reshape(-1) == 1) & (errors.reshape(-1) <= MAX_FLOW_ERROR)
    src_points = reference_points.reshape(-1, 2)[valid_mask]
    dst_points = current_points.reshape(-1, 2)[valid_mask]
    if len(src_points) < MIN_TRACKED_POINTS:
        return None, f"not enough tracked points points={len(src_points)}"

    affine, inlier_mask = cv2.estimateAffinePartial2D(
        src_points,
        dst_points,
        method=cv2.RANSAC,
        ransacReprojThreshold=RANSAC_REPROJ_THRESHOLD,
        maxIters=2000,
        confidence=0.98,
    )
    inliers = int(inlier_mask.sum()) if inlier_mask is not None else 0
    inlier_ratio = inliers / max(len(src_points), 1)
    if affine is None or inlier_mask is None or inliers < MIN_TRACKED_POINTS:
        return None, f"affine failed tracked={len(src_points)} inliers={inliers}"
    if inlier_ratio < MIN_AFFINE_INLIER_RATIO:
        return None, f"affine rejected tracked={len(src_points)} inliers={inliers} ratio={inlier_ratio:.2f}"

    sanity_error = _affine_sanity_error(affine)
    if sanity_error:
        return None, sanity_error
    return affine, None


def _estimate_translation_from_phase_correlation(camera_id: int, reference_bgr, current_bgr):
    reference_gray = cv2.cvtColor(reference_bgr, cv2.COLOR_BGR2GRAY)
    current_gray = cv2.cvtColor(current_bgr, cv2.COLOR_BGR2GRAY)
    if reference_gray.shape != current_gray.shape:
        current_gray = cv2.resize(current_gray, (reference_gray.shape[1], reference_gray.shape[0]))

    reference_float = np.float32(reference_gray)
    current_float = np.float32(current_gray)
    window = cv2.createHanningWindow((reference_gray.shape[1], reference_gray.shape[0]), cv2.CV_32F)
    (dx, dy), response = cv2.phaseCorrelate(reference_float, current_float, window)
    if response < LOW_PHASE_CORRELATION_RESPONSE:
        _pending_low_confidence_translations.pop(camera_id, None)
        return None, f"phase correlation rejected response={response:.2f} dx={dx:.1f} dy={dy:.1f}"
    if response < MIN_PHASE_CORRELATION_RESPONSE:
        previous = _pending_low_confidence_translations.get(camera_id)
        _pending_low_confidence_translations[camera_id] = (dx, dy)
        if previous is None:
            return None, f"phase correlation waiting response={response:.2f} dx={dx:.1f} dy={dy:.1f}"
        distance = ((dx - previous[0]) ** 2 + (dy - previous[1]) ** 2) ** 0.5
        if distance > LOW_PHASE_CONFIRM_DISTANCE_PX:
            return None, (
                f"phase correlation unstable response={response:.2f} dx={dx:.1f} dy={dy:.1f} "
                f"previous_dx={previous[0]:.1f} previous_dy={previous[1]:.1f}"
            )
    else:
        _pending_low_confidence_translations.pop(camera_id, None)

    affine = np.array([[1.0, 0.0, dx], [0.0, 1.0, dy]], dtype=np.float32)
    return affine, None


def _affine_sanity_error(affine) -> str | None:
    scale_x = float(np.linalg.norm(affine[0, :2]))
    scale_y = float(np.linalg.norm(affine[1, :2]))
    if not (1 - MAX_SCALE_CHANGE_RATIO <= scale_x <= 1 + MAX_SCALE_CHANGE_RATIO):
        return f"affine rejected scale_x={scale_x:.2f}"
    if not (1 - MAX_SCALE_CHANGE_RATIO <= scale_y <= 1 + MAX_SCALE_CHANGE_RATIO):
        return f"affine rejected scale_y={scale_y:.2f}"
    return None


def _drift_magnitude_px(affine, frame_width: int, frame_height: int) -> float:
    center = np.array([frame_width / 2, frame_height / 2, 1.0], dtype=np.float32)
    mapped = affine @ center
    dx = float(mapped[0]) - frame_width / 2
    dy = float(mapped[1]) - frame_height / 2
    return (dx**2 + dy**2) ** 0.5


def _apply_correction(camera_id: int, affine, frame_width: int, frame_height: int) -> None:
    db = SessionLocal()
    try:
        zones = db.query(Zone).filter(Zone.camera_id == camera_id, Zone.is_active.is_(True)).all()
        for zone in zones:
            corrected_points = []
            for point in zone.points:
                px = point["x"] / ZONE_SPACE_WIDTH * frame_width
                py = point["y"] / ZONE_SPACE_HEIGHT * frame_height
                mapped = affine @ np.array([px, py, 1.0], dtype=np.float32)
                corrected_points.append({
                    "x": round(float(mapped[0]) / frame_width * ZONE_SPACE_WIDTH, 1),
                    "y": round(float(mapped[1]) / frame_height * ZONE_SPACE_HEIGHT, 1),
                })
            zone.points = corrected_points
        db.commit()
        if zones:
            print(f"[BARO][ZONE_CALIBRATION] camera_id={camera_id}: corrected {len(zones)} zone(s) for camera drift")
    except Exception as exc:
        db.rollback()
        print(f"[BARO][ZONE_CALIBRATION][DB_ERROR] {exc}")
    finally:
        db.close()


def check_and_correct_drift(camera_id: int, current_bgr) -> bool:
    """Returns True if drift was large enough to be flagged (caller should
    record a safety event) rather than auto-corrected."""
    reference_path = _reference_path(camera_id)
    if not reference_path.exists():
        print(f"[BARO][ZONE_CALIBRATION] camera_id={camera_id}: reference frame missing")
        return False

    reference_bgr = cv2.imread(str(reference_path))
    if reference_bgr is None:
        print(f"[BARO][ZONE_CALIBRATION] camera_id={camera_id}: reference frame unreadable")
        return False

    affine, reason = _estimate_affine_from_tracked_points(reference_bgr, current_bgr)
    if affine is None:
        affine, fallback_reason = _estimate_translation_from_phase_correlation(camera_id, reference_bgr, current_bgr)
        if affine is not None:
            print(
                f"[BARO][ZONE_CALIBRATION] camera_id={camera_id}: using translation fallback "
                f"after affine skip ({reason})"
            )
        else:
            reason = f"{reason}; {fallback_reason}"
    if affine is None:
        print(f"[BARO][ZONE_CALIBRATION] camera_id={camera_id}: skipped drift check ({reason})")
        return False

    frame_height, frame_width = current_bgr.shape[:2]
    drift = _drift_magnitude_px(affine, frame_width, frame_height)

    if drift < DRIFT_IGNORE_LIMIT_PX:
        print(f"[BARO][ZONE_CALIBRATION] camera_id={camera_id}: drift={drift:.1f}px below threshold")
        return False

    if drift > FLAG_LIMIT_PX:
        print(f"[BARO][ZONE_CALIBRATION] camera_id={camera_id}: drift={drift:.1f}px flagged")
        return True

    if drift > LOW_CONFIDENCE_AUTO_CORRECT_LIMIT_PX:
        print(f"[BARO][ZONE_CALIBRATION] camera_id={camera_id}: drift={drift:.1f}px too large for auto-correction")
        return True

    print(f"[BARO][ZONE_CALIBRATION] camera_id={camera_id}: drift={drift:.1f}px correcting zones")
    _apply_correction(camera_id, affine, frame_width, frame_height)
    save_reference_frame(camera_id, current_bgr)  # adopt the corrected framing as the new baseline
    return False
