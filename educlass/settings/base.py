from pathlib import Path
from decouple import config
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production-please-now')
DEBUG = str(config('DEBUG', default='False')).strip().lower() in ('true', '1', 'yes', 'on')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'cloudinary_storage',
    'django.contrib.staticfiles',
    'cloudinary',
    'storages',
    'accounts',
    'courses',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'educlass.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'educlass.wsgi.application'

DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default=f'sqlite:///{BASE_DIR}/db.sqlite3'),
        conn_max_age=600,
    )
}

AUTH_USER_MODEL = 'accounts.CustomUser'

AUTHENTICATION_BACKENDS = [
    'accounts.backends.EmailOrUsernameBackend',
    'django.contrib.auth.backends.ModelBackend',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-us'
TIME_ZONE = 'America/Guatemala'
USE_I18N = True
USE_TZ = True

# ─── Static Files ───
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ─── Cloudinary (Documentos, imagenes, PDFs) ───
MEDIA_URL = '/media/'
# DEFAULT_FILE_STORAGE removed — production.py uses STORAGES dict (Django 4.2+)

CLOUDINARY_STORAGE = {
    'CLOUDINARY_URL': config('CLOUDINARY_URL', default='cloudinary://placeholder:placeholder@placeholder'),
    'PREFIX': 'academIA',  # Carpeta base en Cloudinary
}

# ─── Backblaze B2 (Videos de clase - almacenamiento barato) ───
# $0.006/GB-mes, primeros 10GB gratis
# Activar: configurar variables B2_* en Railway
B2_ENABLED = config('B2_ENABLED', default=False, cast=bool)

if B2_ENABLED:
    B2_KEY_ID = config('B2_KEY_ID', default='')
    B2_APPLICATION_KEY = config('B2_APPLICATION_KEY', default='')
    B2_BUCKET_NAME = config('B2_BUCKET_NAME', default='academia-videos')
    B2_REGION = config('B2_REGION', default='us-west-004')

    # B2 S3-Compatible storage for video files
    B2_STORAGE = {
        'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
        'OPTIONS': {
            'access_key': B2_KEY_ID,
            'secret_key': B2_APPLICATION_KEY,
            'bucket_name': B2_BUCKET_NAME,
            'region_name': B2_REGION,
            'endpoint_url': f'https://s3.{B2_REGION}.backblazeb2.com',
            'location': 'academIA/videos',
            'default_acl': 'public-read',
            'querystring_auth': False,
            'object_parameters': {
                'ContentDisposition': 'inline',
            },
        }
    }
    VIDEO_STORAGE_BACKEND = 'storages.backends.s3boto3.S3Boto3Storage'
else:
    VIDEO_STORAGE_BACKEND = None  # Falls back to Cloudinary or local

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# Max upload sizes
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024   # 50MB in memory
DATA_UPLOAD_MAX_MEMORY_SIZE = 500 * 1024 * 1024  # 500MB total (for videos)

ALLOWED_FILE_EXTENSIONS = ['.ppt', '.pptx', '.xls', '.xlsx', '.doc', '.docx', '.pdf', '.txt', '.zip']
ALLOWED_VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv', '.webm']

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
