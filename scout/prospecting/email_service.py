from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings

from .services import mark_outreach_sent


def send_approved_outreach(outreach):
    """Deliver an approved email and record it only after SMTP accepts it."""
    if outreach.status != outreach.Status.APPROVED:
        raise ValidationError("Outreach must be approved before it can be sent.")
    if not outreach.contact or not outreach.contact.email:
        raise ValidationError("Approved outreach requires a contact with an email address.")

    delivered_count = send_mail(
        subject=outreach.subject,
        message=outreach.body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[outreach.contact.email],
        fail_silently=False,
    )
    if delivered_count != 1:
        raise ValidationError("The email provider did not accept the outreach message.")

    return mark_outreach_sent(outreach)
