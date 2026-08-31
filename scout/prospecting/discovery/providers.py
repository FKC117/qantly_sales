import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

import httpx

from .schemas import DiscoveredJob


class SearchProvider(Protocol):
    def search_jobs(self, query: str) -> list[DiscoveredJob]: ...


class JobBoardProvider(Protocol):
    def fetch_jobs(self) -> list[DiscoveredJob]: ...


@dataclass(frozen=True)
class GreenhouseBoard:
    company_name: str
    board_token: str
    company_domain: str | None = None


class GreenhouseJobBoardProvider:
    """Optional ATS adapter for explicitly configured public Greenhouse boards."""

    source_name = "greenhouse"
    base_url = "https://boards-api.greenhouse.io/v1/boards"

    def __init__(self, boards: list[GreenhouseBoard], timeout: float = 20.0):
        self.boards = boards
        self.timeout = timeout

    def fetch_jobs(self) -> list[DiscoveredJob]:
        discovered_jobs = []
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            for board in self.boards:
                response = client.get(f"{self.base_url}/{board.board_token}/jobs", params={"content": "true"})
                response.raise_for_status()
                for job in response.json().get("jobs", []):
                    discovered_jobs.append(self.normalize_job(board, job))
        return discovered_jobs

    def normalize_job(self, board: GreenhouseBoard, job: dict) -> DiscoveredJob:
        description = job.get("content") or ""
        return DiscoveredJob(
            source=self.source_name,
            source_url=job["absolute_url"],
            source_job_id=str(job["id"]),
            company_name=board.company_name,
            company_domain=board.company_domain,
            title=job.get("title") or "",
            description=description,
            location=(job.get("location") or {}).get("name") or "",
            posted_at=job.get("updated_at"),
            raw_content=description,
            metadata={"board_token": board.board_token},
        )


class PublicWebSearchProvider:
    """Public-web provider facade. The Muse is the first supported live adapter."""

    def __init__(self, provider_name: str | None = None, api_key: str | None = None):
        self.provider_name = os.getenv("SEARCH_PROVIDER", "") if provider_name is None else provider_name
        self.api_key = os.getenv("SEARCH_API_KEY", "") if api_key is None else api_key
        self._adapter = TheMuseSearchProvider(api_key=self.api_key) if self.provider_name.lower() == "themuse" else None

    @property
    def is_configured(self) -> bool:
        return self.provider_name.lower() == "themuse"

    def search_jobs(self, query: str) -> list[DiscoveredJob]:
        if not self.is_configured:
            return []
        return self._adapter.search_jobs(query)


class TheMuseSearchProvider:
    """Live adapter for The Muse's public, unauthenticated jobs API.

    The API does not offer keyword filtering, so this adapter fetches a bounded
    number of public result pages and performs deterministic local matching.
    """

    source_name = "themuse"
    base_url = "https://www.themuse.com/api/public/jobs"

    def __init__(self, api_key: str | None = None, max_pages: int | None = None, timeout: float = 20.0):
        self.api_key = api_key or os.getenv("SEARCH_API_KEY", "")
        self.max_pages = max_pages or int(os.getenv("SEARCH_MAX_PAGES", "25"))
        self.timeout = timeout
        self._public_jobs: list[DiscoveredJob] | None = None

    def search_jobs(self, query: str) -> list[DiscoveredJob]:
        role_terms = [term.lower() for term in re.findall(r'"([^"]+)"', query)]
        freshness_days = self._freshness_days(query)
        return [
            job for job in self._fetch_public_jobs() if self._matches_query(job, role_terms, freshness_days)
        ]

    def _fetch_public_jobs(self) -> list[DiscoveredJob]:
        if self._public_jobs is not None:
            return self._public_jobs
        discovered_jobs = []
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            for page in range(self.max_pages):
                params = {"page": page}
                if self.api_key:
                    params["api_key"] = self.api_key
                response = client.get(self.base_url, params=params)
                response.raise_for_status()
                payload = response.json()
                for job in payload.get("results", []):
                    discovered_jobs.append(self.normalize_job(job))
                if page + 1 >= payload.get("page_count", 0):
                    break
        self._public_jobs = discovered_jobs
        return self._public_jobs

    def normalize_job(self, job: dict) -> DiscoveredJob:
        company = job.get("company") or {}
        refs = job.get("refs") or {}
        locations = job.get("locations") or []
        return DiscoveredJob(
            source=self.source_name,
            source_url=refs.get("landing_page") or job.get("url") or "",
            source_job_id=str(job["id"]),
            company_name=company.get("name") or "Unknown company",
            title=job.get("name") or "",
            description=job.get("contents") or job.get("short_description") or "",
            location=", ".join(location.get("name", "") for location in locations if location.get("name")),
            posted_at=job.get("publication_date"),
            raw_content=job.get("contents") or job.get("short_description") or "",
            metadata={"source": "The Muse"},
        )

    @staticmethod
    def _freshness_days(query: str) -> int | None:
        match = re.search(r"past\s+(\d+)\s+days", query, flags=re.IGNORECASE)
        return int(match.group(1)) if match else None

    @staticmethod
    def _matches_query(job: DiscoveredJob, role_terms: list[str], freshness_days: int | None) -> bool:
        searchable_text = f"{job.title} {job.description}".lower()
        role_matches = not role_terms or role_terms[0] in searchable_text
        if not role_matches:
            return False
        if freshness_days is None or job.posted_at is None:
            return True
        posted_at = job.posted_at
        if posted_at.tzinfo is None:
            posted_at = posted_at.replace(tzinfo=UTC)
        return posted_at >= datetime.now(UTC) - timedelta(days=freshness_days)


def greenhouse_boards_from_json(value: str) -> list[GreenhouseBoard]:
    """Parse GREENHOUSE_BOARDS_JSON, keeping board configuration out of source code."""
    if not value.strip():
        return []
    configured_boards = json.loads(value)
    return [GreenhouseBoard(**board) for board in configured_boards]
