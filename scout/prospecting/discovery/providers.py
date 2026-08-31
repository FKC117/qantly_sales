import json
from dataclasses import dataclass
from typing import Protocol

import httpx

from .queries import matches_target_role
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
    """Uses Greenhouse's unauthenticated public job-board endpoint."""

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
                    description = job.get("content") or ""
                    title = job.get("title") or ""
                    if not matches_target_role(title, description):
                        continue
                    discovered_jobs.append(
                        DiscoveredJob(
                            source=self.source_name,
                            source_url=job["absolute_url"],
                            source_job_id=str(job["id"]),
                            company_name=board.company_name,
                            company_domain=board.company_domain,
                            title=title,
                            description=description,
                            location=(job.get("location") or {}).get("name") or "",
                            posted_at=job.get("updated_at"),
                            raw_content=description,
                            metadata={"board_token": board.board_token},
                        )
                    )
        return discovered_jobs


def greenhouse_boards_from_json(value: str) -> list[GreenhouseBoard]:
    """Parse GREENHOUSE_BOARDS_JSON, keeping board configuration out of source code."""
    if not value.strip():
        return []
    configured_boards = json.loads(value)
    return [GreenhouseBoard(**board) for board in configured_boards]
