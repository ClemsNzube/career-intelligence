from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from apps.intelligence.embeddings.services import (
    EmbeddingService,
    build_job_text,
    build_profile_text,
)
from apps.intelligence.models import Embedding
from apps.jobs.models import Job
from apps.users.models import CareerProfile


class Command(BaseCommand):
    help = "Generate embeddings for career profiles and jobs that do not have one."

    def handle(self, *args, **options):
        service = EmbeddingService()
        generated = 0
        skipped = 0
        skipped_without_text = 0

        sources = (
            (
                CareerProfile,
                CareerProfile.objects.prefetch_related(
                    "skills",
                    "work_experiences__skills_used",
                    "projects__skills_used",
                ),
                build_profile_text,
            ),
            (Job, Job.objects.prefetch_related("skills"), build_job_text),
        )
        for model, objects, build_text in sources:
            content_type = ContentType.objects.get_for_model(model)
            existing_ids = set(
                Embedding.objects.filter(content_type=content_type).values_list(
                    "object_id", flat=True
                )
            )
            for obj in objects.iterator(chunk_size=100):
                if obj.pk in existing_ids:
                    skipped += 1
                    continue
                source_text = build_text(obj)
                if not source_text.strip():
                    skipped_without_text += 1
                    self.stderr.write(
                        self.style.WARNING(
                            f"Skipped {model._meta.label} pk={obj.pk}: no text available for embedding."
                        )
                    )
                    continue
                service.save_for_object(obj, source_text)
                generated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Generated {generated} embeddings; skipped {skipped} existing embeddings "
                f"and {skipped_without_text} objects without embeddable text."
            )
        )
