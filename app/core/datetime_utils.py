from datetime import datetime, timezone
from typing import Annotated

from pydantic import AfterValidator


def ensure_utc(value: datetime) -> datetime:
    """SQLite drops tzinfo on round-trip even for columns declared
    DateTime(timezone=True), so datetimes read back from the DB come out
    naive even though every write path (`datetime.now(timezone.utc)`) is
    UTC. Without this, the serialized ISO string has no offset and clients
    (JS `Date`) parse it as local time instead of UTC, silently shifting
    every displayed timestamp by the browser's UTC offset."""
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


UtcDatetime = Annotated[datetime, AfterValidator(ensure_utc)]
