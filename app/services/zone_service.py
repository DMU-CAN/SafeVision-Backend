from app.db.session import SessionLocal
from app.models.zone import Zone

# Must match the frontend CameraFeed's SVG viewBox (see App.jsx / CameraFeed.jsx).
ZONE_SPACE_WIDTH = 1000
ZONE_SPACE_HEIGHT = 600


def _point_in_polygon(x: float, y: float, points: list[dict]) -> bool:
    if len(points) < 3:
        return False

    inside = False
    j = len(points) - 1
    for i in range(len(points)):
        xi, yi = points[i]["x"], points[i]["y"]
        xj, yj = points[j]["x"], points[j]["y"]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi:
            inside = not inside
        j = i
    return inside


def is_point_in_zone(camera_id: int | None, frame_x: float, frame_y: float, frame_width: int, frame_height: int) -> bool:
    """Checks whether a frame-pixel point falls inside a configured danger
    zone for the given camera. If no zones are configured at all (for this
    camera or globally), falls back to True so detection keeps working
    before any zone has been set up."""

    norm_x = frame_x / max(frame_width, 1) * ZONE_SPACE_WIDTH
    norm_y = frame_y / max(frame_height, 1) * ZONE_SPACE_HEIGHT

    db = SessionLocal()
    try:
        zones = db.query(Zone).filter(Zone.is_active.is_(True)).all()
        if not zones:
            return True

        applicable_zones = [zone for zone in zones if zone.camera_id is None or zone.camera_id == camera_id]
        if not applicable_zones:
            return True

        return any(_point_in_polygon(norm_x, norm_y, zone.points) for zone in applicable_zones)
    finally:
        db.close()
