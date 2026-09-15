from django.conf import settings
from django.db import models
from apps.skills.models import Skill

class CareerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    related_name = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    year_of_experience = models.PositiveIntegerField(default=0)
    preferred_locations = models.JSONField(default=list, blank=True)
    preferred_work_type = models.CharField(max_length=20, blank=True, choices=[('remote', 'Remote'), ('onsite', 'Onsite'), ('hybrid', 'Hybrid')])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    skills = models.ManyToManyField(Skill, related_name='career_profiles', blank=True)

    def __str__(self):
        return f"{self.user.username}'s Career Profile"