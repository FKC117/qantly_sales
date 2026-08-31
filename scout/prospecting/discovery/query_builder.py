from ..models import SearchProfile


def build_search_queries(search_profile: SearchProfile) -> list[str]:
    """Build a bounded set of public-search queries from active database configuration."""
    roles = list(search_profile.roles.filter(is_active=True).order_by("-weight", "name"))
    signals = list(search_profile.signals.filter(is_active=True).order_by("-weight", "value"))
    industries = list(search_profile.industries.filter(is_active=True).order_by("name"))
    locations = list(search_profile.locations.filter(is_active=True).order_by("country", "region"))
    queries = []
    for index, role in enumerate(roles):
        parts = [f'"{role.name}"']
        if signals:
            parts.append(f'"{signals[index % len(signals)].value}"')
        if industries:
            parts.append(industries[index % len(industries)].name)
        if locations:
            location = locations[index % len(locations)]
            parts.append(location.region or location.country)
        parts.append("jobs")
        parts.append(f"past {search_profile.freshness_days} days")
        queries.append(" ".join(parts))
    return list(dict.fromkeys(queries))
