from django.db import models

from apps.skills.models import Skill
from .profile import CareerProfile


class Experience(models.Model):
    EMPLOYMENT_TYPE_CHOICES = [
        ("full_time", "Full-time"),
        ("part_time", "Part-time"),
        ("contract", "Contract"),
        ("internship", "Internship"),
        ("freelance", "Freelance"),
    ]

    career_profile = models.ForeignKey(
        CareerProfile,
        on_delete=models.CASCADE,
        related_name="work_experiences",
    )
    job_title = models.CharField(max_length=255)
    company = models.CharField(max_length=255)
    employment_type = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_TYPE_CHOICES,
        blank=True,
    )
    location = models.CharField(max_length=255, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    currently_working = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    skills_used = models.ManyToManyField(Skill, related_name="experiences", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Work Experience"
        verbose_name_plural = "Work Experience"
        ordering = ["-start_date", "-end_date", "company"]

    def __str__(self):
        return f"{self.job_title} at {self.company}"
