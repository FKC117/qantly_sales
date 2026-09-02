from pydantic import BaseModel, Field, HttpUrl


class ResearchEvidence(BaseModel):
    url: HttpUrl
    title: str
    source_type: str
    summary: str = ""


class ProspectResearchResult(BaseModel):
    demand_evidence: str = ""
    research_summary: str = ""
    source_urls: list[ResearchEvidence] = Field(default_factory=list)
    research_confidence: int = Field(default=0, ge=0, le=100)


class CapabilityComparison(BaseModel):
    current_match: list[dict[str, str]] = Field(default_factory=list)
    customization_gap: list[str] = Field(default_factory=list)
