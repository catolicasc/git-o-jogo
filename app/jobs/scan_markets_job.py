from datetime import datetime

from app.config.settings import get_settings
from app.modules.audit.audit_service import AuditService
from app.modules.markets.markets_service import MarketsService
from app.shared.db.models import JobRun
from app.shared.utils.time import elapsed_ms


def scan_markets_job(*, markets_service: MarketsService, audit_service: AuditService, mode: str) -> list[dict]:
    started_at = datetime.utcnow()
    db = markets_service.db
    job_run = JobRun(job_name="scan-markets", status="RUNNING", mode=mode, started_at=started_at)
    db.add(job_run)
    db.commit()
    settings = get_settings()

    try:
        snapshots = [markets_service.collect_snapshot(symbol).model_dump() for symbol in settings.symbols]
        audit_service.log(
            event_type="job.scan-markets.completed",
            mode=mode,
            message=f"Collected {len(snapshots)} market snapshots",
            status="OK",
            raw_payload={"snapshots": snapshots},
        )
        finished_at = datetime.utcnow()
        job_run.status = "SUCCESS"
        job_run.finished_at = finished_at
        job_run.duration_ms = elapsed_ms(started_at, finished_at)
        job_run.summary = f"Collected {len(snapshots)} market snapshots"
        job_run.raw_payload = {"snapshots": snapshots}
        db.commit()
        return snapshots
    except Exception as exc:
        finished_at = datetime.utcnow()
        job_run.status = "FAILED"
        job_run.finished_at = finished_at
        job_run.duration_ms = elapsed_ms(started_at, finished_at)
        job_run.summary = str(exc)
        job_run.raw_payload = {"error": str(exc)}
        db.commit()
        raise


if __name__ == "__main__":
    from app.bootstrap import build_services
    from app.config.settings import get_settings
    from app.shared.db.session import SessionLocal

    settings = get_settings()
    with SessionLocal() as db:
        services = build_services(db, settings.app_mode)
        print(
            scan_markets_job(
                markets_service=services.markets_service,
                audit_service=services.audit_service,
                mode=settings.app_mode,
            )
        )
