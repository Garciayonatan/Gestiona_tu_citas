from pathlib import Path
from decouple import config, Csv

# BASE DIR
BASE_DIR = Path(__file__).resolve().parent.parent

# SEGURIDAD
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

# APLICACIONES INSTALADAS
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'citas',  # Tu app personalizada
]

# MIDDLEWARE
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# URLS
ROOT_URLCONF = 'gestiona_tu_cita.urls'

# TEMPLATES
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

# WSGI
WSGI_APPLICATION = 'gestiona_tu_cita.wsgi.application'

# BASE DE DATOS - PostgreSQL AlwaysData
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
    }
}

# VALIDADORES DE CONTRASEÑA
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# INTERNACIONALIZACIÓN
LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'America/Santo_Domingo'
USE_I18N = True
USE_TZ = True

# ARCHIVOS ESTÁTICOS
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ARCHIVOS DE MEDIA
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# EMAIL CONFIGURATION
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL')

# SEGURIDAD
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', cast=Csv())
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', cast=bool)
SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', cast=bool)
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', cast=bool)
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', cast=bool)

# Vista personalizada para errores CSRF
CSRF_FAILURE_VIEW = 'citas.views.csrf_failure'

# TELEGRAM (opcional)
TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN', default=None)
TELEGRAM_CHAT_ID = config('TELEGRAM_CHAT_ID', default=None)

# LOGIN Y LOGOUT
LOGIN_REDIRECT_URL = '/home/'
LOGIN_URL = '/accounts/login/'
LOGOUT_REDIRECT_URL = '/'
