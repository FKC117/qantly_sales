from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("prospecting", "0002_jobposting_analytics_signals_jobposting_department_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="SearchProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255, unique=True)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("freshness_days", models.PositiveSmallIntegerField(default=7)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="SearchRole",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("weight", models.PositiveSmallIntegerField(default=1)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("search_profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="roles", to="prospecting.searchprofile")),
            ],
            options={"ordering": ["-weight", "name"]},
        ),
        migrations.CreateModel(
            name="SearchSignal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("value", models.CharField(max_length=255)),
                ("category", models.CharField(choices=[("skill", "Skill"), ("method", "Method"), ("software", "Software"), ("industry", "Industry"), ("domain_signal", "Domain signal"), ("technology", "Technology"), ("qualification", "Qualification")], max_length=20)),
                ("weight", models.PositiveSmallIntegerField(default=1)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("search_profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="signals", to="prospecting.searchprofile")),
            ],
            options={"ordering": ["-weight", "value"]},
        ),
        migrations.CreateModel(
            name="SearchLocation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("country", models.CharField(max_length=100)),
                ("region", models.CharField(blank=True, max_length=100)),
                ("is_active", models.BooleanField(default=True)),
                ("search_profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="locations", to="prospecting.searchprofile")),
            ],
            options={"ordering": ["country", "region"]},
        ),
        migrations.CreateModel(
            name="SearchIndustry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                ("is_active", models.BooleanField(default=True)),
                ("search_profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="industries", to="prospecting.searchprofile")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.RenameModel(old_name="Outreach", new_name="OutreachEmail"),
        migrations.RenameModel(old_name="ProspectActivity", new_name="ProspectEvent"),
        migrations.RenameField(model_name="jobposting", old_name="analytics_signals", new_name="matched_signals"),
        migrations.AddField(
            model_name="jobposting",
            name="search_profile",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="job_postings", to="prospecting.searchprofile"),
        ),
        migrations.AddConstraint(model_name="searchrole", constraint=models.UniqueConstraint(fields=("search_profile", "name"), name="unique_profile_role")),
        migrations.AddConstraint(model_name="searchsignal", constraint=models.UniqueConstraint(fields=("search_profile", "value", "category"), name="unique_profile_signal")),
        migrations.AddConstraint(model_name="searchlocation", constraint=models.UniqueConstraint(fields=("search_profile", "country", "region"), name="unique_profile_location")),
        migrations.AddConstraint(model_name="searchindustry", constraint=models.UniqueConstraint(fields=("search_profile", "name"), name="unique_profile_industry")),
    ]
