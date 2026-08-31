from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("prospecting", "0004_seed_qantly_healthcare_search_profile")]

    operations = [
        migrations.AlterField(
            model_name="outreachemail",
            name="prospect",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="outreach_emails", to="prospecting.prospect"),
        ),
        migrations.AlterField(
            model_name="prospectevent",
            name="prospect",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="prospecting.prospect"),
        ),
    ]
