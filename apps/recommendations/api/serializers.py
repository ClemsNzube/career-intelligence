from rest_framework import serializers

from apps.jobs.api.serializers import JobSerializer


class RecommendationSerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    score = serializers.FloatField()
    match = serializers.BooleanField()
    job = JobSerializer(read_only=True)
    components = serializers.DictField(child=serializers.FloatField())
    explanation = serializers.DictField()