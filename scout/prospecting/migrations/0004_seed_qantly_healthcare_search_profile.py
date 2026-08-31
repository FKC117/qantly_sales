from django.db import migrations


def seed_qantly_profile(apps, schema_editor):
    SearchProfile = apps.get_model("prospecting", "SearchProfile")
    SearchRole = apps.get_model("prospecting", "SearchRole")
    SearchSignal = apps.get_model("prospecting", "SearchSignal")
    SearchLocation = apps.get_model("prospecting", "SearchLocation")
    SearchIndustry = apps.get_model("prospecting", "SearchIndustry")

    profile, _ = SearchProfile.objects.get_or_create(
        name="Qantly Healthcare & Statistical Analytics",
        defaults={
            "description": "Analytics hiring signals for healthcare, research, and clinical organizations.",
            "freshness_days": 7,
            "is_active": True,
        },
    )
    for name, weight in [
        ("Biostatistician", 10), ("Statistical Analyst", 9), ("Clinical Data Analyst", 9),
        ("Research Analyst", 7), ("Data Analyst", 6), ("Epidemiologist", 9),
        ("Statistical Programmer", 8), ("Data Scientist", 6), ("Quantitative Analyst", 6),
    ]:
        SearchRole.objects.get_or_create(search_profile=profile, name=name, defaults={"weight": weight})
    for value, category, weight in [
        ("SPSS", "software", 6), ("SAS", "software", 8), ("Stata", "software", 6),
        ("R", "software", 7), ("Python", "software", 5), ("SQL", "software", 4),
        ("survival analysis", "method", 9), ("Kaplan-Meier", "method", 9),
        ("Cox regression", "method", 9), ("regression", "method", 5),
        ("hypothesis testing", "method", 5), ("clinical research", "domain_signal", 8),
        ("clinical trial", "domain_signal", 9), ("machine learning", "method", 3),
    ]:
        SearchSignal.objects.get_or_create(
            search_profile=profile, value=value, category=category, defaults={"weight": weight}
        )
    for country in ("USA", "UK", "Canada"):
        SearchLocation.objects.get_or_create(search_profile=profile, country=country)
    for name in ("Healthcare", "Pharmaceutical", "CRO", "Research", "University", "Clinical Research", "Analytics Consulting"):
        SearchIndustry.objects.get_or_create(search_profile=profile, name=name)


class Migration(migrations.Migration):
    dependencies = [("prospecting", "0003_searchprofile_search_configuration_and_model_renames")]

    operations = [migrations.RunPython(seed_qantly_profile, migrations.RunPython.noop)]
