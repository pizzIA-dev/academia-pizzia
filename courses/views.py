from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import Http404
from .models import Course, Session, SessionMaterial, Activity, Submission, EnrollmentRequest
from .forms import CourseForm, SessionForm, MaterialUploadForm, ActivityForm, GradeForm
from accounts.decorators import course_manager_required, course_teacher_required


def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'courses/landing.html')


@login_required
def dashboard(request):
    user = request.user
    taught = user.get_taught_courses()
    moderated = user.get_moderated_courses()
    enrolled = user.get_enrolled_courses()
    pending_requests = {}
    for course in taught:
        count = course.get_pending_requests_count()
        if count:
            pending_requests[course.pk] = count
    return render(request, 'courses/dashboard.html', {
        'taught': taught,
        'moderated': moderated,
        'enrolled': enrolled,
        'pending_requests': pending_requests,
    })


@login_required
def course_create(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.teacher = request.user
            import random
            colors = ['#0ea5e9','#8b5cf6','#10b981','#f59e0b','#ef4444','#ec4899','#06b6d4']
            course.cover_color = random.choice(colors)
            course.save()
            messages.success(request, f'Curso "{course.title}" creado correctamente.')
            return redirect('course_detail', pk=course.pk)
    else:
        form = CourseForm()
    COLORS = ['#0ea5e9','#8b5cf6','#10b981','#f59e0b','#ef4444','#ec4899','#06b6d4','#84cc16']
    return render(request, 'courses/course_form.html', {
        'form': form, 'action': 'Crear',
        'colors': COLORS, 'current_color': '#0ea5e9'})


@login_required
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    user = request.user
    if not user.is_member_of(course):
        messages.error(request, 'No tienes acceso a este curso.')
        return redirect('dashboard')
    sessions = course.sessions.all()
    is_owner = user.is_teacher_of(course)
    can_manage = user.can_manage(course)
    pending_count = course.get_pending_requests_count() if can_manage else 0
    return render(request, 'courses/course_detail.html', {
        'course': course,
        'sessions': sessions,
        'is_owner': is_owner,
        'can_manage': can_manage,
        'pending_count': pending_count,
    })


@login_required
def course_enroll(request, code):
    """Shareable enrollment link — creates an EnrollmentRequest."""
    course = get_object_or_404(Course, code=code, is_active=True)
    user = request.user

    if user.is_member_of(course):
        messages.info(request, f'Ya eres miembro de "{course.title}".')
        return redirect('course_detail', pk=course.pk)

    existing = EnrollmentRequest.objects.filter(user=user, course=course).first()

    if request.method == 'POST':
        if existing and existing.status == 'pending':
            messages.info(request, 'Ya tienes una solicitud pendiente para este curso.')
            return redirect('dashboard')
        message = request.POST.get('message', '').strip()
        if existing and existing.status == 'rejected':
            existing.status = 'pending'
            existing.message = message
            existing.reviewed_by = None
            existing.reviewed_at = None
            existing.save()
        else:
            EnrollmentRequest.objects.create(user=user, course=course, message=message)
        messages.success(request,
            f'Solicitud enviada para "{course.title}". El profesor te notificara cuando sea aprobada.')
        return redirect('dashboard')

    return render(request, 'courses/course_enroll.html', {
        'course': course,
        'existing': existing,
    })


@login_required
def enrollment_requests(request, pk):
    """List of pending enrollment requests for a course."""
    course = get_object_or_404(Course, pk=pk)
    if not request.user.can_manage(course):
        messages.error(request, 'No tienes permiso para ver esto.')
        return redirect('dashboard')
    pending = course.enrollment_requests.filter(status='pending').select_related('user')
    approved = course.enrollment_requests.filter(status='approved').select_related('user')
    rejected = course.enrollment_requests.filter(status='rejected').select_related('user')
    return render(request, 'courses/enrollment_requests.html', {
        'course': course,
        'pending': pending,
        'approved': approved,
        'rejected': rejected,
    })


@login_required
def enrollment_review(request, pk, req_pk, action):
    """Approve or reject an enrollment request."""
    course = get_object_or_404(Course, pk=pk)
    if not request.user.can_manage(course):
        messages.error(request, 'No tienes permiso.')
        return redirect('dashboard')
    enrollment = get_object_or_404(EnrollmentRequest, pk=req_pk, course=course)
    if action == 'approve':
        enrollment.approve(request.user)
        messages.success(request, f'{enrollment.user.display_name} fue aprobado en el curso.')
    elif action == 'reject':
        enrollment.reject(request.user)
        messages.warning(request, f'Solicitud de {enrollment.user.display_name} rechazada.')
    return redirect('enrollment_requests', pk=pk)


@login_required
def course_moderators(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if not request.user.is_teacher_of(course):
        messages.error(request, 'Solo el profesor puede gestionar moderadores.')
        return redirect('course_detail', pk=pk)
    moderators = course.moderators.all()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            from accounts.models import CustomUser
            username = request.POST.get('username', '').strip()
            try:
                user = CustomUser.objects.get(username=username)
                if user == course.teacher:
                    messages.error(request, 'El profesor no puede ser moderador.')
                elif course.moderators.filter(pk=user.pk).exists():
                    messages.warning(request, f'{username} ya es moderador.')
                elif not course.students.filter(pk=user.pk).exists():
                    messages.error(request, f'{username} debe ser estudiante del curso primero.')
                else:
                    course.moderators.add(user)
                    messages.success(request, f'{username} ahora es moderador.')
            except CustomUser.DoesNotExist:
                messages.error(request, f'Usuario "{username}" no encontrado.')
        elif action == 'remove':
            user_id = request.POST.get('user_id')
            from accounts.models import CustomUser
            try:
                user = CustomUser.objects.get(pk=user_id)
                course.moderators.remove(user)
                messages.success(request, f'Moderador {user.username} eliminado.')
            except CustomUser.DoesNotExist:
                pass
        return redirect('course_moderators', pk=pk)
    return render(request, 'courses/course_moderators.html', {
        'course': course, 'moderators': moderators})


@login_required
def session_create(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk)
    if not request.user.can_manage(course):
        messages.error(request, 'No tienes permiso.')
        return redirect('course_detail', pk=course_pk)
    if request.method == 'POST':
        form = SessionForm(request.POST, request.FILES)
        if form.is_valid():
            session = form.save(commit=False)
            session.course = course
            session.save()
            messages.success(request, 'Sesion creada.')
            return redirect('session_detail', pk=session.pk)
    else:
        form = SessionForm()
    return render(request, 'courses/session_form.html', {
        'form': form, 'course': course, 'action': 'Crear'})


@login_required
def session_detail(request, pk):
    session = get_object_or_404(Session, pk=pk)
    course = session.course
    if not request.user.is_member_of(course):
        messages.error(request, 'No tienes acceso.')
        return redirect('dashboard')
    materials = session.materials.all()
    activities = session.activities.all()
    can_manage = request.user.can_manage(course)
    return render(request, 'courses/session_detail.html', {
        'session': session, 'course': course,
        'materials': materials, 'activities': activities,
        'can_manage': can_manage,
    })


@login_required
def material_upload(request, session_pk):
    session = get_object_or_404(Session, pk=session_pk)
    course = session.course
    if not request.user.can_manage(course):
        messages.error(request, 'No tienes permiso.')
        return redirect('session_detail', pk=session_pk)
    if request.method == 'POST':
        form = MaterialUploadForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.session = session
            material.save()
            messages.success(request, 'Archivo subido correctamente.')
            return redirect('session_detail', pk=session_pk)
    else:
        form = MaterialUploadForm()
    return render(request, 'courses/material_form.html', {
        'form': form, 'session': session, 'course': course})


@login_required
def material_delete(request, pk):
    material = get_object_or_404(SessionMaterial, pk=pk)
    session = material.session
    if not request.user.can_manage(session.course):
        messages.error(request, 'No tienes permiso.')
        return redirect('session_detail', pk=session.pk)
    if request.method == 'POST':
        material.file.delete(save=False)
        material.delete()
        messages.success(request, 'Archivo eliminado.')
    return redirect('session_detail', pk=session.pk)


@login_required
def activity_create(request, session_pk):
    session = get_object_or_404(Session, pk=session_pk)
    course = session.course
    if not request.user.can_manage(course):
        messages.error(request, 'No tienes permiso.')
        return redirect('session_detail', pk=session_pk)
    if request.method == 'POST':
        form = ActivityForm(request.POST, request.FILES)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.session = session
            activity.save()
            messages.success(request, 'Actividad creada.')
            return redirect('session_detail', pk=session_pk)
    else:
        form = ActivityForm()
    return render(request, 'courses/activity_form.html', {
        'form': form, 'session': session, 'course': course})


@login_required
def activity_detail(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    session = activity.session
    course = session.course
    if not request.user.is_member_of(course):
        messages.error(request, 'No tienes acceso.')
        return redirect('dashboard')
    user = request.user
    can_manage = user.can_manage(course)
    user_submission = None
    sub_form = None
    if not can_manage:
        user_submission = Submission.objects.filter(activity=activity, student=user).first()
        if not user_submission:
            if request.method == 'POST':
                file = request.FILES.get('file')
                comment = request.POST.get('comment', '')
                if file:
                    Submission.objects.create(
                        activity=activity, student=user, file=file, comment=comment)
                    messages.success(request, 'Actividad entregada exitosamente.')
                    return redirect('activity_detail', pk=pk)
                else:
                    messages.error(request, 'Debes adjuntar un archivo.')
            sub_form = True
    return render(request, 'courses/activity_detail.html', {
        'activity': activity, 'session': session, 'course': course,
        'can_manage': can_manage, 'user_submission': user_submission,
        'sub_form': sub_form, 'now': timezone.now(),
    })


@login_required
def submissions_list(request, activity_pk):
    activity = get_object_or_404(Activity, pk=activity_pk)
    course = activity.session.course
    if not request.user.can_manage(course):
        messages.error(request, 'No tienes permiso.')
        return redirect('dashboard')
    submissions = activity.submissions.select_related('student').all()
    graded = submissions.filter(grade__isnull=False).exclude(grade='')
    pending = submissions.filter(grade__isnull=True) | submissions.filter(grade='')
    return render(request, 'courses/submissions_list.html', {
        'activity': activity, 'course': course,
        'submissions': submissions, 'graded': graded, 'pending': pending,
    })


@login_required
def grade_submission(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    activity = submission.activity
    course = activity.session.course
    if not request.user.can_manage(course):
        messages.error(request, 'No tienes permiso.')
        return redirect('dashboard')
    grade_options = activity.get_grade_options()
    if request.method == 'POST':
        grade = request.POST.get('grade', '').strip()
        teacher_comment = request.POST.get('teacher_comment', '').strip()
        if grade:
            submission.grade = grade
            submission.teacher_comment = teacher_comment
            submission.graded_by = request.user
            submission.graded_at = timezone.now()
            submission.save()
            messages.success(request, f'Nota asignada: {grade}')
            return redirect('submissions_list', activity_pk=activity.pk)
        else:
            messages.error(request, 'Ingresa una nota.')
    return render(request, 'courses/grade_submission.html', {
        'submission': submission, 'activity': activity,
        'course': course, 'grade_options': grade_options,
    })


# ── EDIT / DELETE ──────────────────────────────────────────


@login_required
def course_edit(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if not request.user.is_teacher_of(course):
        messages.error(request, 'Solo el profesor puede editar el curso.')
        return redirect('course_detail', pk=pk)
    from .forms import CourseForm
    COLORS = ['#0ea5e9','#8b5cf6','#10b981','#f59e0b','#ef4444','#ec4899','#06b6d4','#84cc16']
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, 'Curso actualizado correctamente.')
            return redirect('course_detail', pk=pk)
    else:
        form = CourseForm(instance=course)
    return render(request, 'courses/course_form.html', {
        'form': form, 'course': course, 'action': 'Editar',
        'colors': COLORS, 'current_color': course.cover_color})


@login_required
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if not request.user.is_teacher_of(course):
        messages.error(request, 'Solo el profesor puede eliminar el curso.')
        return redirect('course_detail', pk=pk)
    if request.method == 'POST':
        title = course.title
        course.delete()
        messages.success(request, f'Curso "{title}" eliminado.')
        return redirect('dashboard')
    return render(request, 'courses/confirm_delete.html', {
        'object': course, 'type': 'curso',
        'cancel_url': 'course_detail', 'cancel_pk': pk})


@login_required
def session_edit(request, pk):
    session = get_object_or_404(Session, pk=pk)
    course = session.course
    if not request.user.can_manage(course):
        messages.error(request, 'No tienes permiso para editar esta sesion.')
        return redirect('session_detail', pk=pk)
    if request.method == 'POST':
        from .forms import SessionForm
        form = SessionForm(request.POST, request.FILES, instance=session)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sesion actualizada.')
            return redirect('session_detail', pk=pk)
    else:
        from .forms import SessionForm
        form = SessionForm(instance=session)
    return render(request, 'courses/session_form.html', {
        'form': form, 'course': course, 'session': session,
        'action': 'Editar', 'cancel_pk': session.pk})


@login_required
def session_delete(request, pk):
    session = get_object_or_404(Session, pk=pk)
    course = session.course
    if not request.user.can_manage(course):
        messages.error(request, 'No tienes permiso.')
        return redirect('session_detail', pk=pk)
    if request.method == 'POST':
        course_pk = course.pk
        session.delete()
        messages.success(request, 'Sesion eliminada.')
        return redirect('course_detail', pk=course_pk)
    return render(request, 'courses/confirm_delete.html', {
        'object': session, 'type': 'sesion',
        'cancel_url': 'session_detail', 'cancel_pk': pk})


@login_required
def activity_edit(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    session = activity.session
    course = session.course
    if not request.user.can_manage(course):
        messages.error(request, 'No tienes permiso.')
        return redirect('activity_detail', pk=pk)
    if request.method == 'POST':
        from .forms import ActivityForm
        form = ActivityForm(request.POST, request.FILES, instance=activity)
        if form.is_valid():
            form.save()
            messages.success(request, 'Actividad actualizada.')
            return redirect('activity_detail', pk=pk)
    else:
        from .forms import ActivityForm
        form = ActivityForm(instance=activity)
    return render(request, 'courses/activity_form.html', {
        'form': form, 'session': session, 'course': course,
        'activity': activity, 'action': 'Editar'})


@login_required
def activity_delete(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    session = activity.session
    course = session.course
    if not request.user.can_manage(course):
        messages.error(request, 'No tienes permiso.')
        return redirect('activity_detail', pk=pk)
    if request.method == 'POST':
        session_pk = session.pk
        activity.delete()
        messages.success(request, 'Actividad eliminada.')
        return redirect('session_detail', pk=session_pk)
    return render(request, 'courses/confirm_delete.html', {
        'object': activity, 'type': 'actividad',
        'cancel_url': 'activity_detail', 'cancel_pk': pk})


@login_required
def remove_student(request, pk, student_pk):
    """Teacher removes a student from course."""
    course = get_object_or_404(Course, pk=pk)
    if not request.user.is_teacher_of(course):
        messages.error(request, 'Solo el profesor puede remover estudiantes.')
        return redirect('course_detail', pk=pk)
    if request.method == 'POST':
        from accounts.models import CustomUser
        student = get_object_or_404(CustomUser, pk=student_pk)
        course.students.remove(student)
        course.moderators.remove(student)
        EnrollmentRequest.objects.filter(user=student, course=course).update(status='rejected')
        messages.success(request, f'{student.display_name} fue removido del curso.')
    return redirect('enrollment_requests', pk=pk)



def _get_cloudinary_file_url(url, file_type, for_download=False):
    """
    Fix Cloudinary URLs:
    - Old files stored as /image/upload/ need .pdf/.docx etc. appended
    - New files stored as /raw/upload/ work as-is
    For download, we just return the URL and let the proxy handle headers.
    """
    if not url:
        return url

    # Map file types to extensions
    EXT_MAP = {
        'pdf': '.pdf', 'ppt': '.pptx', 'word': '.docx',
        'excel': '.xlsx', 'video': '.mp4',
    }

    # If it's a raw URL, return as-is (new uploads)
    if '/raw/upload/' in url:
        return url

    # Old image-type URL: check if it already has an extension
    base = url.split('?')[0]
    last_part = base.split('/')[-1]
    has_ext = '.' in last_part.split('_')[-1]  # Cloudinary IDs have underscores

    if not has_ext and file_type in EXT_MAP:
        # Append the correct extension so Cloudinary serves original file
        url = url + EXT_MAP[file_type]

    return url

@login_required
def download_material(request, pk):
    """
    Smart download:
    - Videos/audio  → redirect directly to Cloudinary CDN.
    - Docs/PDFs     → proxy through Django, fixing the URL for old image-type uploads.
    """
    import requests as req
    from django.http import HttpResponse
    material = get_object_or_404(SessionMaterial, pk=pk)
    course = material.session.course
    if not request.user.is_member_of(course):
        messages.error(request, 'No tienes acceso a este archivo.')
        return redirect('dashboard')

    raw_url = material.file.url
    VIDEO_TYPES = ('video', 'audio')

    if material.file_type in VIDEO_TYPES:
        # Videos: redirect to CDN — avoids loading huge files into RAM
        return redirect(raw_url)

    # Fix URL for old Cloudinary image-type uploads
    url = _get_cloudinary_file_url(raw_url, material.file_type, for_download=True)
    safe_name = material.name.replace('"', "\'")

    CONTENT_TYPES = {
        'pdf': 'application/pdf',
        'ppt': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'word': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'excel': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'zip': 'application/zip',
    }
    EXTENSIONS = {
        'pdf': '.pdf', 'ppt': '.pptx', 'word': '.docx', 'excel': '.xlsx', 'zip': '.zip'
    }
    ct = CONTENT_TYPES.get(material.file_type, 'application/octet-stream')
    ext = EXTENSIONS.get(material.file_type, '')
    if ext and not safe_name.endswith(ext):
        safe_name += ext

    try:
        r = req.get(url, timeout=30)
        r.raise_for_status()
        response = HttpResponse(r.content, content_type=ct)
        response['Content-Disposition'] = f'attachment; filename="{safe_name}"'
        return response
    except Exception as e:
        # Fallback: redirect directly to URL
        return redirect(url)


@login_required
def view_material(request, pk):
    """Proxy-serve a material file inline (for PDF preview in iframe)."""
    import requests as req
    from django.http import HttpResponse
    material = get_object_or_404(SessionMaterial, pk=pk)
    course = material.session.course
    if not request.user.is_member_of(course):
        return redirect('dashboard')

    raw_url = material.file.url
    url = _get_cloudinary_file_url(raw_url, material.file_type)

    CONTENT_TYPES = {
        'pdf': 'application/pdf',
        'ppt': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'word': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'excel': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    }
    ct = CONTENT_TYPES.get(material.file_type, 'application/octet-stream')

    try:
        r = req.get(url, timeout=30)
        r.raise_for_status()
        response = HttpResponse(r.content, content_type=ct)
        # inline = let browser display it, not download
        response['Content-Disposition'] = f'inline; filename="{material.name}"'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        return response
    except Exception:
        return redirect(url)
