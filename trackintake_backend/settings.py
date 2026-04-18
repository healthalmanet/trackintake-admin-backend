import os
from dotenv import load_dotenv
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# .env load
<<<<<<< HEAD
load_dotenv(os.path.join(BASE_DIR, '.env'))
=======
load_dotenv(BASE_DIR / ".env")
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c

SECRET_KEY = 'django-insecure-trackintake-admin-secret-key-2026'

DEBUG = True

ALLOWED_HOSTS = ['*']


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'corsheaders',
    'rest_framework',
    'drf_yasg',
    'users',
    'subscription',
    'dashboard',
<<<<<<< HEAD
    'meals',
    'notifications',
    'nutritionist',
=======
    'meals'
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
<<<<<<< HEAD
=======
    'corsheaders.middleware.CorsMiddleware',
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'trackintake_backend.urls'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

<<<<<<< HEAD
WSGI_APPLICATION = 'trackintake_backend.wsgi.application'


#
# ✅ DEBUG check
print("DATABASE_URL:", os.getenv("DATABASE_URL"))

DATABASES = {
    'default': dj_database_url.config(
        conn_max_age=600,
        ssl_require=True
    )
=======

WSGI_APPLICATION = 'trackintake_backend.wsgi.application'


# ✅ DATABASE from .env (DATABASE_URL)
DATABASES = {
    'default': dj_database_url.parse(os.getenv("DATABASE_URL"),conn_max_age=600,ssl_require=True)
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
}


# CORS
CORS_ALLOW_ALL_ORIGINS = True


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer'
    ],
}


STATIC_URL = '/static/'

<<<<<<< HEAD
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}
=======
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
>>>>>>> 5dca6abf9aa9b4bf10ebf4485cddfab65a7d841c
