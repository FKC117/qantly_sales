from typing import Protocol

from ..models import Prospect
from .schemas import ProspectResearchResult, ResearchEvidence


class CompanyResearchProvider(Protocol):
    """Return normalized, public, source-backed evidence for a prospect."""

    def research_company(self, prospect: Prospect) -> ProspectResearchResult: ...


class StoredPublicEvidenceProvider:
    """Use Scout's existing public job/company URLs without claiming new facts."""

    def research_company(self, prospect: Prospect) -> ProspectResearchResult:
        job = prospect.job_posting
        evidence = [
            ResearchEvidence(
                url=job.source_url,
                title=job.title,
                source_type="job",
                summary="Public job posting discovered by Scout.",
            )
        ]
        if prospect.company.website:
            evidence.append(
                ResearchEvidence(
                    url=prospect.company.website,
                    title=f"{prospect.company.name} website",
                    source_type="company_website",
                    summary="Company website recorded in Scout.",
                )
            )
        demand_evidence = f"Public hiring signal: {job.title}."
        summary = f"Research is based on {len(evidence)} stored public source{'s' if len(evidence) != 1 else ''}."
        return ProspectResearchResult(
            demand_evidence=demand_evidence,
            research_summary=summary,
            source_urls=evidence,
            research_confidence=55 if len(evidence) == 1 else 70,
        )
