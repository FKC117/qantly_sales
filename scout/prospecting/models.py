from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q


class Company(models.Model):
    name = models.CharField(max_length=255)
    domain = models.CharField(max_length=255, unique=True, blank=True)
    website = models.URLField(blank=True)
    industry = models.CharField(max_length=150, blank=True)
    country = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class JobPosting(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        PARSED = "parsed", "Parsed"
        INVALID = "invalid", "Invalid"
        ARCHIVED = "archived", "Archived"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="job_postings")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    source = models.CharField(max_length=100)
    source_url = models.URLField()
    source_job_id = models.CharField(max_length=255, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    discovered_at = models.DateTimeField(auto_now_add=True)
    raw_content = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status, default=Status.NEW)

    class Meta:
        ordering = ["-discovered_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "source_job_id"],
                condition=Q(source_job_id__gt=""),
                name="unique_populated_source_job_id",
            )
        ]

    def __str__(self):
        return f"{self.company.name} — {self.title}"


class Prospect(models.Model):
    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    class Status(models.TextChoices):
        DISCOVERED = "discovered", "Discovered"
        QUALIFIED = "qualified", "Qualified"
        AWAITING_APPROVAL = "awaiting_approval", "Awaiting approval"
        APPROVED = "approved", "Approved"
        SENT = "sent", "Sent"
        REPLIED = "replied", "Replied"
        DEMO = "demo", "Demo"
        TRIAL = "trial", "Trial"
        CONVERTED = "converted", "Converted"
        LOST = "lost", "Lost"
        CLOSED = "closed", "Closed"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="prospects")
    job_posting = models.OneToOneField(JobPosting, on_delete=models.CASCADE, related_name="prospect")
    fit_score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)], default=0
    )
    fit_reason = models.TextField(blank=True)
    priority = models.CharField(max_length=10, choices=Priority, default=Priority.MEDIUM)
    status = models.CharField(max_length=25, choices=Status, default=Status.DISCOVERED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fit_score", "-created_at"]

    def __str__(self):
        return f"{self.company.name} ({self.fit_score})"


class Contact(models.Model):
    class VerificationStatus(models.TextChoices):
        UNVERIFIED = "unverified", "Unverified"
        VERIFIED = "verified", "Verified"
        INVALID = "invalid", "Invalid"
        UNKNOWN = "unknown", "Unknown"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="contacts")
    name = models.CharField(max_length=255)
    job_title = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    source_url = models.URLField(blank=True)
    verification_status = models.CharField(
        max_length=20, choices=VerificationStatus, default=VerificationStatus.UNVERIFIED
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.company.name})"


class Outreach(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        AWAITING_APPROVAL = "awaiting_approval", "Awaiting approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    class ReplyStatus(models.TextChoices):
        NOT_APPLICABLE = "not_applicable", "Not applicable"
        PENDING = "pending", "Pending"
        REPLIED = "replied", "Replied"
        POSITIVE = "positive", "Positive reply"
        NEGATIVE = "negative", "Negative reply"

    prospect = models.ForeignKey(Prospect, on_delete=models.CASCADE, related_name="outreach")
    contact = models.ForeignKey(
        Contact, on_delete=models.SET_NULL, related_name="outreach", null=True, blank=True
    )
    subject = models.CharField(max_length=255)
    body = models.TextField()
    status = models.CharField(max_length=25, choices=Status, default=Status.DRAFT)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="approved_outreach",
        null=True,
        blank=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    reply_status = models.CharField(
        max_length=20, choices=ReplyStatus, default=ReplyStatus.NOT_APPLICABLE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.prospect.company.name}: {self.subject}"


class ProspectActivity(models.Model):
    class EventType(models.TextChoices):
        DISCOVERED = "discovered", "Discovered"
        QUALIFIED = "qualified", "Qualified"
        STATUS_CHANGED = "status_changed", "Status changed"
        OUTREACH_DRAFTED = "outreach_drafted", "Outreach drafted"
        OUTREACH_APPROVED = "outreach_approved", "Outreach approved"
        OUTREACH_REJECTED = "outreach_rejected", "Outreach rejected"
        OUTREACH_SENT = "outreach_sent", "Outreach sent"
        REPLY_RECEIVED = "reply_received", "Reply received"
        NOTE = "note", "Note"

    prospect = models.ForeignKey(Prospect, on_delete=models.CASCADE, related_name="activities")
    event_type = models.CharField(max_length=30, choices=EventType)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.prospect}: {self.get_event_type_display()}"
