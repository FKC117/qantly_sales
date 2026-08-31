from django.db import migrations


def add_analytics_engineer_role(apps, schema_editor):
    SearchProfile = apps.get_model("prospecting", "SearchProfile")
    SearchRole = apps.get_model("prospecting", "SearchRole")
    profile = SearchProfile.objects.get(name="Qantly Healthcare & Statistical Analytics")
    SearchRole.objects.get_or_create(search_profile=profile, name="Analytics Engineer", defaults={"weight": 6})


class Migration(migrations.Migration):
    dependencies = [("prospecting", "0005_update_renamed_model_related_names")]

    operations = [migrations.RunPython(add_analytics_engineer_role, migrations.RunPython.noop)]
