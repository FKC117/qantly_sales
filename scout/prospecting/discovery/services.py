import re
from difflib import SequenceMatcher

from bs4 import BeautifulSoup
from django.utils import timezone

from ..models import Company, JobPosting
from .queries import ANALYTICS_KEYWORDS
from .schemas import DiscoveredJob, ParsedJobDetails


SKILL_PATTERNS = ("SPSS", "SAS", "R", "Python", "SQL", "Stata", "Tableau", "Power BI")
METHOD_PATTERNS = (
    "survival analysis",
    "Kaplan-Meier",
    "Cox regression",
    "hypothesis testing",
    "regression",
    "clinical trial",
    "machine learning",
)


def parse_job_details(raw_content: str) -> ParsedJobDetails:
    description = BeautifulSoup(raw_content, "lxml").get_text(" ", strip=True)
    lower_description = description.lower()
    requirements = [
        skill
        for skill in SKILL_PATTERNS
        if (re.search(r"\br\b", lower_description) if skill == "R" else skill.lower() in lower_description)
    ]
    analytics_signals = [method for method in METHOD_PATTERNS if method.lower() in lower_description]
    analytics_signals.extend(
        keyword for keyword in ANALYTICS_KEYWORDS if keyword.strip() and keyword in lower_description and keyword not in analytics_signals
    )

    seniority = next(
        (label for label in ("Senior", "Lead", "Principal", "Manager", "Director", "Junior") if label.lower() in lower_description),
        "",
    )
    department = next(
        (label for label in ("Clinical", "Research", "Biostatistics", "Data Science", "Analytics") if label.lower() in lower_description),
        "",
    )
    return ParsedJobDetails(
        description=description,
        requirements=requirements,
        analytics_signals=analytics_signals,
        seniority=seniority,
        department=department,
    )


def parse_existing_job(job: JobPosting) -> JobPosting:
    parsed = parse_job_details(job.raw_content or job.description)
    job.description = parsed.description
    job.requirements = parsed.requirements
    job.analytics_signals = parsed.analytics_signals
    job.seniority = parsed.seniority
    job.department = parsed.department
    job.parsed_at = timezone.now()
    job.status = JobPosting.Status.PARSED
    job.save(
        update_fields=[
            "description",
            "requirements",
            "analytics_signals",
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


def ingest_discovered_job(discovered_job: DiscoveredJob) -> tuple[JobPosting, bool]:
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

    parsed = parse_job_details(discovered_job.raw_content or discovered_job.description)
    fields = {
        "company": company,
        "title": discovered_job.title,
        "description": parsed.description,
        "location": discovered_job.location,
        "source": discovered_job.source,
        "source_url": discovered_job.source_url,
        "source_job_id": discovered_job.source_job_id,
        "posted_at": discovered_job.posted_at,
        "raw_content": discovered_job.raw_content or discovered_job.description,
        "requirements": parsed.requirements,
        "analytics_signals": parsed.analytics_signals,
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
