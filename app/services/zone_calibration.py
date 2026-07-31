from pathlib import Path

import cv2
import numpy as np

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.zone import Zone
from app.services.zone_service import ZONE_SPACE_HEIGHT, ZONE_SPACE_WIDTH

# A camera nudged out of place is common (bumped mount, vibration); a camera
# actually re-aimed or torn down is a different situation entirely. These two
# thresholds (in source-frame pixels) draw that line: small apparent motion
# gets auto-corrected, large apparent motion only gets flagged — applying a
# big homography automatically risks either a feature-matching artifact or
# genuine tampering silently "fixing" the zone to point at the wrong place.
AUTO_CORRECT_LIMIT_PX = 150.0
FLAG_LIMIT_PX = 400.0
MIN_MATCH_COUNT = 7
MIN_INLIER_RATIO = 0.2
MAX_SCALE_CHANGE_RATIO = 0.5
MAX_PERSPECTIVE_TERM = 0.004
ORB_FEATURE_COUNT = 2000
GOOD_MATCH_LIMIT = 250
RATIO_TEST_THRESHOLD = 0.75
DRIFT_IGNORE_LIMIT_PX = 5.0

_orb = cv2.ORB_create(ORB_FEATURE_COUNT)
_matcher = cv2.BFMatcher(cv2.NORM_HAMMING)


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

    capture = cv2.VideoCapture(str(segments[-1]))
    try:
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames > 1:
            capture.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 1)
        ok, frame = capture.read()
        return frame if ok else None
    finally:
        capture.release()


def _estimate_homography(reference_bgr, current_bgr):
    reference_gray = cv2.cvtColor(reference_bgr, cv2.COLOR_BGR2GRAY)
    current_gray = cv2.cvtColor(current_bgr, cv2.COLOR_BGR2GRAY)

    keypoints1, descriptors1 = _orb.detectAndCompute(reference_gray, None)
    keypoints2, descriptors2 = _orb.detectAndCompute(current_gray, None)
    if (
        descriptors1 is None
        or descriptors2 is None
        or len(keypoints1) < MIN_MATCH_COUNT
        or len(keypoints2) < MIN_MATCH_COUNT
    ):
        return None, f"not enough keypoints reference={len(keypoints1)} current={len(keypoints2)}"

    raw_matches = _matcher.knnMatch(descriptors1, descriptors2, k=2)
    matches = sorted(
        [
            match
            for match_pair in raw_matches
            if len(match_pair) == 2
            for match, next_match in [match_pair]
            if match.distance < RATIO_TEST_THRESHOLD * next_match.distance
        ],
        key=lambda match: match.distance,
    )[:GOOD_MATCH_LIMIT]
    if len(matches) < MIN_MATCH_COUNT:
        return None, f"not enough matches matches={len(matches)}"

    src_points = np.float32([keypoints1[match.queryIdx].pt for match in matches]).reshape(-1, 1, 2)
    dst_points = np.float32([keypoints2[match.trainIdx].pt for match in matches]).reshape(-1, 1, 2)

    homography, inlier_mask = cv2.findHomography(src_points, dst_points, cv2.RANSAC, 5.0)
    inliers = int(inlier_mask.sum()) if inlier_mask is not None else 0
    inlier_ratio = inliers / max(len(matches), 1)
    if homography is None or inlier_mask is None or inliers < MIN_MATCH_COUNT:
        inliers = int(inlier_mask.sum()) if inlier_mask is not None else 0
        return None, f"homography failed matches={len(matches)} inliers={inliers}"
    if inlier_ratio < MIN_INLIER_RATIO:
        return None, f"homography rejected matches={len(matches)} inliers={inliers} ratio={inlier_ratio:.2f}"
    sanity_error = _homography_sanity_error(homography)
    if sanity_error:
        return None, sanity_error
    return homography, None


def _homography_sanity_error(homography) -> str | None:
    scale_x = float(np.linalg.norm(homography[0, :2]))
    scale_y = float(np.linalg.norm(homography[1, :2]))
    if not (1 - MAX_SCALE_CHANGE_RATIO <= scale_x <= 1 + MAX_SCALE_CHANGE_RATIO):
        return f"homography rejected scale_x={scale_x:.2f}"
    if not (1 - MAX_SCALE_CHANGE_RATIO <= scale_y <= 1 + MAX_SCALE_CHANGE_RATIO):
        return f"homography rejected scale_y={scale_y:.2f}"
    perspective = max(abs(float(homography[2, 0])), abs(float(homography[2, 1])))
    if perspective > MAX_PERSPECTIVE_TERM:
        return f"homography rejected perspective={perspective:.5f}"
    return None


def _drift_magnitude_px(homography, frame_width: int, frame_height: int) -> float:
    center = np.array([[[frame_width / 2, frame_height / 2]]], dtype=np.float32)
    mapped = cv2.perspectiveTransform(center, homography)
    dx = float(mapped[0][0][0]) - frame_width / 2
    dy = float(mapped[0][0][1]) - frame_height / 2
    return (dx**2 + dy**2) ** 0.5


def _apply_correction(camera_id: int, homography, frame_width: int, frame_height: int) -> None:
    db = SessionLocal()
    try:
        zones = db.query(Zone).filter(Zone.camera_id == camera_id, Zone.is_active.is_(True)).all()
        for zone in zones:
            corrected_points = []
            for point in zone.points:
                px = point["x"] / ZONE_SPACE_WIDTH * frame_width
                py = point["y"] / ZONE_SPACE_HEIGHT * frame_height
                mapped = cv2.perspectiveTransform(np.array([[[px, py]]], dtype=np.float32), homography)
                corrected_points.append({
                    "x": round(float(mapped[0][0][0]) / frame_width * ZONE_SPACE_WIDTH, 1),
                    "y": round(float(mapped[0][0][1]) / frame_height * ZONE_SPACE_HEIGHT, 1),
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

    homography, reason = _estimate_homography(reference_bgr, current_bgr)
    if homography is None:
        print(f"[BARO][ZONE_CALIBRATION] camera_id={camera_id}: skipped drift check ({reason})")
        return False

    frame_height, frame_width = current_bgr.shape[:2]
    drift = _drift_magnitude_px(homography, frame_width, frame_height)

    if drift < DRIFT_IGNORE_LIMIT_PX:
        print(f"[BARO][ZONE_CALIBRATION] camera_id={camera_id}: drift={drift:.1f}px below threshold")
        return False

    if drift > FLAG_LIMIT_PX:
        print(f"[BARO][ZONE_CALIBRATION] camera_id={camera_id}: drift={drift:.1f}px flagged")
        return True

    print(f"[BARO][ZONE_CALIBRATION] camera_id={camera_id}: drift={drift:.1f}px correcting zones")
    _apply_correction(camera_id, homography, frame_width, frame_height)
    if drift <= AUTO_CORRECT_LIMIT_PX:
        save_reference_frame(camera_id, current_bgr)  # adopt the corrected framing as the new baseline
    return False
