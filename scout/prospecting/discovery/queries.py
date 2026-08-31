TARGET_ROLE_TERMS = (
    "data analyst",
    "statistical analyst",
    "biostatistician",
    "clinical data analyst",
    "research analyst",
    "epidemiologist",
    "statistical programmer",
    "business intelligence analyst",
    "data scientist",
    "quantitative analyst",
)

ANALYTICS_KEYWORDS = (
    "spss",
    "sas",
    "python",
    "survival analysis",
    "kaplan-meier",
    "cox regression",
    "clinical trial",
    "hypothesis testing",
    "regression",
)


def matches_target_role(title: str, description: str = "") -> bool:
    searchable_text = f"{title} {description}".lower()
    return any(term in searchable_text for term in TARGET_ROLE_TERMS)


def configured_search_queries() -> list[str]:
    return [f'"{role}" hiring' for role in TARGET_ROLE_TERMS]
