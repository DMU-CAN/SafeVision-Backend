from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Equipment(Base):
    __tablename__ = "equipments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # "SERIAL": control_address is a serial device path (e.g. /dev/ttyACM0),
    # commands sent as line-based text (STOP/SLOW/RESUME), same protocol as
    # the legacy single-equipment /api/v1/equipment/* routes.
    # "NETWORK": control_address is host:port, commands POSTed as JSON — same
    # shape as the robot control channel (app/services/robot_controller.py).
    control_protocol: Mapped[str] = mapped_column(String(20), nullable=False)
    control_address: Mapped[str] = mapped_column(String(100), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
