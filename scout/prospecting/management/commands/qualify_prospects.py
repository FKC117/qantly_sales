from django.core.management.base import BaseCommand

from prospecting.models import Prospect
from prospecting.research.assessment import assess_prospect


class Command(BaseCommand):
    help = "Research and assess a bounded set of prospects. It never sends email."

    def add_arguments(self, parser):
        parser.add_argument("--status", default=Prospect.Status.DISCOVERED)
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit < 1 or limit > 100:
            self.stderr.write("--limit must be between 1 and 100.")
            return
        prospects = Prospect.objects.filter(status=options["status"]).order_by("-fit_score")[:limit]
        succeeded = failed = 0
        for prospect in prospects:
            try:
                assess_prospect(prospect, force_research=options["force"])
                succeeded += 1
            except Exception as error:
                failed += 1
                self.stderr.write(f"Prospect {prospect.id} failed: {error}")
        self.stdout.write(self.style.SUCCESS(f"Qualified {succeeded}; failed {failed}; no emails sent."))
