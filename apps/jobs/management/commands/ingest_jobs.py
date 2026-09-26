from django.core.management.base import BaseCommand

from apps.jobs.models import JobSource
from apps.jobs.services.adapters import LinkedInJobAdapter
from apps.jobs.services.ingestion import JobIngestionService


class Command(BaseCommand):
    help = "Ingest jobs from an external source and persist them to the database."

    def add_arguments(self, parser):
        parser.add_argument("--source", dest="source", default="linkedin")
        parser.add_argument("--jobs", nargs="*", default=[])

    def handle(self, *args, **options):
        source_slug = options["source"]
        payloads = options["jobs"]

        source, _ = JobSource.objects.get_or_create(
            slug=source_slug,
            defaults={"name": source_slug.title(), "base_url": f"https://{source_slug}.example.com"},
        )

        if not payloads:
            adapter_map = {
                "linkedin": LinkedInJobAdapter,
            }
            adapter_cls = adapter_map.get(source_slug, LinkedInJobAdapter)
            payloads = adapter_cls(source_slug).fetch_jobs()

        result = JobIngestionService(source=source).ingest(payloads)
        self.stdout.write(self.style.SUCCESS(
            f"Created={result['created_count']}, Updated={result['updated_count']}, Failed={result['failed_count']}"
        ))
