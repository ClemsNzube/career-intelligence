import uuid

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models


def cv_upload_path(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower()
    return f"cvs/{instance.user_id}/{uuid.uuid4().hex}.{extension}"


class CVDocument(models.Model):
    class Status(models.TextChoices):
        PROCESSING = "processing", "Processing"
        REVIEW = "review", "Review required"
        APPROVED = "approved", "Approved"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cv_documents",
    )
    file = models.FileField(
        upload_to=cv_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "docx"])],
    )
    original_filename = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROCESSING,
    )
    extracted_text = models.TextField(blank=True)
    extracted_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]

    def __str__(self):
        return f"{self.original_filename} ({self.get_status_display()})"
