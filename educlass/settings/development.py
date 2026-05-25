from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

# In development, videos go to local media folder too
