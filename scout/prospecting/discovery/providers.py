import json
import os
from dataclasses import dataclass
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
    """Boundary for a future approved public-web search API integration.

    General web discovery deliberately returns no results while no provider is configured;
    Scout must not fabricate jobs or scrape authenticated/private sources.
    """

    def __init__(self, provider_name: str | None = None, api_key: str | None = None):
        self.provider_name = provider_name or os.getenv("SEARCH_PROVIDER", "")
        self.api_key = api_key or os.getenv("SEARCH_API_KEY", "")

    @property
    def is_configured(self) -> bool:
        return bool(self.provider_name and self.api_key)

    def search_jobs(self, query: str) -> list[DiscoveredJob]:
        if not self.is_configured:
            return []
        raise NotImplementedError(
            f"Search provider '{self.provider_name}' is configured but has no adapter yet. "
            "Add an approved provider adapter; do not fall back to scraping."
        )


def greenhouse_boards_from_json(value: str) -> list[GreenhouseBoard]:
    """Parse GREENHOUSE_BOARDS_JSON, keeping board configuration out of source code."""
    if not value.strip():
        return []
    configured_boards = json.loads(value)
    return [GreenhouseBoard(**board) for board in configured_boards]
