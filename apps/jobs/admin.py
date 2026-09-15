from django.contrib import admin

from .models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "company_name",
        "work_type",
        "employment_type",
        "posted_at",
    )

    list_filter = (
        "work_type",
        "employment_type",
    )

    search_fields = (
        "title",
        "company_name",
        "description",
    )

    filter_horizontal = ("skills",)