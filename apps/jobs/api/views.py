from rest_framework.generics import ListAPIView
from apps.jobs.models import Job
from apps.jobs.api.serializers import JobSerializer

class JobListAPIView(ListAPIView):
    queryset = Job.objects.prefetch_related("skills").all()
    serializer_class = JobSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get("search")
        work_type = self.request.query_params.get("work_type")
        employment_type = self.request.query_params.get("employment_type")

        if search:
            queryset = queryset.filter(title__icontains=search)

        if work_type:
            queryset = queryset.filter(work_type=work_type)

        if employment_type:
            queryset = queryset.filter(employment_type=employment_type)

        return queryset.distinct()