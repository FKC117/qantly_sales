from django.utils import timezone

from ..models import Prospect, ProspectAssessment, ProspectEvent
from ..services import log_activity
from .services import research_prospect


def detect_account_type(prospect: Prospect) -> str:
    company = prospect.company
    evidence = f"{company.name} {company.industry} {company.description}".lower()
    if "recruit" in evidence or "staffing" in evidence or "talent" in evidence:
        return ProspectAssessment.AccountType.RECRUITER
    if "consult" in evidence or "advisory" in evidence:
        return ProspectAssessment.AccountType.CONSULTING
    if any(term in evidence for term in ("university", "hospital", "institute", "research center", "research centre")):
        return ProspectAssessment.AccountType.INSTITUTIONAL
    if "partner" in evidence or "channel" in evidence:
        return ProspectAssessment.AccountType.CHANNEL_PARTNER
    if "technology" in evidence or "software" in evidence:
        return ProspectAssessment.AccountType.TECHNOLOGY_PARTNER
    return ProspectAssessment.AccountType.DIRECT_ENTERPRISE if company.name else ProspectAssessment.AccountType.UNKNOWN


def _classification(account_type: str, technical_fit: int, near_term: int, strategic_value: int) -> str:
    if account_type in {
        ProspectAssessment.AccountType.RECRUITER,
        ProspectAssessment.AccountType.CONSULTING,
        ProspectAssessment.AccountType.CHANNEL_PARTNER,
        ProspectAssessment.AccountType.TECHNOLOGY_PARTNER,
    }:
        return ProspectAssessment.Classification.C
    if technical_fit >= 70 and near_term >= 60:
        return ProspectAssessment.Classification.A
    if strategic_value >= 60 or technical_fit >= 45:
        return ProspectAssessment.Classification.B
    if technical_fit < 20 and near_term < 20:
        return ProspectAssessment.Classification.E
    return ProspectAssessment.Classification.D


def _recommended_cta(account_type: str, customization_opportunity: int) -> str:
    if account_type in {ProspectAssessment.AccountType.RECRUITER, ProspectAssessment.AccountType.CHANNEL_PARTNER}:
        return "referral_partnership"
    if account_type in {ProspectAssessment.AccountType.CONSULTING, ProspectAssessment.AccountType.TECHNOLOGY_PARTNER}:
        return "partnership_discussion"
    if account_type == ProspectAssessment.AccountType.INSTITUTIONAL:
        return "research_pilot"
    return "custom_deployment" if customization_opportunity >= 60 else "try_qantly"


def assess_prospect(prospect: Prospect, *, force_research: bool = False) -> ProspectAssessment:
    """Persist explainable, deterministic sales qualification for one prospect."""
    try:
        research = research_prospect(prospect, force=force_research)
        job = prospect.job_posting
        active_jobs = prospect.company.job_postings.filter(status__in=["new", "parsed"]).count()
        current_matches = research.qantly_current_match
        gaps = research.customization_gap
        account_type = detect_account_type(prospect)

        technical_fit = min(100, len(current_matches) * 30 + min(20, job.relevance_score // 5))
        customization_opportunity = min(100, len(gaps) * 20 + (20 if job.relevance_label == "strong" else 0))
        ease_base = 65 if account_type in {
            ProspectAssessment.AccountType.RECRUITER,
            ProspectAssessment.AccountType.CONSULTING,
            ProspectAssessment.AccountType.CHANNEL_PARTNER,
        } else 50
        ease_of_entry = min(100, ease_base + (10 if research.research_confidence >= 70 else 0))
        near_term_conversion = min(100, job.relevance_score + min(20, max(0, active_jobs - 1) * 5))
        strategic_value = min(100, 35 + min(30, active_jobs * 5) + (20 if account_type == ProspectAssessment.AccountType.INSTITUTIONAL else 0) + (15 if account_type in {ProspectAssessment.AccountType.CONSULTING, ProspectAssessment.AccountType.TECHNOLOGY_PARTNER} else 0))
        classification = _classification(account_type, technical_fit, near_term_conversion, strategic_value)
        score_reasons = {
            "technical_fit": f"{len(current_matches)} active Qantly capability match(es); job relevance {job.relevance_score}.",
            "customization_opportunity": f"{len(gaps)} requirement(s) are separated as potential customization.",
            "ease_of_entry": f"Account type {account_type}; research confidence {research.research_confidence}.",
            "near_term_conversion": f"Job relevance {job.relevance_score}; {active_jobs} active company job posting(s).",
            "strategic_value": f"Account type {account_type}; repeated hiring considered from {active_jobs} posting(s).",
        }
        assessment, _ = ProspectAssessment.objects.get_or_create(prospect=prospect)
        assessment.technical_fit = technical_fit
        assessment.customization_opportunity = customization_opportunity
        assessment.ease_of_entry = ease_of_entry
        assessment.near_term_conversion = near_term_conversion
        assessment.strategic_value = strategic_value
        assessment.account_type = account_type
        assessment.classification = classification
        assessment.score_reasons = score_reasons
        assessment.overall_reason = f"Classification {classification} based on independent technical, entry, conversion, and strategic signals."
        assessment.recommended_cta = _recommended_cta(account_type, customization_opportunity)
        assessment.assessed_at = timezone.now()
        assessment.save()
        log_activity(prospect, ProspectEvent.EventType.ASSESSMENT_COMPLETED, {"assessment_id": assessment.id, "classification": classification})
        return assessment
    except Exception as error:
        log_activity(prospect, ProspectEvent.EventType.ASSESSMENT_FAILED, {"error": str(error)})
        raise
