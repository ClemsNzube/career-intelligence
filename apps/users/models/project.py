from django.db import models

from apps.skills.models import Skill
from .profile import CareerProfile


class Project(models.Model):
    career_profile = models.ForeignKey(
        CareerProfile,
        on_delete=models.CASCADE,
        related_name="projects",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    role = models.CharField(max_length=255, blank=True)
    project_url = models.URLField(max_length=500, blank=True)
    repository_url = models.URLField(max_length=500, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    skills_used = models.ManyToManyField(Skill, related_name="projects", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        ordering = ["-start_date", "-end_date", "name"]

    def __str__(self):
        return self.name
