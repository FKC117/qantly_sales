import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("prospecting", "0006_add_analytics_engineer_to_qantly_profile")]

    operations = [
        migrations.AddField(
            model_name="searchprofile",
            name="prospect_threshold",
            field=models.PositiveSmallIntegerField(
                default=70,
                help_text="Minimum relevance score required for automatic Prospect creation.",
                validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)],
            ),
        ),
        migrations.AddField(
            model_name="jobposting",
            name="relevance_score",
            field=models.PositiveSmallIntegerField(
                default=0,
                validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)],
            ),
        ),
        migrations.AddField(
            model_name="jobposting",
            name="relevance_label",
            field=models.CharField(
                choices=[("strong", "Strong"), ("review", "Review"), ("weak", "Weak")],
                default="weak",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="jobposting",
            name="relevance_reason",
            field=models.TextField(blank=True),
        ),
    ]
