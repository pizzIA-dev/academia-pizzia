from functools import wraps
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages


def login_required_custom(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def course_member_required(view_func):
    """User must be teacher, moderator, or approved student of the course."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        from courses.models import Course
        course_pk = kwargs.get('pk') or kwargs.get('course_pk')
        if course_pk:
            course = get_object_or_404(Course, pk=course_pk)
            if not request.user.is_member_of(course):
                messages.error(request, 'No tienes acceso a este curso.')
                return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def course_manager_required(view_func):
    """User must be teacher or moderator of the course."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        from courses.models import Course
        course_pk = kwargs.get('pk') or kwargs.get('course_pk')
        if course_pk:
            course = get_object_or_404(Course, pk=course_pk)
            if not request.user.can_manage(course):
                messages.error(request, 'Solo profesores y moderadores pueden hacer esto.')
                return redirect('course_detail', pk=course_pk)
        return view_func(request, *args, **kwargs)
    return wrapper


def course_teacher_required(view_func):
    """User must be the course teacher (owner)."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        from courses.models import Course
        course_pk = kwargs.get('pk') or kwargs.get('course_pk')
        if course_pk:
            course = get_object_or_404(Course, pk=course_pk)
            if not request.user.is_teacher_of(course):
                messages.error(request, 'Solo el profesor del curso puede hacer esto.')
                return redirect('course_detail', pk=course_pk)
        return view_func(request, *args, **kwargs)
    return wrapper
