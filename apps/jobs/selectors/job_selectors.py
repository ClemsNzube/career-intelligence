from django.db.models import QuerySet   
from apps.jobs.models import Job

def get_jobs(*, search: str | None = None, work_type: str | None = None, employment_type: str | None = None) -> QuerySet[Job]:
    """
    Returns a queryset of jobs filtered by the provided search, work_type, and employment_type parameters.
    """
    queryset = Job.objects.prefetch_related("skills").all()

    if search:
        queryset = queryset.filter(title__icontains=search)

    if work_type:
        queryset = queryset.filter(work_type=work_type)

    if employment_type:
        queryset = queryset.filter(employment_type=employment_type)

    return queryset