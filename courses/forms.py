import os
from django import forms
from django.conf import settings
from .models import Course, Session, SessionMaterial, Activity, Submission, COVER_COLORS

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
        choices=[(c, c) for c in COVER_COLORS],
        widget=forms.RadioSelect(attrs={'class': 'color-picker'}),
        label='Color del curso',
        initial='#0ea5e9',
    )

    class Meta:
        model = Course
        fields = ('title', 'description', 'cover_color')
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Ej: Matematicas Discretas 2024'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Descripcion breve del curso...'}),
        }


class JoinCourseForm(forms.Form):
    code = forms.CharField(
        max_length=8,
        label='Codigo del curso',
        widget=forms.TextInput(attrs={
            'placeholder': 'Ej: ABC12345',
            'class': 'code-input',
            'style': 'text-transform: uppercase; letter-spacing: 4px; font-size: 1.4rem;'
        })
    )

    def clean_code(self):
        return self.cleaned_data['code'].strip().upper()


class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ('week_number', 'title', 'description', 'date', 'video_link')
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'video_link': forms.URLInput(attrs={'placeholder': 'https://youtu.be/... o https://drive.google.com/...'}),
        }


class SessionMaterialForm(forms.ModelForm):
    class Meta:
        model = SessionMaterial
        fields = ('name', 'file', 'file_type')

    def clean_file(self):
        file = self.cleaned_data.get('file')
        validate_file_extension(file)
        return file


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ('title', 'instructions', 'instruction_file', 'due_date',
                  'grade_type', 'max_grade', 'custom_grades')
        widgets = {
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'instructions': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Describe la actividad detalladamente...'}),
            'custom_grades': forms.TextInput(attrs={'placeholder': 'Ej: Excelente,Bueno,Regular,Deficiente'}),
        }

    def clean_instruction_file(self):
        file = self.cleaned_data.get('instruction_file')
        validate_file_extension(file)
        return file


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ('file', 'comment')
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Comentario opcional para el profesor...'}),
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        validate_file_extension(file)
        return file


class GradeSubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ('grade', 'teacher_comment')
        widgets = {
            'teacher_comment': forms.Textarea(attrs={'rows': 3}),
        }


class AddModeratorForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        label='Nombre de usuario del moderador',
        widget=forms.TextInput(attrs={'placeholder': 'Ingresa el username exacto'})
    )
