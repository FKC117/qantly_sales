from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Outreach, ProspectActivity


def log_activity(prospect, event_type, metadata=None):
    return ProspectActivity.objects.create(
        prospect=prospect,
        event_type=event_type,
        metadata=metadata or {},
    )


def submit_outreach_for_approval(outreach):
    if outreach.status != Outreach.Status.DRAFT:
        raise ValidationError("Only draft outreach can be submitted for approval.")

    outreach.status = Outreach.Status.AWAITING_APPROVAL
    outreach.save(update_fields=["status", "updated_at"])
    log_activity(outreach.prospect, ProspectActivity.EventType.OUTREACH_DRAFTED, {"outreach_id": outreach.id})
    return outreach


def approve_outreach(outreach, user):
    if outreach.status != Outreach.Status.AWAITING_APPROVAL:
        raise ValidationError("Only outreach awaiting approval can be approved.")

    approved_at = timezone.now()
    outreach.status = Outreach.Status.APPROVED
    outreach.approved_by = user
    outreach.approved_at = approved_at
    outreach.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    log_activity(
        outreach.prospect,
        ProspectActivity.EventType.OUTREACH_APPROVED,
        {"outreach_id": outreach.id, "approved_by_id": user.id},
    )
    return outreach


def reject_outreach(outreach, user):
    if outreach.status not in {Outreach.Status.DRAFT, Outreach.Status.AWAITING_APPROVAL}:
        raise ValidationError("Only unsent outreach can be rejected.")

    outreach.status = Outreach.Status.REJECTED
    outreach.save(update_fields=["status", "updated_at"])
    log_activity(
        outreach.prospect,
        ProspectActivity.EventType.OUTREACH_REJECTED,
        {"outreach_id": outreach.id, "rejected_by_id": user.id},
    )
    return outreach


def mark_outreach_sent(outreach):
    """Internal-only transition for a future email delivery task."""
    if outreach.status != Outreach.Status.APPROVED:
        raise ValidationError("Outreach must be approved before it can be sent.")

    sent_at = timezone.now()
    outreach.status = Outreach.Status.SENT
    outreach.sent_at = sent_at
    outreach.reply_status = Outreach.ReplyStatus.PENDING
    outreach.save(update_fields=["status", "sent_at", "reply_status", "updated_at"])
    log_activity(outreach.prospect, ProspectActivity.EventType.OUTREACH_SENT, {"outreach_id": outreach.id})
    return outreach
