import random
import string
from django.db import models
from django.conf import settings
from django.utils import timezone


def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


class Course(models.Model):
    title = models.CharField(max_length=200, verbose_name='Titulo')
    description = models.TextField(blank=True, verbose_name='Descripcion')
    code = models.CharField(max_length=8, unique=True, default=generate_code, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='courses_taught', verbose_name='Profesor')
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True,
        related_name='courses_enrolled', verbose_name='Estudiantes')
    moderators = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True,
        related_name='courses_moderated', verbose_name='Moderadores')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    cover_color = models.CharField(max_length=7, default='#0ea5e9')

    class Meta:
        verbose_name = 'Curso'
        verbose_name_plural = 'Cursos'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_pending_requests_count(self):
        return self.enrollment_requests.filter(status='pending').count()


class EnrollmentRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='enrollment_requests')
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE,
        related_name='enrollment_requests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(blank=True, verbose_name='Mensaje (opcional)')
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reviewed_enrollments')
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Solicitud de inscripcion'
        verbose_name_plural = 'Solicitudes de inscripcion'
        unique_together = ['user', 'course']
        ordering = ['-requested_at']

    def __str__(self):
        return f'{self.user} → {self.course} ({self.status})'

    def approve(self, reviewed_by):
        self.status = 'approved'
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.save()
        self.course.students.add(self.user)

    def reject(self, reviewed_by):
        self.status = 'rejected'
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.save()
        self.course.students.remove(self.user)


def session_video_upload_path(instance, filename):
    return f'academIA/courses/{instance.course_id}/sessions/videos/{filename}'


class Session(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sessions')
    week_number = models.PositiveIntegerField(verbose_name='Semana')
    title = models.CharField(max_length=200, verbose_name='Titulo')
    description = models.TextField(blank=True, verbose_name='Descripcion')
    date = models.DateField(verbose_name='Fecha de la sesion')
    video_link = models.URLField(blank=True, verbose_name='Enlace de grabacion (YouTube/Drive)')
    video_file = models.FileField(
        upload_to=session_video_upload_path,
        blank=True, null=True,
        verbose_name='Archivo de video (MP4, max 500MB)')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Sesion'
        verbose_name_plural = 'Sesiones'
        ordering = ['week_number']

    def __str__(self):
        return f'Semana {self.week_number}: {self.title}'


def material_upload_path(instance, filename):
    return f'academIA/courses/{instance.session.course.id}/sessions/{instance.session.id}/{filename}'


FILE_TYPE_CHOICES = [
    ('ppt', 'PowerPoint'), ('excel', 'Excel'),
    ('word', 'Word'), ('pdf', 'PDF'), ('other', 'Otro'),
]


class SessionMaterial(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='materials')
    name = models.CharField(max_length=200, verbose_name='Nombre del archivo')
    file = models.FileField(upload_to=material_upload_path, verbose_name='Archivo')
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES, default='other')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Material'
        ordering = ['uploaded_at']

    def __str__(self):
        return self.name


GRADE_TYPE_CHOICES = [
    ('numeric', 'Numerica'), ('letter', 'Letra (A-F)'), ('custom', 'Personalizada'),
]


class Activity(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='activities')
    title = models.CharField(max_length=200, verbose_name='Titulo')
    instructions = models.TextField(verbose_name='Instrucciones')
    instruction_file = models.FileField(
        upload_to='academIA/activities/instructions/', blank=True, null=True,
        verbose_name='Archivo de instrucciones (opcional)')
    due_date = models.DateTimeField(verbose_name='Fecha limite')
    grade_type = models.CharField(max_length=10, choices=GRADE_TYPE_CHOICES, default='numeric')
    max_grade = models.FloatField(default=100, verbose_name='Nota maxima')
    custom_grades = models.CharField(
        max_length=200, blank=True,
        help_text='Valores separados por coma (ej: Excelente,Bueno,Regular,Deficiente)')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Actividad'
        ordering = ['due_date']

    def __str__(self):
        return self.title

    @property
    def course(self):
        return self.session.course

    def get_grade_options(self):
        if self.grade_type == 'letter':
            return ['A', 'B', 'C', 'D', 'F']
        elif self.grade_type == 'custom' and self.custom_grades:
            return [g.strip() for g in self.custom_grades.split(',')]
        return None

    def submission_count(self):
        return self.submissions.count()


def submission_upload_path(instance, filename):
    return f'academIA/submissions/{instance.activity.session.course.id}/{instance.activity.id}/{instance.student.id}/{filename}'


class Submission(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='submissions')
    file = models.FileField(upload_to=submission_upload_path, verbose_name='Archivo de entrega')
    comment = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.CharField(max_length=50, blank=True, null=True)
    teacher_comment = models.TextField(blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='graded_submissions')
    graded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['activity', 'student']
        ordering = ['-submitted_at']

    def __str__(self):
        return f'{self.student} - {self.activity}'

    @property
    def is_graded(self):
        return bool(self.grade)


class ClassRecording(models.Model):
    SOURCE_CHOICES = [
        ('drive',   'Google Drive'),
        ('youtube', 'YouTube'),
        ('zoom',    'Zoom'),
        ('meet',    'Google Meet'),
        ('other',   'Otro enlace'),
    ]
    session     = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='recordings')
    title       = models.CharField(max_length=200)
    link        = models.URLField(max_length=500)
    source      = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='other')
    description = models.CharField(max_length=300, blank=True)
    added_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.title} ({self.session})"

    @property
    def embed_url(self):
        import re
        yt = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)', self.link)
        if yt:
            return f"https://www.youtube.com/embed/{yt.group(1)}"
        return None

    @property
    def is_youtube(self):
        return 'youtube.com' in self.link or 'youtu.be' in self.link

    @property
    def source_icon(self):
        return {'drive':'📁','youtube':'▶️','zoom':'💻','meet':'📹','other':'🔗'}.get(self.source, '🔗')

    @property
    def source_color(self):
        return {'drive':'#4285F4','youtube':'#FF0000','zoom':'#2D8CFF','meet':'#00897B','other':'#6366f1'}.get(self.source, '#6366f1')
