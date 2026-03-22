from datetime import datetime

from app.config.settings import get_settings
from app.modules.audit.audit_service import AuditService
from app.modules.news.news_service import NewsService
from app.shared.db.models import JobRun
from app.shared.utils.time import elapsed_ms


def collect_news_job(*, news_service: NewsService, audit_service: AuditService, mode: str) -> list[dict]:
    started_at = datetime.utcnow()
    db = news_service.db
    job_run = JobRun(job_name="collect-news", status="RUNNING", mode=mode, started_at=started_at)
    db.add(job_run)
    db.commit()
    settings = get_settings()

    try:
        news = [item.model_dump() for item in news_service.collect(settings.symbols)]
        audit_service.log(
            event_type="job.collect-news.completed",
            mode=mode,
            message=f"Collected {len(news)} news items",
            status="OK",
            raw_payload={"news": news},
        )
        finished_at = datetime.utcnow()
        job_run.status = "SUCCESS"
        job_run.finished_at = finished_at
        job_run.duration_ms = elapsed_ms(started_at, finished_at)
        job_run.summary = f"Collected {len(news)} news items"
        job_run.raw_payload = {"news": news}
        db.commit()
        return news
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
            collect_news_job(
                news_service=services.news_service,
                audit_service=services.audit_service,
                mode=settings.app_mode,
            )
        )
