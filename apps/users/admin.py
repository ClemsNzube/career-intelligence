from django.contrib import admin

from .models import (
    CareerPreferences,
    CareerProfile,
    Certification,
    Education,
    Experience,
    Project,
)


@admin.register(CareerProfile)
class CareerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "year_of_experience", "preferred_work_type", "created_at")
    search_fields = ("user__username", "related_name", "bio")
    list_filter = ("preferred_work_type", "created_at")


@admin.register(CareerPreferences)
class CareerPreferencesAdmin(admin.ModelAdmin):
    list_display = ("career_profile", "min_years_of_experience", "max_years_of_experience")
    search_fields = ("career_profile__user__username",)
    list_filter = ("min_years_of_experience",)


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ("career_profile", "institution", "degree", "field_of_study", "start_date", "end_date")
    search_fields = ("institution", "degree", "field_of_study", "career_profile__user__username")
    list_filter = ("currently_studying", "start_date", "end_date")


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ("career_profile", "job_title", "company", "employment_type", "location", "start_date", "end_date")
    search_fields = ("job_title", "company", "location", "career_profile__user__username")
    list_filter = ("employment_type", "currently_working", "start_date")


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ("career_profile", "name", "issuing_organization", "issue_date", "expiration_date")
    search_fields = ("name", "issuing_organization", "credential_id", "career_profile__user__username")
    list_filter = ("issue_date", "expiration_date")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("career_profile", "name", "role", "start_date", "end_date")
    search_fields = ("name", "role", "description", "career_profile__user__username")
    list_filter = ("start_date", "end_date")
