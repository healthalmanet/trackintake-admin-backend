import os
from dotenv import load_dotenv
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# .env load
load_dotenv(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-trackintake-admin-secret-key-2026-change-in-production')

DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Dynamic ALLOWED_HOSTS configuration - Strip whitespace from each host
ALLOWED_HOSTS = [
    host.strip() for host in 
    os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if host.strip()
]


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'corsheaders',
    'rest_framework',
    'rest_framework.authtoken',
    'drf_yasg',
    'users',
    'subscription',
    'dashboard',
    'meals',
    'notifications',
    'nutritionist',
]


MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
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

WSGI_APPLICATION = 'trackintake_backend.wsgi.application'


#
# ✅ DEBUG check
print("DATABASE_URL:", os.getenv("DATABASE_URL"))

# Build DATABASE_URL if not set
database_url = os.getenv('DATABASE_URL')
if not database_url:
    # Construct from individual components
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', '')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'postgres')
    
    if db_password:
        database_url = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
    else:
        database_url = f'postgresql://{db_user}@{db_host}:{db_port}/{db_name}'
    
    os.environ['DATABASE_URL'] = database_url
    print("Constructed DATABASE_URL:", database_url)

DATABASES = {
    'default': dj_database_url.config(
        conn_max_age=300,
        ssl_require=False
    )
}

# Add connection options after config
DATABASES['default']['OPTIONS'] = {
    'connect_timeout': 10,
    'options': '-c statement_timeout=30000'
}


# CORS Configuration - Dynamic via environment variables
# Properly handles whitespace and empty values
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in 
    os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:5173').split(',')
    if origin.strip()
]

# CORS Settings for production
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# CORS Expose Headers for frontend to access
CORS_EXPOSE_HEADERS = [
    'content-type',
    'x-csrftoken',
]

# Allow credentials in CORS requests
CORS_ALLOW_ALL_ORIGINS = False

# Debug logging for CORS
print("[CORS Config]")
print(f"  ALLOWED_ORIGINS: {CORS_ALLOWED_ORIGINS}")
print(f"  ALLOW_CREDENTIALS: {CORS_ALLOW_CREDENTIALS}")
print(f"  ALLOW_METHODS: {CORS_ALLOW_METHODS}")


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer'
    ],
}


STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

SWAGGER_SETTINGS = {
    'USE_SESSION_AUTH': False,
}

EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = os.getenv('EMAIL_HOST', 'sandbox.smtp.mailtrap.io')
EMAIL_PORT          = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS       = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER     = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL  = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@trackintake.com')

# ============================================================================
# SECURITY CONFIGURATION
# ============================================================================

# SSL/HTTPS Configuration
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

# Security Headers
SECURE_CONTENT_SECURITY_POLICY = {
    'default-src': ("'self'",),
    'script-src': ("'self'", "'unsafe-inline'"),
    'style-src': ("'self'", "'unsafe-inline'"),
    'img-src': ("'self'", "data:", "https:"),
    'font-src': ("'self'", "data:"),
    'connect-src': ("'self'",) + tuple(CORS_ALLOWED_ORIGINS),
}

# X-Frame-Options
X_FRAME_OPTIONS = 'DENY'

# Additional Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_SECURITY_POLICY_REPORT_ONLY = False

print("[Security Config]")
print(f"  DEBUG: {DEBUG}")
print(f"  SECURE_SSL_REDIRECT: {SECURE_SSL_REDIRECT}")
print(f"  SESSION_COOKIE_SECURE: {SESSION_COOKIE_SECURE}")
print(f"  CSRF_COOKIE_SECURE: {CSRF_COOKIE_SECURE}")

