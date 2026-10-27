from django.core.management.base import BaseCommand

from apps.intelligence.normalization.profile_skills import (
    classify_profile_skills,
    sync_profile_skills_from_evidence,
)
from apps.users.models import CareerProfile


class Command(BaseCommand):
    help = (
        "Link exact positive skill mentions and explicitly recorded experience/project "
        "skills to profiles; report uncertain mentions for review."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report proposed links without changing profile skills.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        linked_count = 0
        suggestion_count = 0
        profiles_count = 0

        profiles = CareerProfile.objects.prefetch_related(
            "skills",
            "work_experiences__skills_used",
            "projects__skills_used",
        )
        for profile in profiles.iterator(chunk_size=100):
            profiles_count += 1
            confirmed, suggestions = classify_profile_skills(profile)
            linked_ids = {skill.pk for skill in profile.skills.all()}
            explicit_skills = [
                skill
                for relation in (profile.work_experiences.all(), profile.projects.all())
                for item in relation
                for skill in item.skills_used.all()
                if skill.pk not in linked_ids
            ]
            to_link = {skill.pk: skill for skill in (*explicit_skills, *confirmed)}
            if not dry_run and to_link:
                sync_profile_skills_from_evidence(profile)
            linked_count += len(to_link)
            suggestion_count += len(suggestions)

            if suggestions:
                names = ", ".join(skill.name for skill, _ in suggestions)
                self.stdout.write(
                    f"Profile pk={profile.pk}: review suggestions: {names}"
                )

        action = "Would link" if dry_run else "Linked"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} {linked_count} skills across {profiles_count} profiles; "
                f"{suggestion_count} uncertain mentions need review."
            )
        )
