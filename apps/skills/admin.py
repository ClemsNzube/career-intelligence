from django.contrib import admin

from .models import Skill


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
	list_display = (
		"name",
		"category",
		"created_at",
		"updated_at",
	)

	list_filter = (
		"category",
	)

	search_fields = (
		"name",
		"slug",
		"category",
		"description",
	)

	prepopulated_fields = {
		"slug": ("name",),
	}
