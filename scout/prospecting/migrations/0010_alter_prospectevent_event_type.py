from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("prospecting", "0009_prospect_research_and_assessment")]

    operations = [
        migrations.AlterField(
            model_name="prospectevent",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("discovered", "Discovered"), ("qualified", "Qualified"), ("status_changed", "Status changed"),
                    ("outreach_drafted", "Outreach drafted"), ("outreach_approved", "Outreach approved"),
                    ("outreach_rejected", "Outreach rejected"), ("outreach_sent", "Outreach sent"),
                    ("reply_received", "Reply received"), ("research_completed", "Research completed"),
                    ("research_failed", "Research failed"), ("assessment_completed", "Assessment completed"),
                    ("assessment_failed", "Assessment failed"), ("outreach_generated", "Outreach generated"), ("note", "Note"),
                ],
                max_length=30,
            ),
        ),
    ]
