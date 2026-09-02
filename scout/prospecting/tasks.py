import os

from celery import shared_task

from .discovery.providers import (
    GreenhouseJobBoardProvider,
    JoobleUaeSearchProvider,
    PublicWebSearchProvider,
    greenhouse_boards_from_json,
)
from .discovery.query_builder import build_search_queries
from .discovery.services import ingest_discovered_job, job_matches_profile, parse_existing_job
from .email_service import send_approved_outreach
from .models import JobPosting, OutreachEmail, SearchProfile
from .metrics import calculate_funnel_metrics


@shared_task(bind=True, autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def send_approved_outreach_task(self, outreach_id):
    """Background-only SMTP delivery; never call this task for unapproved outreach."""
    outreach = OutreachEmail.objects.select_related("contact", "prospect__company").get(pk=outreach_id)
    send_approved_outreach(outreach)
    return {"outreach_id": outreach_id, "status": OutreachEmail.Status.SENT}


@shared_task(autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def discover_jobs_task(search_profile_id=None):
    """Discover jobs from database search intent and optional ATS adapters."""
    profiles = SearchProfile.objects.filter(is_active=True)
    if search_profile_id is not None:
        profiles = profiles.filter(pk=search_profile_id)
    public_web_provider = PublicWebSearchProvider()
    jooble_provider = JoobleUaeSearchProvider()
    search_providers = [provider for provider in (public_web_provider, jooble_provider) if provider.is_configured]
    boards = greenhouse_boards_from_json(os.getenv("GREENHOUSE_BOARDS_JSON", ""))
    greenhouse_provider = GreenhouseJobBoardProvider(boards)
    created_count = 0
    updated_count = 0
    query_count = 0
    provider_counts = {provider.source_name if hasattr(provider, "source_name") else "themuse": 0 for provider in search_providers}
    provider_errors = {}
    greenhouse_jobs = greenhouse_provider.fetch_jobs() if boards else []
    for profile in profiles:
        for query in build_search_queries(profile):
            query_count += 1
            for provider in search_providers:
                provider_name = provider.source_name if hasattr(provider, "source_name") else "themuse"
                try:
                    discovered_jobs = provider.search_jobs(query)
                except Exception as error:
                    provider_errors[provider_name] = str(error)
                    continue
                provider_counts[provider_name] += len(discovered_jobs)
                for discovered_job in discovered_jobs:
                    _, created = ingest_discovered_job(discovered_job, profile)
                    created_count += int(created)
                    updated_count += int(not created)
        for discovered_job in greenhouse_jobs:
            if not job_matches_profile(discovered_job, profile):
                continue
            _, created = ingest_discovered_job(discovered_job, profile)
            created_count += int(created)
            updated_count += int(not created)
    return {
        "created": created_count,
        "updated": updated_count,
        "queries": query_count,
        "greenhouse_boards": len(boards),
        "public_web_configured": public_web_provider.is_configured,
        "jooble_configured": jooble_provider.is_configured,
        "provider_matches": provider_counts,
        "provider_errors": provider_errors,
    }


@shared_task
def parse_new_jobs_task():
    """Parse raw job postings created outside the provider ingestion flow."""
    jobs = JobPosting.objects.filter(status=JobPosting.Status.NEW)
    job_count = jobs.count()
    for job in jobs.iterator():
        parse_existing_job(job)
    return {"parsed": job_count}


@shared_task
def calculate_metrics_task():
    """Calculate the current funnel without changing prospect or email state."""
    return calculate_funnel_metrics()
