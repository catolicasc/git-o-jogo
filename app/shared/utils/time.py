from datetime import datetime


def now_utc() -> datetime:
    return datetime.utcnow()


def elapsed_ms(started_at: datetime, finished_at: datetime) -> int:
    return int((finished_at - started_at).total_seconds() * 1000)
