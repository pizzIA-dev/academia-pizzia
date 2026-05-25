import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import Http404
from django.conf import settings

from accounts.models import CustomUser
from accounts.decorators import teacher_required
from .models import Course, Session, SessionMaterial, Activity, Submission, COVER_COLORS
from .forms import (CourseForm, JoinCourseForm, SessionForm, SessionMaterialForm,
                    ActivityForm, SubmissionForm, GradeSubmissionForm, AddModeratorForm)


def can_manage(user, course):
    """Check if user can manage course (teacher or moderator)."""
    return user == course.teacher or course.moderators.filter(pk=user.pk).exists()


# ─────────────────── Landing ───────────────────
def landing_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'courses/landing.html')


# ─────────────────── Dashboard ───────────────────
@login_required
def dashboard_view(request):
    user = request.user
    if user.is_teacher:
        courses = Course.objects.filter(teacher=user).prefetch_related('students', 'sessions')
        moderated = Course.objects.filter(moderators=user)
        context = {
            'courses': courses,
            'moderated_courses': moderated,
            'total_students': sum(c.students.count() for c in courses),
        }
    else:
        courses = Course.objects.filter(students=user).prefetch_related('sessions')
        context = {'courses': courses}
    return render(request, 'courses/dashboard.html', context)


# ─────────────────── Courses ───────────────────
@login_required
@teacher_required
def course_create_view(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.teacher = request.user
            course.save()
            messages.success(request, f'Curso "{course.title}" creado. Codigo: {course.code}')
            return redirect('course_detail', pk=course.pk)
    else:
        form = CourseForm()
    return render(request, 'courses/course_form.html', {'form': form, 'colors': COVER_COLORS, 'action': 'Crear'})


@login_required
def course_join_view(request):
    if request.method == 'POST':
        form = JoinCourseForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            try:
                course = Course.objects.get(code=code, is_active=True)
                if course.is_member(request.user) or course.teacher == request.user:
                    messages.info(request, 'Ya eres miembro de este curso.')
                else:
                    course.students.add(request.user)
                    messages.success(request, f'Te uniste a "{course.title}" exitosamente.')
                return redirect('course_detail', pk=course.pk)
            except Course.DoesNotExist:
                messages.error(request, 'Codigo incorrecto o el curso no existe.')
    else:
        form = JoinCourseForm()
    return render(request, 'courses/course_join.html', {'form': form})


@login_required
def course_detail_view(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if not course.is_member(request.user) and request.user != course.teacher:
        messages.error(request, 'No tienes acceso a este curso.')
        return redirect('dashboard')
    sessions = course.sessions.prefetch_related('materials', 'activities').all()
    context = {
        'course': course,
        'sessions': sessions,
        'can_manage': can_manage(request.user, course),
        'is_owner': request.user == course.teacher,
    }
    return render(request, 'courses/course_detail.html', context)


@login_required
def course_moderators_view(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.user != course.teacher:
        messages.error(request, 'Solo el profesor puede gestionar moderadores.')
        return redirect('course_detail', pk=pk)
    form = AddModeratorForm()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            form = AddModeratorForm(request.POST)
            if form.is_valid():
                username = form.cleaned_data['username']
                try:
                    user = CustomUser.objects.get(username=username)
                    if user == course.teacher:
                        messages.error(request, 'El profesor no puede ser moderador.')
                    elif course.moderators.filter(pk=user.pk).exists():
                        messages.warning(request, f'{username} ya es moderador.')
                    else:
                        course.moderators.add(user)
                        course.students.add(user)
                        messages.success(request, f'{username} ahora es moderador del curso.')
                except CustomUser.DoesNotExist:
                    messages.error(request, f'Usuario "{username}" no encontrado.')
        elif action == 'remove':
            user_id = request.POST.get('user_id')
            try:
                user = CustomUser.objects.get(pk=user_id)
                course.moderators.remove(user)
                messages.success(request, f'{user.username} ya no es moderador.')
            except CustomUser.DoesNotExist:
                pass
        return redirect('course_moderators', pk=pk)
    context = {
        'course': course,
        'moderators': course.moderators.all(),
        'form': form,
    }
    return render(request, 'courses/course_moderators.html', context)


# ─────────────────── Sessions ───────────────────
@login_required
def session_create_view(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk)
    if not can_manage(request.user, course):
        messages.error(request, 'No tienes permiso para crear sesiones.')
        return redirect('course_detail', pk=course_pk)
    if request.method == 'POST':
        form = SessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.course = course
            session.save()
            messages.success(request, f'Sesion "{session.title}" creada.')
            return redirect('session_detail', pk=session.pk)
    else:
        next_week = course.sessions.count() + 1
        form = SessionForm(initial={'week_number': next_week})
    return render(request, 'courses/session_form.html', {'form': form, 'course': course, 'action': 'Crear'})


@login_required
def session_detail_view(request, pk):
    session = get_object_or_404(Session, pk=pk)
    course = session.course
    if not course.is_member(request.user) and request.user != course.teacher:
        raise Http404
    materials = session.materials.all()
    activities = session.activities.all()
    
    # For students, get their submissions
    student_submissions = {}
    if request.user.is_student:
        for activity in activities:
            try:
                sub = Submission.objects.get(activity=activity, student=request.user)
                student_submissions[activity.pk] = sub
            except Submission.DoesNotExist:
                pass

    context = {
        'session': session,
        'course': course,
        'materials': materials,
        'activities': activities,
        'can_manage': can_manage(request.user, course),
        'student_submissions': student_submissions,
    }
    return render(request, 'courses/session_detail.html', context)


@login_required
def material_upload_view(request, session_pk):
    session = get_object_or_404(Session, pk=session_pk)
    course = session.course
    if not can_manage(request.user, course):
        messages.error(request, 'No tienes permiso para subir materiales.')
        return redirect('session_detail', pk=session_pk)
    if request.method == 'POST':
        form = SessionMaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.session = session
            # Auto-detect file type
            ext = os.path.splitext(request.FILES['file'].name)[1].lower()
            if ext in ['.ppt', '.pptx']:
                material.file_type = 'ppt'
            elif ext in ['.xls', '.xlsx']:
                material.file_type = 'excel'
            elif ext in ['.doc', '.docx']:
                material.file_type = 'word'
            elif ext == '.pdf':
                material.file_type = 'pdf'
            else:
                material.file_type = 'other'
            material.save()
            messages.success(request, f'Archivo "{material.name}" subido exitosamente.')
            return redirect('session_detail', pk=session_pk)
    else:
        form = SessionMaterialForm()
    return render(request, 'courses/material_form.html', {'form': form, 'session': session, 'course': course})


@login_required
def material_delete_view(request, pk):
    material = get_object_or_404(SessionMaterial, pk=pk)
    session = material.session
    if not can_manage(request.user, session.course):
        messages.error(request, 'No tienes permiso.')
        return redirect('session_detail', pk=session.pk)
    if request.method == 'POST':
        material.delete()
        messages.success(request, 'Material eliminado.')
    return redirect('session_detail', pk=session.pk)


# ─────────────────── Activities ───────────────────
@login_required
def activity_create_view(request, session_pk):
    session = get_object_or_404(Session, pk=session_pk)
    course = session.course
    if not can_manage(request.user, course):
        messages.error(request, 'No tienes permiso para crear actividades.')
        return redirect('session_detail', pk=session_pk)
    if request.method == 'POST':
        form = ActivityForm(request.POST, request.FILES)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.session = session
            activity.save()
            messages.success(request, f'Actividad "{activity.title}" creada.')
            return redirect('activity_detail', pk=activity.pk)
    else:
        form = ActivityForm()
    return render(request, 'courses/activity_form.html', {'form': form, 'session': session, 'course': course})


@login_required
def activity_detail_view(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    course = activity.course
    if not course.is_member(request.user) and request.user != course.teacher:
        raise Http404

    user_submission = None
    if request.user.is_student:
        try:
            user_submission = Submission.objects.get(activity=activity, student=request.user)
        except Submission.DoesNotExist:
            pass

    sub_form = None
    if request.user.is_student and not user_submission:
        if request.method == 'POST':
            sub_form = SubmissionForm(request.POST, request.FILES)
            if sub_form.is_valid():
                submission = sub_form.save(commit=False)
                submission.activity = activity
                submission.student = request.user
                submission.save()
                messages.success(request, 'Tarea entregada exitosamente.')
                return redirect('activity_detail', pk=pk)
        else:
            sub_form = SubmissionForm()

    context = {
        'activity': activity,
        'course': course,
        'session': activity.session,
        'can_manage': can_manage(request.user, course),
        'user_submission': user_submission,
        'sub_form': sub_form,
        'now': timezone.now(),
    }
    return render(request, 'courses/activity_detail.html', context)


@login_required
def submissions_list_view(request, activity_pk):
    activity = get_object_or_404(Activity, pk=activity_pk)
    course = activity.course
    if not can_manage(request.user, course):
        messages.error(request, 'No tienes permiso para ver entregas.')
        return redirect('activity_detail', pk=activity_pk)
    submissions = activity.submissions.select_related('student').all()
    context = {
        'activity': activity,
        'course': course,
        'submissions': submissions,
        'pending': submissions.filter(grade__isnull=True) | submissions.filter(grade=''),
        'graded': submissions.exclude(grade__isnull=True).exclude(grade=''),
    }
    return render(request, 'courses/submissions_list.html', context)


@login_required
def grade_submission_view(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    activity = submission.activity
    course = activity.course
    if not can_manage(request.user, course):
        messages.error(request, 'No tienes permiso para calificar.')
        return redirect('submissions_list', activity_pk=activity.pk)

    grade_options = activity.get_grade_options()

    if request.method == 'POST':
        form = GradeSubmissionForm(request.POST, instance=submission)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.graded_by = request.user
            sub.graded_at = timezone.now()
            sub.save()
            messages.success(request, f'Nota asignada: {sub.grade}')
            return redirect('submissions_list', activity_pk=activity.pk)
    else:
        form = GradeSubmissionForm(instance=submission)

    if grade_options:
        form.fields['grade'].widget = forms.Select(
            choices=[('', '---------')] + [(g, g) for g in grade_options]
        )

    context = {
        'submission': submission,
        'activity': activity,
        'course': course,
        'form': form,
        'grade_options': grade_options,
    }
    return render(request, 'courses/grade_submission.html', context)
