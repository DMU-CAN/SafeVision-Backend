from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Robot(Base):
    __tablename__ = "robots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Stable identity for self-registration (see POST /robots/register) so a
    # robot re-announcing after a reboot/DHCP lease change updates its
    # existing row instead of creating a duplicate. Manually-created robots
    # (via the admin UI) leave this null. Typically the robot Pi's MAC address.
    hardware_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True, index=True)
    # host:port of the robot's onboard Raspberry Pi, reachable over wifi —
    # PTZ/movement commands are POSTed here (see services/robot_controller.py).
    control_address: Mapped[str] = mapped_column(String(100), nullable=False)
    camera_rtsp_url: Mapped[str] = mapped_column(String(255), nullable=False)
    location_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="IDLE")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
