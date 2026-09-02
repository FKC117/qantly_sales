"""Deterministic funnel metrics for the human-reviewed Scout workflow."""

from collections import Counter

from .models import OutreachEmail, Prospect


def _rate(numerator: int, denominator: int) -> float:
    return round((numerator / denominator) * 100, 1) if denominator else 0.0


def calculate_funnel_metrics() -> dict:
    prospects = Prospect.objects.all()
    outreach = OutreachEmail.objects.all()
    prospect_total = prospects.count()
    outreach_total = outreach.count()
    sent = outreach.filter(status=OutreachEmail.Status.SENT).count()
    replied = outreach.filter(reply_status__in=[OutreachEmail.ReplyStatus.REPLIED, OutreachEmail.ReplyStatus.POSITIVE, OutreachEmail.ReplyStatus.NEGATIVE]).count()
    positive = outreach.filter(reply_status=OutreachEmail.ReplyStatus.POSITIVE).count()
    statuses = Counter(prospects.values_list("status", flat=True))
    classifications = Counter(prospects.values_list("assessment__classification", flat=True))
    return {
        "prospects": prospect_total,
        "qualified_prospects": statuses[Prospect.Status.QUALIFIED],
        "approved_emails": outreach.filter(status__in=[OutreachEmail.Status.APPROVED, OutreachEmail.Status.SENT]).count(),
        "emails_sent": sent,
        "emails_replied": replied,
        "positive_replies": positive,
        "qualified_prospect_rate": _rate(statuses[Prospect.Status.QUALIFIED], prospect_total),
        "email_delivery_rate": _rate(sent, outreach_total),
        "reply_rate": _rate(replied, sent),
        "positive_reply_rate": _rate(positive, sent),
        "pipeline": dict(statuses),
        "classification": {key: value for key, value in classifications.items() if key},
    }
