import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("prospecting", "0008_qantly_capability_and_job_capability_matches")]

    operations = [
        migrations.CreateModel(
            name="ProspectResearch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("demand_evidence", models.TextField(blank=True)),
                ("qantly_current_match", models.JSONField(blank=True, default=list)),
                ("customization_gap", models.JSONField(blank=True, default=list)),
                ("internal_build_capability", models.CharField(blank=True, max_length=255)),
                ("existing_stack", models.JSONField(blank=True, default=list)),
                ("data_sensitivity", models.CharField(blank=True, max_length=255)),
                ("deployment_barrier", models.CharField(blank=True, max_length=255)),
                ("procurement_difficulty", models.CharField(blank=True, max_length=255)),
                ("buyer_user", models.JSONField(blank=True, default=list)),
                ("recommended_entry_person", models.CharField(blank=True, max_length=255)),
                ("recommended_entry_strategy", models.TextField(blank=True)),
                ("recommended_first_cta", models.CharField(blank=True, choices=[("try_qantly", "Try Qantly"), ("technical_feedback", "Technical feedback"), ("demo", "Demo"), ("pilot", "Pilot"), ("custom_deployment", "Custom deployment"), ("partnership_discussion", "Partnership discussion"), ("referral_partnership", "Referral partnership"), ("research_pilot", "Research pilot")], max_length=30)),
                ("research_summary", models.TextField(blank=True)),
                ("source_urls", models.JSONField(blank=True, default=list)),
                ("research_confidence", models.PositiveSmallIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ("researched_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("prospect", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="research", to="prospecting.prospect")),
            ],
        ),
        migrations.CreateModel(
            name="ProspectAssessment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("technical_fit", models.PositiveSmallIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ("customization_opportunity", models.PositiveSmallIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ("ease_of_entry", models.PositiveSmallIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ("near_term_conversion", models.PositiveSmallIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ("strategic_value", models.PositiveSmallIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ("account_type", models.CharField(choices=[("direct_enterprise", "Direct enterprise"), ("institutional", "Institutional"), ("channel_partner", "Channel partner"), ("technology_partner", "Technology partner"), ("recruiter", "Recruiter"), ("job_aggregator", "Job aggregator"), ("consulting", "Consulting"), ("unknown", "Unknown")], default="unknown", max_length=25)),
                ("classification", models.CharField(choices=[("A", "A — Contact now"), ("B", "B — Strategic entry"), ("C", "C — Partnership/channel"), ("D", "D — Research/watch"), ("E", "E — Do not pursue")], default="D", max_length=1)),
                ("overall_reason", models.TextField(blank=True)),
                ("score_reasons", models.JSONField(blank=True, default=dict)),
                ("recommended_cta", models.CharField(blank=True, choices=[("try_qantly", "Try Qantly"), ("technical_feedback", "Technical feedback"), ("demo", "Demo"), ("pilot", "Pilot"), ("custom_deployment", "Custom deployment"), ("partnership_discussion", "Partnership discussion"), ("referral_partnership", "Referral partnership"), ("research_pilot", "Research pilot")], max_length=30)),
                ("assessed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("prospect", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="assessment", to="prospecting.prospect")),
            ],
        ),
    ]
