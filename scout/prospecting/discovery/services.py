import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from bs4 import BeautifulSoup
from django.utils import timezone

from ..models import Company, JobPosting, Prospect, QantlyCapability, SearchProfile
from .schemas import DiscoveredJob, ParsedJobDetails


def term_matches(text: str, term: str) -> bool:
    """Match signals as complete tokens, including short values such as R or SAS."""
    return bool(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text, flags=re.IGNORECASE))


def parse_job_details(
    raw_content: str, search_profile: SearchProfile | None = None, title: str = ""
) -> ParsedJobDetails:
    description = BeautifulSoup(raw_content, "lxml").get_text(" ", strip=True)
    lower_description = description.lower()
    signals = search_profile.signals.filter(is_active=True) if search_profile else []
    matched_signal_objects = [signal for signal in signals if term_matches(description, signal.value)]
    matched_signals = [signal.value for signal in matched_signal_objects]
    requirements = [
        signal.value
        for signal in matched_signal_objects
        if signal.category in {"skill", "software", "technology", "qualification"}
    ]

    seniority = _seniority_from_title(title)
    department = ""
    return ParsedJobDetails(
        description=description,
        requirements=requirements,
        matched_signals=matched_signals,
        seniority=seniority,
        department=department,
    )


@dataclass(frozen=True)
class RelevanceAssessment:
    score: int
    label: str
    reason: str


DOMAIN_TERMS = ("healthcare", "health care", "clinical", "hospital", "patient", "medical", "pharma", "biomedical")
RESEARCH_TERMS = ("research", "trial", "study", "protocol", "publication", "epidemiology")
STATISTICAL_TERMS = ("statistical", "statistics", "biostatistics", "survival analysis", "regression", "hypothesis")
ENGINEERING_TERMS = ("data engineer", "data engineering", "etl", "pipeline", "airflow", "spark", "warehouse")
SOFTWARE_ENGINEERING_TERMS = ("backend", "software engineer", "software development", "microservice", "api development")
DASHBOARD_TERMS = ("dashboard", "power bi", "tableau", "reporting")


def _contains_any(text: str, terms: tuple[str, ...]) -> list[str]:
    return [term for term in terms if term_matches(text, term)]


def _seniority_from_title(title: str) -> str:
    levels = ("Senior", "Lead", "Principal", "Director", "Manager", "Junior")
    for level in levels:
        if term_matches(title, level):
            return level
    return ""


def relevance_label_for_score(score: int) -> str:
    if score >= 70:
        return JobPosting.RelevanceLabel.STRONG
    if score >= 45:
        return JobPosting.RelevanceLabel.REVIEW
    return JobPosting.RelevanceLabel.WEAK


def match_job_capabilities(text: str, search_profile: SearchProfile) -> list[dict[str, str | int]]:
    """Map a posting's evidence to the active, database-defined Qantly capabilities."""
    matches = []
    for capability in search_profile.capabilities.filter(is_active=True):
        evidence = next((keyword for keyword in capability.keywords if term_matches(text, keyword)), None)
        if evidence:
            matches.append(
                {
                    "name": capability.name,
                    "category": capability.category,
                    "evidence": evidence,
                    "weight": capability.weight,
                }
            )
    return matches


def score_job_relevance(discovered_job: DiscoveredJob, search_profile: SearchProfile) -> RelevanceAssessment:
    """Deterministically score a discovered job without discarding weak discovery results."""
    title = discovered_job.title or ""
    text = f"{title} {discovered_job.description or discovered_job.raw_content}".lower()
    score = 0
    reasons: list[str] = []
    active_roles = list(search_profile.roles.filter(is_active=True))
    active_signals = list(search_profile.signals.filter(is_active=True))
    active_industries = list(search_profile.industries.filter(is_active=True))
    capability_matches = match_job_capabilities(text, search_profile)

    exact_roles = [role.name for role in active_roles if term_matches(title, role.name)]
    if exact_roles:
        score += 30
        reasons.append(f"+30 target role: {exact_roles[0]}")
    else:
        role_tokens = [set(re.findall(r"\w+", role.name.lower())) for role in active_roles]
        if any(tokens and len(tokens & set(re.findall(r"\w+", title.lower()))) >= max(1, len(tokens) - 1) for tokens in role_tokens):
            score += 20
            reasons.append("+20 near target role")

    matched_signals = [signal for signal in active_signals if term_matches(text, signal.value)]
    methods = [signal.value for signal in matched_signals if signal.category == "method"]
    software = [signal.value for signal in matched_signals if signal.category in {"software", "technology", "skill"}]
    domain_signals = [signal.value for signal in matched_signals if signal.category in {"domain_signal", "industry"}]
    if methods:
        score += 20
        reasons.append(f"+20 statistical/method: {', '.join(methods[:3])}")
    if software:
        score += 10
        reasons.append(f"+10 software: {', '.join(software[:3])}")
    if domain_signals:
        score += 25
        reasons.append(f"+25 domain signal: {', '.join(domain_signals[:3])}")
    if capability_matches:
        capability_points = min(15, sum(int(match["weight"]) for match in capability_matches))
        score += capability_points
        reasons.append(f"+{capability_points} Qantly capability: {', '.join(match['name'] for match in capability_matches[:3])}")

    industry_matches = [industry.name for industry in active_industries if term_matches(text, industry.name)]
    domain_hits = _contains_any(text, DOMAIN_TERMS + RESEARCH_TERMS)
    if industry_matches or domain_hits:
        score += 25
        evidence = industry_matches[0] if industry_matches else domain_hits[0]
        reasons.append(f"+25 healthcare/research evidence: {evidence}")
    clinical_hits = _contains_any(text, ("clinical", "trial", "study", "protocol", "patient"))
    if clinical_hits:
        score += 15
        reasons.append(f"+15 clinical/research terminology: {clinical_hits[0]}")
    statistical_hits = _contains_any(text, STATISTICAL_TERMS)
    if statistical_hits and not methods:
        score += 10
        reasons.append(f"+10 statistical analysis: {statistical_hits[0]}")

    engineering_hits = _contains_any(text, ENGINEERING_TERMS)
    software_engineering_hits = _contains_any(text, SOFTWARE_ENGINEERING_TERMS)
    dashboard_hits = _contains_any(text, DASHBOARD_TERMS)
    if engineering_hits:
        score -= 25
        reasons.append(f"-25 data engineering emphasis: {engineering_hits[0]}")
    if software_engineering_hits:
        score -= 25
        reasons.append(f"-25 software engineering emphasis: {software_engineering_hits[0]}")
    if dashboard_hits and not (methods or statistical_hits or domain_hits):
        score -= 10
        reasons.append(f"-10 dashboard-only BI: {dashboard_hits[0]}")
    if not (methods or statistical_hits or domain_hits or industry_matches):
        score -= 20
        reasons.append("-20 no statistical/research evidence")

    score = max(0, min(100, score))
    label = relevance_label_for_score(score)
    reasons.append(f"Final score: {score}")
    return RelevanceAssessment(score=score, label=label, reason="\n".join(reasons))


def parse_existing_job(job: JobPosting, search_profile: SearchProfile | None = None) -> JobPosting:
    search_profile = search_profile or job.search_profile
    parsed = parse_job_details(job.raw_content or job.description, search_profile, job.title)
    discovered_job = DiscoveredJob(
        source=job.source,
        source_url=job.source_url,
        source_job_id=job.source_job_id,
        company_name=job.company.name,
        title=job.title,
        description=job.description,
        location=job.location,
        posted_at=job.posted_at,
        raw_content=job.raw_content,
    )
    assessment = score_job_relevance(discovered_job, search_profile) if search_profile else RelevanceAssessment(0, JobPosting.RelevanceLabel.WEAK, "Final score: 0")
    capability_matches = match_job_capabilities(
        f"{discovered_job.title} {discovered_job.description or discovered_job.raw_content}", search_profile
    ) if search_profile else []
    job.description = parsed.description
    job.requirements = parsed.requirements
    job.matched_signals = parsed.matched_signals
    job.seniority = parsed.seniority
    job.department = parsed.department
    job.relevance_score = assessment.score
    job.relevance_label = assessment.label
    job.relevance_reason = assessment.reason
    job.capability_matches = capability_matches
    job.parsed_at = timezone.now()
    job.status = JobPosting.Status.PARSED
    job.save(
        update_fields=[
            "description",
            "requirements",
            "matched_signals",
            "seniority",
            "department",
            "relevance_score",
            "relevance_label",
            "relevance_reason",
            "capability_matches",
            "parsed_at",
            "status",
        ]
    )
    _promote_strong_job(job, search_profile)
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

    parsed = parse_job_details(discovered_job.raw_content or discovered_job.description, search_profile, discovered_job.title)
    assessment = score_job_relevance(discovered_job, search_profile) if search_profile else RelevanceAssessment(0, JobPosting.RelevanceLabel.WEAK, "Final score: 0")
    capability_matches = match_job_capabilities(
        f"{discovered_job.title} {discovered_job.description or discovered_job.raw_content}", search_profile
    ) if search_profile else []
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
        "relevance_score": assessment.score,
        "relevance_label": assessment.label,
        "relevance_reason": assessment.reason,
        "capability_matches": capability_matches,
        "parsed_at": timezone.now(),
        "status": JobPosting.Status.PARSED,
    }
    if job is None:
        job = JobPosting.objects.create(**fields)
        _promote_strong_job(job, search_profile)
        return job, True

    for field, value in fields.items():
        setattr(job, field, value)
    job.save(update_fields=fields)
    _promote_strong_job(job, search_profile)
    return job, False


def _promote_strong_job(job: JobPosting, search_profile: SearchProfile | None) -> None:
    if not search_profile or job.relevance_score < search_profile.prospect_threshold:
        return
    Prospect.objects.get_or_create(
        job_posting=job,
        defaults={"company": job.company, "fit_score": job.relevance_score, "fit_reason": job.relevance_reason},
    )
