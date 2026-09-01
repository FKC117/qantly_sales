"""Provider contracts for externally sourced company and contact enrichment."""

from dataclasses import dataclass, field
from typing import Protocol

from .models import Company


@dataclass(frozen=True)
class CompanyResearchResult:
    website: str = ""
    industry: str = ""
    description: str = ""
    country: str = ""
    facts: list[dict[str, str]] = field(default_factory=list)


class CompanyEnrichmentProvider(Protocol):
    """Return source-backed company facts. Providers must not fabricate facts."""

    def enrich_company(self, company: Company) -> CompanyResearchResult: ...


@dataclass(frozen=True)
class DiscoveredContact:
    name: str
    job_title: str = ""
    email: str = ""
    source_url: str = ""
    verification_status: str = "unverified"


class ContactProvider(Protocol):
    """Discover publicly sourced contacts for the supplied company and target roles."""

    def find_contacts(self, company: Company, target_roles: list[str]) -> list[DiscoveredContact]: ...
