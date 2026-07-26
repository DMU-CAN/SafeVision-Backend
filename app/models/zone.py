from sqlalchemy import JSON, Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    camera_id: Mapped[int | None] = mapped_column(ForeignKey("cameras.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Polygon vertices as [{"x": .., "y": ..}, ...] in the frontend's normalized
    # 1000x600 coordinate space (see CameraFeed's viewBox), independent of the
    # actual camera source resolution.
    points: Mapped[list] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
