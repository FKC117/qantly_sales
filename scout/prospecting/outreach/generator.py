from ..models import Contact, OutreachEmail, Prospect, ProspectEvent
from ..services import log_activity
from .strategy import build_outreach_strategy


def generate_outreach_email(prospect: Prospect, contact: Contact | None = None) -> OutreachEmail:
    """Create a personalized draft from stored evidence; never send or overclaim."""
    research = prospect.research
    strategy = build_outreach_strategy(prospect)
    current_match = ", ".join(item["name"] for item in research.qantly_current_match) or "the needs visible in the role"
    customization = ", ".join(research.customization_gap)
    greeting = f"Hi {contact.name}," if contact else "Hello,"
    customization_sentence = (
        f" Separately, we could discuss whether a tailored approach for {customization} would be useful."
        if customization else ""
    )
    body = (
        f"{greeting}\n\n"
        f"I noticed {prospect.company.name} is hiring for {prospect.job_posting.title}. "
        f"That public hiring signal suggests a timely analytics need. Qantly's current relevant capability match is {current_match}."
        f"{customization_sentence}\n\n"
        f"Would a {strategy.motion} be useful? You can also explore qantly.ai.\n\nBest,\nQantly"
    )
    outreach = OutreachEmail.objects.create(
        prospect=prospect,
        contact=contact,
        subject=f"Qantly and {prospect.company.name}'s {prospect.job_posting.title} hiring signal",
        body=body,
        status=OutreachEmail.Status.DRAFT,
    )
    log_activity(prospect, ProspectEvent.EventType.OUTREACH_GENERATED, {"outreach_id": outreach.id, "cta": strategy.cta})
    return outreach
