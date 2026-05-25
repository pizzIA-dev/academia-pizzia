import os
from django import forms
from .models import Course, Session, SessionMaterial, Activity, Submission

# Auto-detect file type from extension
EXT_TO_TYPE = {
    '.ppt': 'ppt', '.pptx': 'ppt',
    '.xls': 'excel', '.xlsx': 'excel',
    '.doc': 'word', '.docx': 'word',
    '.pdf': 'pdf',
    '.mp4': 'video', '.mov': 'video', '.avi': 'video', '.mkv': 'video',
    '.zip': 'other', '.rar': 'other',
    '.txt': 'other', '.csv': 'other',
    '.png': 'other', '.jpg': 'other', '.jpeg': 'other',
}

def detect_file_type(filename):
    ext = os.path.splitext(filename)[1].lower()
    return EXT_TO_TYPE.get(ext, 'other')


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
        fields = ('week_number', 'title', 'description', 'date', 'video_link', 'video_file')
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'video_link': forms.URLInput(attrs={'placeholder': 'https://youtu.be/...'}),
        }


class MaterialUploadForm(forms.ModelForm):
    # No extension validation — any file allowed
    file = forms.FileField()

    class Meta:
        model = SessionMaterial
        fields = ('name', 'file_type', 'file')


class ActivityForm(forms.ModelForm):
    instruction_file = forms.FileField(required=False)

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
