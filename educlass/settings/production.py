from .base import *
import dj_database_url
from decouple import config

DEBUG = False

SECRET_KEY = config('SECRET_KEY')

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*').split(',')

# ── Database (Railway PostgreSQL via DATABASE_URL) ────────────
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True,
    )
}

# ── Static files (WhiteNoise) ─────────────────────────────────
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ── Cloudinary (all media) ────────────────────────────────────
CLOUDINARY_URL = config('CLOUDINARY_URL')

# ── Backblaze B2 for videos (optional) ───────────────────────
B2_ENABLED = config('B2_ENABLED', default=False, cast=bool)
if B2_ENABLED:
    AWS_ACCESS_KEY_ID = config('B2_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('B2_APPLICATION_KEY')
    AWS_STORAGE_BUCKET_NAME = config('B2_BUCKET_NAME')
    AWS_S3_REGION_NAME = config('B2_REGION', default='us-west-004')
    AWS_S3_ENDPOINT_URL = f'https://s3.{AWS_S3_REGION_NAME}.backblazeb2.com'
    STORAGES['default'] = {
        'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
        'OPTIONS': {
            'bucket_name': AWS_STORAGE_BUCKET_NAME,
            'region_name': AWS_S3_REGION_NAME,
            'endpoint_url': AWS_S3_ENDPOINT_URL,
        }
    }

# ── Security ──────────────────────────────────────────────────
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = False  # Railway handles SSL
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# ── Logging ───────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}
