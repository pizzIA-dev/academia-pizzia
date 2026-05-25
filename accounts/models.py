from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    bio = models.TextField(blank=True, verbose_name='Bio')

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return self.get_full_name() or self.username

    def get_taught_courses(self):
        return self.courses_taught.filter(is_active=True)

    def get_moderated_courses(self):
        return self.courses_moderated.filter(is_active=True)

    def get_enrolled_courses(self):
        return self.courses_enrolled.filter(is_active=True)

    def is_teacher_of(self, course):
        return self.pk == course.teacher_id

    def is_moderator_of(self, course):
        return self.courses_moderated.filter(pk=course.pk).exists()

    def is_student_of(self, course):
        return self.courses_enrolled.filter(pk=course.pk).exists()

    def can_manage(self, course):
        return self.is_teacher_of(course) or self.is_moderator_of(course)

    def is_member_of(self, course):
        return (self.is_teacher_of(course) or
                self.is_moderator_of(course) or
                self.is_student_of(course))

    @property
    def display_name(self):
        return self.get_full_name() or self.username
