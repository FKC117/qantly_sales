from datetime import timedelta

from django.utils import timezone

from ..models import Prospect, ProspectEvent, ProspectResearch
from ..services import log_activity
from .providers import CompanyResearchProvider, StoredPublicEvidenceProvider
from .schemas import CapabilityComparison


RESEARCH_FRESHNESS_DAYS = 14


def _term_in_text(text: str, term: str) -> bool:
    from ..discovery.services import term_matches

    return term_matches(text, term)


def compare_qantly_capabilities(prospect: Prospect) -> CapabilityComparison:
    """Compare job evidence to active database capabilities; never infer a capability."""
    job = prospect.job_posting
    profile = job.search_profile
    if profile is None:
        return CapabilityComparison(customization_gap=list(job.requirements))
    text = f"{job.title} {job.description} {job.raw_content}"
    current_match = []
    matched_capability_terms = set()
    for capability in profile.capabilities.filter(is_active=True):
        evidence = next((term for term in capability.keywords if _term_in_text(text, term)), None)
        if evidence:
            current_match.append({"name": capability.name, "category": capability.category, "evidence": evidence})
            matched_capability_terms.update(term.lower() for term in capability.keywords)
    customization_gap = [
        requirement for requirement in job.requirements
        if requirement.lower() not in matched_capability_terms
    ]
    return CapabilityComparison(current_match=current_match, customization_gap=customization_gap)


def research_prospect(
    prospect: Prospect,
    *,
    provider: CompanyResearchProvider | None = None,
    force: bool = False,
) -> ProspectResearch:
    """Persist fresh, source-backed research or return a cached result."""
    existing = getattr(prospect, "research", None)
    fresh_after = timezone.now() - timedelta(days=RESEARCH_FRESHNESS_DAYS)
    if existing and existing.researched_at and existing.researched_at >= fresh_after and not force:
        return existing

    provider = provider or StoredPublicEvidenceProvider()
    try:
        result = provider.research_company(prospect)
        comparison = compare_qantly_capabilities(prospect)
        research, _ = ProspectResearch.objects.get_or_create(prospect=prospect)
        research.demand_evidence = result.demand_evidence
        research.research_summary = result.research_summary
        research.source_urls = [item.model_dump(mode="json") for item in result.source_urls]
        research.research_confidence = result.research_confidence
        research.qantly_current_match = comparison.current_match
        research.customization_gap = comparison.customization_gap
        research.researched_at = timezone.now()
        research.save(
            update_fields=[
                "demand_evidence", "research_summary", "source_urls", "research_confidence",
                "qantly_current_match", "customization_gap", "researched_at", "updated_at"
            ]
        )
        log_activity(
            prospect,
            ProspectEvent.EventType.RESEARCH_COMPLETED,
            {"research_id": research.id, "source_count": len(research.source_urls)},
        )
        return research
    except Exception as error:
        log_activity(prospect, ProspectEvent.EventType.RESEARCH_FAILED, {"error": str(error)})
        raise
