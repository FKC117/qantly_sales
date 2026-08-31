from difflib import SequenceMatcher

from bs4 import BeautifulSoup
from django.utils import timezone

from ..models import Company, JobPosting, SearchProfile
from .schemas import DiscoveredJob, ParsedJobDetails


def parse_job_details(raw_content: str, search_profile: SearchProfile | None = None) -> ParsedJobDetails:
    description = BeautifulSoup(raw_content, "lxml").get_text(" ", strip=True)
    lower_description = description.lower()
    signals = search_profile.signals.filter(is_active=True) if search_profile else []
    matched_signal_objects = [signal for signal in signals if signal.value.lower() in lower_description]
    matched_signals = [signal.value for signal in matched_signal_objects]
    requirements = [
        signal.value
        for signal in matched_signal_objects
        if signal.category in {"skill", "software", "technology", "qualification"}
    ]

    seniority = next(
        (label for label in ("Senior", "Lead", "Principal", "Manager", "Director", "Junior") if label.lower() in lower_description),
        "",
    )
    department = ""
    return ParsedJobDetails(
        description=description,
        requirements=requirements,
        matched_signals=matched_signals,
        seniority=seniority,
        department=department,
    )


def parse_existing_job(job: JobPosting, search_profile: SearchProfile | None = None) -> JobPosting:
    search_profile = search_profile or job.search_profile
    parsed = parse_job_details(job.raw_content or job.description, search_profile)
    job.description = parsed.description
    job.requirements = parsed.requirements
    job.matched_signals = parsed.matched_signals
    job.seniority = parsed.seniority
    job.department = parsed.department
    job.parsed_at = timezone.now()
    job.status = JobPosting.Status.PARSED
    job.save(
        update_fields=[
            "description",
            "requirements",
            "matched_signals",
            "seniority",
            "department",
            "parsed_at",
            "status",
        ]
    )
    return job


def find_fuzzy_duplicate(company: Company, discovered_job: DiscoveredJob) -> JobPosting | None:
    """Conservatively match a mirrored vacancy without replacing its source record."""
    candidate_title = " ".join(discovered_job.title.lower().split())
    candidate_location = " ".join(discovered_job.location.lower().split())
    candidate_description = parse_job_details(discovered_job.raw_content or discovered_job.description).description.lower()
    for job in JobPosting.objects.filter(company=company):
        title_similarity = SequenceMatcher(None, candidate_title, " ".join(job.title.lower().split())).ratio()
        location_matches = not candidate_location or not job.location or candidate_location == " ".join(job.location.lower().split())
        description_similarity = SequenceMatcher(None, candidate_description, job.description.lower()).ratio()
        if title_similarity >= 0.95 and location_matches and description_similarity >= 0.75:
            return job
    return None


def job_matches_profile(discovered_job: DiscoveredJob, search_profile: SearchProfile) -> bool:
    title = discovered_job.title.lower()
    return any(role.name.lower() in title for role in search_profile.roles.filter(is_active=True))


def ingest_discovered_job(
    discovered_job: DiscoveredJob, search_profile: SearchProfile | None = None
) -> tuple[JobPosting, bool]:
    if discovered_job.company_domain:
        company, _ = Company.objects.get_or_create(
            domain=discovered_job.company_domain.lower(),
            defaults={"name": discovered_job.company_name},
        )
    else:
        company, _ = Company.objects.get_or_create(name=discovered_job.company_name, domain=None)

    job = None
    if discovered_job.source_job_id:
        job = JobPosting.objects.filter(
            source=discovered_job.source, source_job_id=discovered_job.source_job_id
        ).first()
    if job is None:
        job = JobPosting.objects.filter(source=discovered_job.source, source_url=discovered_job.source_url).first()
    if job is None:
        fuzzy_duplicate = find_fuzzy_duplicate(company, discovered_job)
        if fuzzy_duplicate:
            return fuzzy_duplicate, False

    parsed = parse_job_details(discovered_job.raw_content or discovered_job.description, search_profile)
    fields = {
        "company": company,
        "search_profile": search_profile,
        "title": discovered_job.title,
        "description": parsed.description,
        "location": discovered_job.location,
        "source": discovered_job.source,
        "source_url": discovered_job.source_url,
        "source_job_id": discovered_job.source_job_id,
        "posted_at": discovered_job.posted_at,
        "raw_content": discovered_job.raw_content or discovered_job.description,
        "requirements": parsed.requirements,
        "matched_signals": parsed.matched_signals,
        "seniority": parsed.seniority,
        "department": parsed.department,
        "parsed_at": timezone.now(),
        "status": JobPosting.Status.PARSED,
    }
    if job is None:
        return JobPosting.objects.create(**fields), True

    for field, value in fields.items():
        setattr(job, field, value)
    job.save(update_fields=fields)
    return job, False
