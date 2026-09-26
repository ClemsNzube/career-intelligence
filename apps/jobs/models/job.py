import re
from html import unescape

from django.db import models
from django.utils import timezone

from apps.skills.models import Skill


class Job(models.Model):
    WORK_TYPE_CHOICES = [
        ("remote", "Remote"),
        ("onsite", "Onsite"),
        ("hybrid", "Hybrid"),
    ]
    EMPLOYMENT_TYPE_CHOICES = [
        ("full_time", "Full-time"),
        ("part_time", "Part-time"),
        ("contract", "Contract"),
        ("internship", "Internship"),
    ]
    title = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255)
    work_type = models.CharField(max_length=20, choices=WORK_TYPE_CHOICES)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES)
    application_url = models.URLField(max_length=500)
    source = models.CharField(max_length=255, blank=True)
    external_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    skills = models.ManyToManyField(Skill, related_name='jobs', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @staticmethod
    def normalize_title(value):
        text = re.sub(r"\s+", " ", (value or "").strip())
        if not text:
            return text

        tokens = text.split()
        normalized_tokens = []
        for token in tokens:
            lowercase = token.lower()
            if lowercase in {"ai", "api", "aws", "ci", "cd", "cto", "devops", "etl", "gcp", "ml", "sql", "ui", "ux"}:
                normalized_tokens.append(token.upper() if lowercase in {"ai", "api", "aws", "ci", "cd", "gcp", "ml", "sql", "ui", "ux"} else token.capitalize())
            else:
                normalized_tokens.append(token.capitalize())
        return " ".join(normalized_tokens)

    @staticmethod
    def clean_description(value):
        text = unescape(value or "")
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @property
    def is_expired(self):
        return self.expires_at is not None and self.expires_at <= timezone.now()

    def save(self, *args, **kwargs):
        if self.title:
            self.title = self.normalize_title(self.title)
        if self.description:
            self.description = self.clean_description(self.description)
        if self.application_url:
            self.application_url = self.application_url.strip()
        if self.source:
            self.source = self.source.strip()
        if self.external_id is not None:
            self.external_id = self.external_id.strip() or None
        if self.location:
            self.location = self.location.strip()
        if self.company_name:
            self.company_name = self.company_name.strip()

        return super().save(*args, **kwargs)

    def __str__(self):
        return self.title