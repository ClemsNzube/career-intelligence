from django.db.models import Q
from django.utils import timezone

from apps.jobs.models import Job
from apps.users.models import CareerProfile


def get_profile_for_user(user):
    return CareerProfile.objects.prefetch_related("skills").filter(user=user).first()


def get_available_jobs():
    return Job.objects.prefetch_related("skills").filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))