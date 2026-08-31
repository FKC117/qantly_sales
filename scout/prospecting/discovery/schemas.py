from datetime import datetime

from pydantic import BaseModel, Field


class DiscoveredJob(BaseModel):
    source: str
    source_url: str
    company_name: str
    company_domain: str | None = None
    title: str
    description: str = ""
    location: str = ""
    source_job_id: str = ""
    posted_at: datetime | None = None
    raw_content: str = ""
    metadata: dict = Field(default_factory=dict)


class ParsedJobDetails(BaseModel):
    description: str
    requirements: list[str] = Field(default_factory=list)
    matched_signals: list[str] = Field(default_factory=list)
    seniority: str = ""
    department: str = ""
