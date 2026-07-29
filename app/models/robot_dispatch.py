from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class RobotDispatch(Base):
    __tablename__ = "robot_dispatches"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    robot_id: Mapped[int] = mapped_column(ForeignKey("robots.id"), nullable=False)
    safety_event_id: Mapped[int | None] = mapped_column(ForeignKey("safety_events.id"), nullable=True)
    target_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    dispatched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
