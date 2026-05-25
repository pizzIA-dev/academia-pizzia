import random
import string
from django.db import models
from django.conf import settings


def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


COVER_COLORS = [
    '#0ea5e9', '#8b5cf6', '#10b981', '#f59e0b',
    '#ef4444', '#ec4899', '#06b6d4', '#84cc16',
]


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

    def is_teacher_or_moderator(self, user):
        return user == self.teacher or self.moderators.filter(pk=user.pk).exists()

    def is_member(self, user):
        return (user == self.teacher or
                self.students.filter(pk=user.pk).exists() or
                self.moderators.filter(pk=user.pk).exists())

    def get_member_count(self):
        return self.students.count()


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
        verbose_name='Archivo de video (MP4, max 500MB)'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Sesion'
        verbose_name_plural = 'Sesiones'
        ordering = ['week_number']

    def __str__(self):
        return f'Semana {self.week_number}: {self.title}'

    @property
    def has_video(self):
        return bool(self.video_link or self.video_file)


def material_upload_path(instance, filename):
    return f'academIA/courses/{instance.session.course.id}/sessions/{instance.session.id}/{filename}'


FILE_TYPE_CHOICES = [
    ('ppt', 'PowerPoint'),
    ('excel', 'Excel'),
    ('word', 'Word'),
    ('pdf', 'PDF'),
    ('other', 'Otro'),
]


class SessionMaterial(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='materials')
    name = models.CharField(max_length=200, verbose_name='Nombre del archivo')
    file = models.FileField(upload_to=material_upload_path, verbose_name='Archivo')
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES, default='other')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Material'
        verbose_name_plural = 'Materiales'
        ordering = ['uploaded_at']

    def __str__(self):
        return self.name

    @property
    def file_icon(self):
        icons = {'ppt': 'ppt', 'excel': 'xls', 'word': 'doc', 'pdf': 'pdf'}
        return icons.get(self.file_type, 'file')

    @property
    def extension(self):
        import os
        if self.file and hasattr(self.file, 'name'):
            return os.path.splitext(str(self.file.name))[1].lower()
        return ''


GRADE_TYPE_CHOICES = [
    ('numeric', 'Numerica'),
    ('letter', 'Letra (A-F)'),
    ('custom', 'Personalizada'),
]


def activity_upload_path(instance, filename):
    return f'academIA/courses/{instance.session.course.id}/activities/{instance.id}/{filename}'


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
        verbose_name_plural = 'Actividades'
        ordering = ['due_date']

    def __str__(self):
        return f'{self.title} - {self.session}'

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
    comment = models.TextField(blank=True, verbose_name='Comentario')
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.CharField(max_length=50, blank=True, null=True, verbose_name='Nota')
    teacher_comment = models.TextField(blank=True, verbose_name='Comentario del evaluador')
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='graded_submissions')
    graded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Entrega'
        verbose_name_plural = 'Entregas'
        unique_together = ['activity', 'student']
        ordering = ['-submitted_at']

    def __str__(self):
        return f'{self.student} - {self.activity}'

    @property
    def is_graded(self):
        return bool(self.grade)
