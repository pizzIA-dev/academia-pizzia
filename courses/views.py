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
    students = course.students.all().order_by('first_name', 'last_name') if can_manage else None
    return render(request, 'courses/course_detail.html', {
        'course': course,
        'sessions': sessions,
        'is_owner': is_owner,
        'can_manage': can_manage,
        'pending_count': pending_count,
        'students': students,
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
    from .models import ClassRecording
    recordings = session.recordings.all()
    return render(request, 'courses/session_detail.html', {
        'session': session, 'course': course,
        'materials': materials, 'activities': activities,
        'recordings': recordings,
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
            try:
                material = form.save(commit=False)
                material.session = session
                material.save()
                messages.success(request, f'Archivo subido correctamente.')
                return redirect('session_detail', pk=session_pk)
            except Exception as e:
                messages.error(request, f'Error al subir el archivo: {str(e)[:150]}')
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
                files = request.FILES.getlist('files')
                comment = request.POST.get('comment', '')
                if not files:
                    # fallback: try single 'file' field
                    single = request.FILES.get('file')
                    if single:
                        files = [single]
                if files:
                    from .models import SubmissionFile
                    submission = Submission.objects.create(
                        activity=activity, student=user,
                        file=None, comment=comment)
                    for f in files:
                        SubmissionFile.objects.create(
                            submission=submission,
                            file=f,
                            original_name=f.name)
                    messages.success(request, f'Entrega realizada con {len(files)} archivo(s).')
                    return redirect('activity_detail', pk=pk)
                else:
                    messages.error(request, 'Debes adjuntar al menos un archivo.')
            sub_form = True
    # can_resubmit: student can modify submission only before due_date
    can_resubmit = (
        not can_manage and user_submission is not None and
        (not activity.due_date or timezone.now() <= activity.due_date)
    )
    return render(request, 'courses/activity_detail.html', {
        'activity': activity, 'session': session, 'course': course,
        'can_manage': can_manage, 'user_submission': user_submission,
        'sub_form': sub_form, 'now': timezone.now(),
        'can_resubmit': can_resubmit,
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







def _ext_and_ct(file_url, stored_name=''):
    """
    Extract file extension from Cloudinary URL (most reliable) or stored name.
    Cloudinary strips extension from public_id but preserves it in the URL.
    Returns (extension, content_type).
    """
    import os as _os
    from urllib.parse import urlparse as _up, unquote as _uq

    ext = ''
    # 1. Try URL path (Cloudinary URL includes extension)
    try:
        url_path = _up(file_url).path.split('?')[0]
        e = _os.path.splitext(_uq(url_path))[1].lower()
        if e and 2 <= len(e) <= 12:
            ext = e
    except Exception:
        pass
    # 2. Fallback: stored name
    if not ext and stored_name:
        ext = _os.path.splitext(stored_name)[1].lower()

    ct_map = {
        '.pdf':   'application/pdf',
        '.doc':   'application/msword',
        '.docx':  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.ppt':   'application/vnd.ms-powerpoint',
        '.pptx':  'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.xls':   'application/vnd.ms-excel',
        '.xlsx':  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.zip':   'application/zip',
        '.rar':   'application/x-rar-compressed',
        '.7z':    'application/x-7z-compressed',
        '.tar':   'application/x-tar',
        '.gz':    'application/gzip',
        '.mp4':   'video/mp4',
        '.avi':   'video/x-msvideo',
        '.mov':   'video/quicktime',
        '.mp3':   'audio/mpeg',
        '.wav':   'audio/wav',
        '.jpg':   'image/jpeg',
        '.jpeg':  'image/jpeg',
        '.png':   'image/png',
        '.gif':   'image/gif',
        '.svg':   'image/svg+xml',
        '.webp':  'image/webp',
        '.txt':   'text/plain; charset=utf-8',
        '.csv':   'text/csv; charset=utf-8',
        '.json':  'application/json',
        '.xml':   'application/xml',
        '.html':  'text/html; charset=utf-8',
        '.py':    'text/x-python; charset=utf-8',
        '.ipynb': 'application/x-ipynb+json',
        '.r':     'text/x-r; charset=utf-8',
        '.rmd':   'text/x-rmarkdown; charset=utf-8',
        '.sql':   'application/sql',
        '.sh':    'application/x-sh',
        '.js':    'text/javascript',
        '.ts':    'text/typescript',
        '.css':   'text/css',
        '.md':    'text/markdown; charset=utf-8',
        '.yaml':  'text/yaml',
        '.yml':   'text/yaml',
        '.toml':  'text/toml',
        '.mat':   'application/octet-stream',
        '.m':     'text/x-matlab',
        '.c':     'text/x-c',
        '.cpp':   'text/x-c++',
        '.java':  'text/x-java',
        '.h':     'text/x-c',
    }
    ct = ct_map.get(ext, 'application/octet-stream')
    return ext, ct

def _cloudinary_get_bytes(file_url):
    """
    Download file bytes from Cloudinary using the authenticated API
    (generate_archive endpoint). This bypasses ACL/CDN restrictions that
    block direct URL access (X-Cld-Error: deny or ACL failure).

    Returns raw file bytes, or raises an exception.
    """
    import cloudinary.utils
    import requests as req
    import zipfile, io, re
    from urllib.parse import unquote

    # Extract resource_type and public_id from Cloudinary URL
    m = re.search(r'/(raw|image|video)/upload/(?:v\d+/)?(.+)', file_url)
    if not m:
        raise ValueError(f"Cannot parse Cloudinary URL: {file_url[:80]}")

    resource_type = m.group(1)
    public_id = unquote(m.group(2))

    # Remove extension from public_id for raw files (Cloudinary stores without ext)
    # Actually for RawMediaCloudinaryStorage it includes the extension in public_id
    # Try both with and without extension
    archive_url = cloudinary.utils.download_archive_url(
        public_ids=[public_id],
        resource_type=resource_type,
        mode='download',
    )

    r = req.get(archive_url, timeout=30, headers={'User-Agent': 'AcademIA/1.0'})
    r.raise_for_status()

    # Response is a ZIP archive containing the file
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = zf.namelist()
    if not names:
        raise ValueError("Empty archive returned from Cloudinary")

    return zf.read(names[0])



MATERIAL_CONTENT_TYPES = {
    'pdf':   'application/pdf',
    'ppt':   'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'word':  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'excel': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'zip':   'application/zip',
    'video': 'video/mp4',
}

MATERIAL_EXTENSIONS = {
    'pdf': '.pdf', 'ppt': '.pptx', 'word': '.docx',
    'excel': '.xlsx', 'zip': '.zip',
}


@login_required
def view_material(request, pk):
    """
    Inline proxy: downloads file from Cloudinary via authenticated API
    (bypasses CDN ACL restrictions) and serves with correct Content-Type.
    Extension preserved for all formats (ipynb, r, py, etc.).
    """
    from django.http import HttpResponse
    from urllib.parse import urlparse as _up, unquote as _uq
    material = get_object_or_404(SessionMaterial, pk=pk)
    if not request.user.is_member_of(material.session.course):
        return redirect('dashboard')

    file_url = material.file.url

    # For known types use existing map; for 'other' extract from Cloudinary URL
    ext_from_map = MATERIAL_EXTENSIONS.get(material.file_type, '')
    if ext_from_map:
        ext = ext_from_map
        ct  = MATERIAL_CONTENT_TYPES.get(material.file_type, 'application/octet-stream')
    else:
        ext, ct = _ext_and_ct(file_url, material.file.name)

    # Build filename
    try:
        orig_fname = _uq(_up(file_url).path.split('?')[0].split('/')[-1])
        if not orig_fname or orig_fname == ext.lstrip('.'):
            orig_fname = material.name + ext
    except Exception:
        orig_fname = material.name + ext

    if ext and not orig_fname.lower().endswith(ext):
        orig_fname += ext

    safe_name = orig_fname.replace(chr(34), chr(39))

    try:
        content = _cloudinary_get_bytes(file_url)
        response = HttpResponse(content, content_type=ct)
        response['Content-Disposition'] = f'inline; filename="{safe_name}"'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['Cache-Control'] = 'private, max-age=3600'
        return response
    except Exception as e:
        error_msg = str(e)[:120]
        raw_url = getattr(material.file, 'url', 'URL no disponible')
        html = f"""<!DOCTYPE html><html>
<body style="background:#1a1a2e;font-family:sans-serif;
             display:flex;align-items:center;justify-content:center;
             height:100vh;flex-direction:column;gap:1rem;margin:0;padding:1rem;">
  <p style="font-size:1.1rem;color:#f87171;text-align:center;max-width:500px">
    No se pudo cargar el archivo:<br><small>{error_msg}</small>
  </p>
  <a href="{raw_url}" target="_blank"
     style="color:#38bdf8;background:rgba(56,189,248,.1);
            border:1px solid rgba(56,189,248,.3);padding:.6rem 1.2rem;
            border-radius:.5rem;text-decoration:none;">
    Abrir en Cloudinary
  </a>
</body></html>"""
        return HttpResponse(html, content_type='text/html', status=200)


@login_required
def download_material(request, pk):
    """
    Forced download: uses Cloudinary authenticated API (bypasses ACL).
    Extension is always preserved — even for unknown formats (ipynb, r, py, etc.).
    Videos redirect to CDN directly (too large to proxy).
    """
    from django.http import HttpResponse
    from urllib.parse import urlparse as _up, unquote as _uq
    material = get_object_or_404(SessionMaterial, pk=pk)
    if not request.user.is_member_of(material.session.course):
        messages.error(request, 'No tienes acceso a este archivo.')
        return redirect('dashboard')

    if material.file_type in ('video', 'audio'):
        return redirect(material.file.url)

    file_url = material.file.url

    # For known types use existing map; for 'other' extract from Cloudinary URL
    ext_from_map = MATERIAL_EXTENSIONS.get(material.file_type, '')
    if ext_from_map:
        ext = ext_from_map
        ct  = MATERIAL_CONTENT_TYPES.get(material.file_type, 'application/octet-stream')
    else:
        ext, ct = _ext_and_ct(file_url, material.file.name)

    # Build filename: prefer original filename from URL, fallback to material.name + ext
    try:
        orig_fname = _uq(_up(file_url).path.split('?')[0].split('/')[-1])
        # orig_fname is e.g. "notebook.ipynb" or just "notebook"
        if not orig_fname or orig_fname == ext.lstrip('.'):
            orig_fname = material.name + ext
    except Exception:
        orig_fname = material.name + ext

    # Guarantee extension is present
    if ext and not orig_fname.lower().endswith(ext):
        orig_fname += ext

    safe_name = orig_fname.replace(chr(34), chr(39))

    try:
        content = _cloudinary_get_bytes(file_url)
        response = HttpResponse(content, content_type=ct)
        response['Content-Disposition'] = f'attachment; filename="{safe_name}"'
        return response
    except Exception as e:
        messages.error(request, f'Error al descargar: {str(e)[:100]}')
        return redirect('session_detail', pk=material.session.pk)


@login_required
def debug_material(request, pk):
    """Diagnostic: shows what Cloudinary returns for a material file URL."""
    import requests as req
    from django.http import JsonResponse
    from urllib.parse import urlparse, quote, urlunparse
    import urllib.request

    # Only allow staff/superuser
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'forbidden'}, status=403)

    material = get_object_or_404(SessionMaterial, pk=pk)
    raw_url = material.file.url
    candidates = _build_cloudinary_urls(raw_url)

    results = []
    for url in candidates:
        parsed = urlparse(url)
        safe_path = quote(parsed.path, safe='/:@!$&\'()*+,;=-.~%')
        encoded_url = urlunparse(parsed._replace(path=safe_path))

        # Try with requests
        try:
            r = req.get(encoded_url, timeout=15, allow_redirects=True,
                        headers={'User-Agent': 'Mozilla/5.0 (compatible; AcademIA)'})
            content = r.content
            results.append({
                'method': 'requests',
                'url': encoded_url,
                'status': r.status_code,
                'content_type': r.headers.get('Content-Type', ''),
                'content_length': len(content),
                'is_pdf': content[:4] == b'%PDF' if len(content) >= 4 else False,
                'first_bytes': content[:20].hex() if content else '',
                'final_url': r.url,
            })
        except Exception as e:
            results.append({'method': 'requests', 'url': encoded_url, 'error': str(e)})

        # Try with urllib
        try:
            req2 = urllib.request.Request(
                encoded_url,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; AcademIA)'}
            )
            with urllib.request.urlopen(req2, timeout=15) as resp:
                content2 = resp.read()
                results.append({
                    'method': 'urllib',
                    'url': encoded_url,
                    'status': resp.status,
                    'content_type': resp.headers.get('Content-Type', ''),
                    'content_length': len(content2),
                    'is_pdf': content2[:4] == b'%PDF' if len(content2) >= 4 else False,
                    'first_bytes': content2[:20].hex() if content2 else '',
                })
        except Exception as e:
            results.append({'method': 'urllib', 'url': encoded_url, 'error': str(e)})

    return JsonResponse({
        'material_id': pk,
        'material_name': material.name,
        'file_type': material.file_type,
        'raw_url': raw_url,
        'candidates': candidates,
        'results': results,
    }, json_dumps_params={'indent': 2})


@login_required
def material_upload_ajax(request, session_pk):
    """AJAX upload endpoint - returns JSON, supports XHR progress tracking."""
    from django.http import JsonResponse
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    session = get_object_or_404(Session, pk=session_pk)
    course = session.course
    if not request.user.can_manage(course):
        return JsonResponse({'error': 'Sin permiso'}, status=403)

    form = MaterialUploadForm(request.POST, request.FILES)
    if form.is_valid():
        try:
            material = form.save(commit=False)
            material.session = session
            material.save()
            return JsonResponse({
                'success': True,
                'pk': material.pk,
                'name': material.name,
                'file_type': material.file_type,
                'upload_date': material.uploaded_at.strftime('%d/%m/%Y'),
                'view_url':     f'/materials/{material.pk}/view/',
                'download_url': f'/materials/{material.pk}/download/',
            })
        except Exception as e:
            return JsonResponse({'error': f'Error al guardar: {str(e)[:200]}'}, status=500)
    return JsonResponse({'error': str(form.errors)}, status=400)


@login_required
def recording_add(request, session_pk):
    from .models import ClassRecording
    session = get_object_or_404(Session, pk=session_pk)
    if not request.user.can_manage(session.course):
        messages.error(request, 'Sin permiso.')
        return redirect('session_detail', pk=session_pk)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        link  = request.POST.get('link', '').strip()
        source = request.POST.get('source', 'other')
        description = request.POST.get('description', '').strip()
        if title and link:
            ClassRecording.objects.create(
                session=session, title=title, link=link,
                source=source, description=description)
            messages.success(request, 'Grabación agregada.')
        else:
            messages.error(request, 'Título y enlace son requeridos.')
    return redirect('session_detail', pk=session_pk)


@login_required
def recording_delete(request, pk):
    from .models import ClassRecording
    rec = get_object_or_404(ClassRecording, pk=pk)
    if request.user.can_manage(rec.session.course):
        session_pk = rec.session.pk
        rec.delete()
        messages.success(request, 'Grabación eliminada.')
        return redirect('session_detail', pk=session_pk)
    messages.error(request, 'Sin permiso.')
    return redirect('dashboard')


@login_required
def activity_file_view(request, pk):
    """Proxy: serve activity instruction file inline (PDF preview)."""
    from django.http import HttpResponse
    from .models import Activity
    activity = get_object_or_404(Activity, pk=pk)
    if not request.user.is_member_of(activity.session.course):
        return redirect('dashboard')
    if not activity.instruction_file:
        return HttpResponse("No hay archivo adjunto.", status=404)
    file_url = activity.instruction_file.url
    # Determine content type
    name = activity.name if hasattr(activity, 'name') else activity.title
    fname = os.path.basename(activity.instruction_file.name)
    ext = os.path.splitext(fname)[1].lower()
    ct_map = {'.pdf': 'application/pdf', '.doc': 'application/msword',
              '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
              '.ppt': 'application/vnd.ms-powerpoint',
              '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
              '.xls': 'application/vnd.ms-excel',
              '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    }
    ct = ct_map.get(ext, 'application/octet-stream')
    clean_name = activity.title + ext
    try:
        content = _cloudinary_get_bytes(file_url)
        resp = HttpResponse(content, content_type=ct)
        resp['Content-Disposition'] = f'inline; filename="{clean_name}"'
        resp['X-Frame-Options'] = 'SAMEORIGIN'
        return resp
    except Exception as e:
        return HttpResponse(f"Error al cargar: {e}", status=502)


@login_required
def activity_file_download(request, pk):
    """Proxy: download activity instruction file — preserves original extension."""
    from django.http import HttpResponse
    from urllib.parse import urlparse as _up, unquote as _uq
    activity = get_object_or_404(Activity, pk=pk)
    if not request.user.is_member_of(activity.session.course):
        return redirect('dashboard')
    if not activity.instruction_file:
        return HttpResponse("No hay archivo adjunto.", status=404)

    file_url    = activity.instruction_file.url
    ext, ct     = _ext_and_ct(file_url, activity.instruction_file.name)

    # Prefer original filename from Cloudinary URL (extension preserved there)
    try:
        raw_fname = _uq(_up(file_url).path.split('?')[0].split('/')[-1])
        if not raw_fname or raw_fname == ext.lstrip('.'):
            raw_fname = activity.title + ext
    except Exception:
        raw_fname = activity.title + ext

    # Guarantee extension is present
    if ext and not raw_fname.lower().endswith(ext):
        raw_fname += ext

    try:
        content = _cloudinary_get_bytes(file_url)
        resp = HttpResponse(content, content_type=ct)
        resp['Content-Disposition'] = f'attachment; filename="{raw_fname.replace(chr(34), chr(39))}"'
        return resp
    except Exception as e:
        return HttpResponse(f"Error al descargar: {e}", status=502)


@login_required
def course_catalog(request):
    """Browse all active courses — request enrollment for non-members."""
    from .models import EnrollmentRequest
    user = request.user
    all_courses = Course.objects.filter(is_active=True).order_by('-created_at') \
        .select_related('teacher').prefetch_related('students')

    # Map course pk → enrollment request status for this user
    user_requests = {
        er.course_id: er.status
        for er in EnrollmentRequest.objects.filter(user=user)
    }

    course_data = []
    for c in all_courses:
        is_member = user.is_member_of(c)
        req_status = user_requests.get(c.pk)
        course_data.append({
            'course': c,
            'is_member': is_member,
            'req_status': req_status,
            'student_count': c.students.count(),
        })

    return render(request, 'courses/course_catalog.html', {
        'course_data': course_data,
    })


@login_required
def request_enrollment(request, pk):
    """Create an enrollment request directly (no code required)."""
    from .models import EnrollmentRequest
    course = get_object_or_404(Course, pk=pk, is_active=True)
    user = request.user

    if user.is_member_of(course):
        messages.info(request, f'Ya eres miembro de "{course.title}".')
        return redirect('course_detail', pk=pk)

    existing = EnrollmentRequest.objects.filter(user=user, course=course).first()
    if existing:
        if existing.status == 'pending':
            messages.info(request, 'Ya tienes una solicitud pendiente.')
        elif existing.status == 'rejected':
            messages.error(request, 'Tu solicitud fue rechazada.')
        else:
            messages.info(request, 'Ya eres miembro.')
    else:
        EnrollmentRequest.objects.create(user=user, course=course)
        messages.success(request, f'Solicitud enviada para "{course.title}". El profesor la revisará pronto.')

    next_url = request.POST.get('next') or request.GET.get('next') or 'course_catalog'
    return redirect(next_url)


@login_required
def submission_file_download(request, pk):
    """Proxy: download a SubmissionFile through Django (bypasses Cloudinary 401)."""
    from django.http import HttpResponse
    from .models import SubmissionFile
    import os as _os
    sf = get_object_or_404(SubmissionFile, pk=pk)
    sub = sf.submission
    course = sub.activity.session.course

    # Permission: student who submitted OR teacher/moderator
    if request.user != sub.student and not request.user.can_manage(course):
        messages.error(request, 'Sin permiso.')
        return redirect('dashboard')

    file_url = sf.file.url
    fname = sf.original_name or _os.path.basename(str(sf.file))
    ext = _os.path.splitext(fname)[1].lower()

    ct_map = {
        '.pdf':  'application/pdf',
        '.doc':  'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.ppt':  'application/vnd.ms-powerpoint',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.xls':  'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.zip':  'application/zip',
        '.txt':  'text/plain',
        '.jpg':  'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
        '.mp4':  'video/mp4',  '.mp3':  'audio/mpeg',
    }
    ct = ct_map.get(ext, 'application/octet-stream')

    try:
        content = _cloudinary_get_bytes(file_url)
        safe_name = fname.replace('"', "'")
        resp = HttpResponse(content, content_type=ct)
        resp['Content-Disposition'] = f'attachment; filename="{safe_name}"'
        return resp
    except Exception as e:
        return HttpResponse(f'Error al descargar: {e}', status=502)


@login_required
def delete_submission_file(request, pk):
    """Remove one file from a student's submission (only before due_date)."""
    from .models import SubmissionFile
    sf = get_object_or_404(SubmissionFile, pk=pk)
    sub = sf.submission
    activity = sub.activity

    if request.user != sub.student:
        messages.error(request, 'Sin permiso.')
        return redirect('activity_detail', pk=activity.pk)

    # Block if past due_date
    if activity.due_date and timezone.now() > activity.due_date:
        messages.error(request, 'La fecha límite ha pasado. No puedes modificar tu entrega.')
        return redirect('activity_detail', pk=activity.pk)

    if request.method == 'POST':
        try:
            sf.file.delete(save=False)   # remove from Cloudinary
        except Exception:
            pass
        sf.delete()
        messages.success(request, 'Archivo eliminado de tu entrega.')

    return redirect('activity_detail', pk=activity.pk)


@login_required
def resubmit_activity(request, pk):
    """Add new files to an existing submission (only before due_date)."""
    import traceback as _tb
    from .models import SubmissionFile
    from django.db import models as _dm

    # Only accept POST
    if request.method != 'POST':
        return redirect('activity_detail', pk=pk)

    activity = get_object_or_404(Activity, pk=pk)
    # Prefetch related to avoid FK chain issues in upload_to
    activity = Activity.objects.select_related('session__course').get(pk=pk)
    user = request.user

    if user.can_manage(activity.session.course):
        messages.error(request, 'Los profesores no pueden entregar actividades.')
        return redirect('activity_detail', pk=pk)

    if activity.due_date and timezone.now() > activity.due_date:
        messages.error(request, 'La fecha límite ha pasado. No puedes reentregar.')
        return redirect('activity_detail', pk=pk)

    submission = get_object_or_404(
        Submission.objects.select_related('student', 'activity__session__course'),
        activity=activity, student=user)

    try:
        files   = request.FILES.getlist('files')
        comment = request.POST.get('comment', '').strip()

        if files:
            for f in files:
                SubmissionFile.objects.create(
                    submission=submission, file=f, original_name=f.name)
            messages.success(request, f'{len(files)} archivo(s) agregado(s) a tu entrega.')

        if comment != (submission.comment or '').strip():
            submission.comment = comment
            submission.save(update_fields=['comment'])
            if not files:
                messages.success(request, 'Comentario actualizado.')

        if not files and comment == (submission.comment or '').strip():
            messages.info(request, 'No se realizaron cambios.')

    except Exception as e:
        messages.error(request, f'Error al guardar: {e}')

    return redirect('activity_detail', pk=pk)
