from django.db import models

from .profile import CareerProfile


class Education(models.Model):
    career_profile = models.ForeignKey(
        CareerProfile,
        on_delete=models.CASCADE,
        related_name="education_records",
    )
    institution = models.CharField(max_length=255)
    degree = models.CharField(max_length=255, blank=True)
    field_of_study = models.CharField(max_length=255, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    currently_studying = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Education"
        verbose_name_plural = "Education"
        ordering = ["-start_date", "-end_date", "institution"]

    def __str__(self):
        degree_text = self.degree or "Education"
        return f"{degree_text} at {self.institution}"
