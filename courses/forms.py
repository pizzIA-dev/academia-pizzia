import os
from django import forms
from django.conf import settings
from .models import Course, Session, SessionMaterial, Activity, Submission

ALLOWED_EXTENSIONS = getattr(settings, 'ALLOWED_FILE_EXTENSIONS',
    ['.ppt', '.pptx', '.xls', '.xlsx', '.doc', '.docx', '.pdf', '.txt', '.zip'])


def validate_file_extension(file):
    if file:
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise forms.ValidationError(
                f'Tipo de archivo no permitido: {ext}. '
                f'Permitidos: {", ".join(ALLOWED_EXTENSIONS)}'
            )


class CourseForm(forms.ModelForm):
    cover_color = forms.ChoiceField(
        choices=[(c, c) for c in [
            '#0ea5e9', '#8b5cf6', '#10b981', '#f59e0b',
            '#ef4444', '#ec4899', '#06b6d4', '#84cc16'
        ]],
        widget=forms.RadioSelect(attrs={'class': 'color-picker'}),
        label='Color del curso',
        initial='#0ea5e9',
    )

    class Meta:
        model = Course
        fields = ('title', 'description', 'cover_color')
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Ej: Matematicas Discretas 2024'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Descripcion breve...'}),
        }


class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ('week_number', 'title', 'description', 'date', 'video_link', 'video_file')
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'video_link': forms.URLInput(attrs={'placeholder': 'https://youtu.be/...'}),
        }


class MaterialUploadForm(forms.ModelForm):
    file = forms.FileField(validators=[validate_file_extension])

    class Meta:
        model = SessionMaterial
        fields = ('name', 'file_type', 'file')


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ('title', 'instructions', 'instruction_file', 'due_date',
                  'grade_type', 'max_grade', 'custom_grades')
        widgets = {
            'instructions': forms.Textarea(attrs={'rows': 5}),
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class GradeForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ('grade', 'teacher_comment')
