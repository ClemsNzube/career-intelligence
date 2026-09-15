from rest_framework.generics import ListAPIView
from apps.jobs.models import Job
from apps.jobs.api.serializers import JobSerializer

class JobListAPIView(ListAPIView):
    queryset = Job.objects.prefetch_related("skills").all()
    serializer_class = JobSerializer