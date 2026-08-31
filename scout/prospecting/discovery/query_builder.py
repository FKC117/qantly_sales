from ..models import SearchProfile


def build_search_queries(search_profile: SearchProfile) -> list[str]:
    """Build a bounded set of public-search queries from active database configuration."""
    roles = list(search_profile.roles.filter(is_active=True).order_by("-weight", "name"))
    signals = list(search_profile.signals.filter(is_active=True).order_by("-weight", "value"))
    industries = list(search_profile.industries.filter(is_active=True).order_by("name"))
    locations = list(search_profile.locations.filter(is_active=True).order_by("country", "region"))
    queries = []
    for role in roles:
        role_signals = signals or [None]
        role_locations = locations or [None]
        for signal in role_signals:
            for location in role_locations:
                parts = [f'role:"{role.name}"']
                if signal:
                    parts.append(f'signal:"{signal.value}"')
                if industries:
                    parts.append(industries[0].name)
                if location:
                    parts.append(f'location:"{location.region or location.country}"')
                parts.append("jobs")
                parts.append(f"past {search_profile.freshness_days} days")
                queries.append(" ".join(parts))
    return list(dict.fromkeys(queries))
