from __future__ import annotations

from datetime import datetime, timedelta, timezone


class Clock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class FrozenClock(Clock):
    def __init__(self, at: datetime | None = None):
        self._now = at or datetime(2026, 7, 9, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now = self._now + timedelta(seconds=seconds)
