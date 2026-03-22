from sqlalchemy import select
from sqlalchemy.orm import Session

from app.shared.db.models import AuditLog


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def log(
        self,
        *,
        event_type: str,
        mode: str,
        message: str,
        symbol: str | None = None,
        rationale: str | None = None,
        status: str | None = None,
        raw_payload: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            event_type=event_type,
            mode=mode,
            message=message,
            symbol=symbol,
            rationale=rationale,
            status=status,
            raw_payload=raw_payload,
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def list_logs(self) -> list[AuditLog]:
        return list(self.db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100)))
