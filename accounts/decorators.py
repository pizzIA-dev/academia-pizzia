from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def teacher_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_teacher:
            messages.error(request, 'Solo los profesores pueden acceder a esta seccion.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def student_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_student:
            messages.error(request, 'Solo los estudiantes pueden acceder a esta seccion.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper
