from app.config.settings import get_settings
from app.shared.db.models import AuditLog
from app.shared.db.session import SessionLocal


def main() -> None:
    settings = get_settings()
    with SessionLocal() as db:
        db.add(
            AuditLog(
                event_type="seed.completed",
                mode=settings.app_mode,
                message="Initial Python seed executed",
                status="OK",
                raw_payload={"seed": "python"},
            )
        )
        db.commit()


if __name__ == "__main__":
    main()
