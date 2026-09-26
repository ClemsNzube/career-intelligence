from django.db import models

from .profile import CareerProfile


class CareerPreferences(models.Model):
    career_profile = models.OneToOneField(
        CareerProfile,
        on_delete=models.CASCADE,
        related_name="preferences",
    )
    target_job_titles = models.JSONField(default=list, blank=True)
    target_industries = models.JSONField(default=list, blank=True)
    preferred_locations = models.JSONField(default=list, blank=True)
    preferred_work_types = models.JSONField(default=list, blank=True)
    min_years_of_experience = models.PositiveIntegerField(default=0)
    max_years_of_experience = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Career Preferences"
        verbose_name_plural = "Career Preferences"

    def __str__(self):
        return f"{self.career_profile.user.username}'s Career Preferences"
