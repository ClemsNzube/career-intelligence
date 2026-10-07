from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from pgvector.django import VectorField

from apps.intelligence.embeddings.providers.base import DEFAULT_EMBEDDING_DIMENSIONS


class Embedding(models.Model):
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="intelligence_embeddings",
    )
    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    source_text = models.TextField()
    embedding = VectorField(dimensions=DEFAULT_EMBEDDING_DIMENSIONS)
    model_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["model_name"]),
        ]

    def __str__(self):
        return f"{self.model_name} embedding for {self.content_type}#{self.object_id}"
