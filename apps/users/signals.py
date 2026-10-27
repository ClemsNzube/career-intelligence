from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from apps.intelligence.normalization.profile_skills import (
    sync_profile_skills_from_evidence,
)
from apps.users.models import CareerProfile, Experience, Project


@receiver(post_save, sender=CareerProfile, dispatch_uid="sync_profile_skills_after_profile_save")
def sync_skills_after_profile_save(sender, instance, **kwargs):
    sync_profile_skills_from_evidence(instance)


@receiver(post_save, sender=Experience, dispatch_uid="sync_profile_skills_after_experience_save")
def sync_skills_after_experience_save(sender, instance, **kwargs):
    sync_profile_skills_from_evidence(instance.career_profile)


@receiver(post_save, sender=Project, dispatch_uid="sync_profile_skills_after_project_save")
def sync_skills_after_project_save(sender, instance, **kwargs):
    sync_profile_skills_from_evidence(instance.career_profile)


def _sync_skills_after_related_add(sender, instance, action, **kwargs):
    if action == "post_add":
        sync_profile_skills_from_evidence(instance.career_profile)


m2m_changed.connect(
    _sync_skills_after_related_add,
    sender=Experience.skills_used.through,
    dispatch_uid="sync_profile_skills_after_experience_skill_add",
)
m2m_changed.connect(
    _sync_skills_after_related_add,
    sender=Project.skills_used.through,
    dispatch_uid="sync_profile_skills_after_project_skill_add",
)
