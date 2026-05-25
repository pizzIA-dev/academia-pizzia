from django.contrib import admin
from .models import Course, Session, SessionMaterial, Activity, Submission


class SessionInline(admin.TabularInline):
    model = Session
    extra = 0


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'code', 'teacher', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'code', 'teacher__username')
    inlines = [SessionInline]
    filter_horizontal = ('students', 'moderators')


class MaterialInline(admin.TabularInline):
    model = SessionMaterial
    extra = 0


class ActivityInline(admin.TabularInline):
    model = Activity
    extra = 0


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'week_number', 'date')
    list_filter = ('course',)
    inlines = [MaterialInline, ActivityInline]


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'session', 'due_date', 'grade_type', 'submission_count')
    list_filter = ('grade_type',)

    def submission_count(self, obj):
        return obj.submissions.count()
    submission_count.short_description = 'Entregas'


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'activity', 'submitted_at', 'is_graded', 'grade')
    list_filter = ('activity__session__course',)
    search_fields = ('student__username',)
