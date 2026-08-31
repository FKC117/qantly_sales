from urllib.parse import urlparse


def detect_job_source(url: str) -> str:
    hostname = urlparse(url).hostname or ""
    hostname = hostname.lower()
    if hostname in {"boards.greenhouse.io", "job-boards.greenhouse.io"}:
        return "greenhouse"
    if hostname == "jobs.lever.co":
        return "lever"
    if hostname == "jobs.ashbyhq.com":
        return "ashby"
    return "generic"
