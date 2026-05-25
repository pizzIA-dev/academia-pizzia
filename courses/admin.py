from django.contrib import admin
from .models import Course, Session, SessionMaterial, Activity, Submission, EnrollmentRequest


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "teacher", "code", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("title", "code", "teacher__username")
    filter_horizontal = ("students", "moderators")


@admin.register(EnrollmentRequest)
class EnrollmentRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "status", "requested_at", "reviewed_by")
    list_filter = ("status",)
    raw_id_fields = ("user", "reviewed_by")


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "week_number", "date")
    list_filter = ("course",)


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("title", "session", "due_date", "grade_type")


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("student", "activity", "submitted_at", "grade", "is_graded")
    list_filter = ("activity__session__course",)
