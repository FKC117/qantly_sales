import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


def seed_qantly_capabilities(apps, schema_editor):
    SearchProfile = apps.get_model("prospecting", "SearchProfile")
    QantlyCapability = apps.get_model("prospecting", "QantlyCapability")
    profile = SearchProfile.objects.filter(name="Qantly Healthcare & Statistical Analytics").first()
    if not profile:
        return
    capabilities = [
        ("Descriptive statistics", "descriptive_statistics", ["descriptive statistics", "summary statistics"], 5),
        ("Hypothesis testing", "hypothesis_testing", ["hypothesis testing", "p-value", "t-test", "anova"], 7),
        ("Regression", "regression", ["regression", "logistic regression", "cox regression"], 8),
        ("Survival analysis", "survival_analysis", ["survival analysis", "kaplan-meier", "cox regression"], 10),
        ("Multivariate analysis", "multivariate_analysis", ["multivariate", "principal component", "factor analysis"], 6),
        ("Machine learning", "machine_learning", ["machine learning", "predictive model"], 4),
        ("Study design", "study_design", ["study design", "protocol", "clinical trial"], 8),
        ("Power analysis", "power_analysis", ["power analysis", "sample size"], 7),
        ("Data cleaning", "data_cleaning", ["data cleaning", "data quality"], 4),
        ("Visualization", "visualization", ["visualization", "data visualisation"], 3),
        ("Reporting", "reporting", ["reporting", "statistical report"], 3),
        ("Interpretation", "interpretation", ["interpretation", "insights"], 4),
    ]
    for name, category, keywords, weight in capabilities:
        QantlyCapability.objects.get_or_create(
            search_profile=profile,
            name=name,
            defaults={"category": category, "keywords": keywords, "weight": weight, "is_active": True},
        )


class Migration(migrations.Migration):
    dependencies = [("prospecting", "0007_job_relevance_and_prospect_threshold")]

    operations = [
        migrations.CreateModel(
            name="QantlyCapability",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                ("category", models.CharField(choices=[("descriptive_statistics", "Descriptive statistics"), ("hypothesis_testing", "Hypothesis testing"), ("regression", "Regression"), ("survival_analysis", "Survival analysis"), ("multivariate_analysis", "Multivariate analysis"), ("machine_learning", "Machine learning"), ("study_design", "Study design"), ("power_analysis", "Power analysis"), ("data_cleaning", "Data cleaning"), ("visualization", "Visualization"), ("reporting", "Reporting"), ("interpretation", "Interpretation")], max_length=30)),
                ("keywords", models.JSONField(blank=True, default=list)),
                ("weight", models.PositiveSmallIntegerField(default=5, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(20)])),
                ("is_active", models.BooleanField(default=True)),
                ("search_profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="capabilities", to="prospecting.searchprofile")),
            ],
            options={"ordering": ["category", "name"]},
        ),
        migrations.AddField(
            model_name="jobposting",
            name="capability_matches",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddConstraint(model_name="qantlycapability", constraint=models.UniqueConstraint(fields=("search_profile", "name"), name="unique_profile_capability")),
        migrations.RunPython(seed_qantly_capabilities, migrations.RunPython.noop),
    ]
