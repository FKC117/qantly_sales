import os

from celery import shared_task

from .discovery.providers import GreenhouseJobBoardProvider, greenhouse_boards_from_json
from .discovery.services import ingest_discovered_job, parse_existing_job
from .email_service import send_approved_outreach
from .models import JobPosting, Outreach


@shared_task(bind=True, autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def send_approved_outreach_task(self, outreach_id):
    """Background-only SMTP delivery; never call this task for unapproved outreach."""
    outreach = Outreach.objects.select_related("contact", "prospect__company").get(pk=outreach_id)
    send_approved_outreach(outreach)
    return {"outreach_id": outreach_id, "status": Outreach.Status.SENT}


@shared_task(autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def discover_jobs_task():
    """Fetch configured public Greenhouse boards and ingest target analytics roles."""
    boards = greenhouse_boards_from_json(os.getenv("GREENHOUSE_BOARDS_JSON", ""))
    provider = GreenhouseJobBoardProvider(boards)
    created_count = 0
    updated_count = 0
    for discovered_job in provider.fetch_jobs():
        _, created = ingest_discovered_job(discovered_job)
        if created:
            created_count += 1
        else:
            updated_count += 1
    return {"created": created_count, "updated": updated_count, "boards": len(boards)}


@shared_task
def parse_new_jobs_task():
    """Parse raw job postings created outside the provider ingestion flow."""
    jobs = JobPosting.objects.filter(status=JobPosting.Status.NEW)
    job_count = jobs.count()
    for job in jobs.iterator():
        parse_existing_job(job)
    return {"parsed": job_count}
