from pathlib import Path
from decouple import config, Csv

# ===============================
# 📂 Base Directory
# ===============================
BASE_DIR = Path(__file__).resolve().parent.parent

# ===============================
# 🔑 Seguridad
# ===============================
SECRET_KEY = config("SECRET_KEY", default="django-insecure-placeholder-key")
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="127.0.0.1,localhost,gestiona-tu-citas.onrender.com",
    cast=Csv()
)

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost,http://127.0.0.1,https://gestiona-tu-citas.onrender.com",
    cast=Csv()
)

# ===============================
# 📦 Aplicaciones instaladas
# ===============================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "citas",
]

# ===============================
# ⚙️ Middleware
# ===============================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ===============================
# 🌐 URLs y WSGI
# ===============================
ROOT_URLCONF = "gestiona_tu_cita.urls"
WSGI_APPLICATION = "gestiona_tu_cita.wsgi.application"

# ===============================
# 🎨 Templates
# ===============================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ===============================
# 🗄️ Base de Datos - PostgreSQL con SSL (Render)
# ===============================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME").strip(),
        "USER": config("DB_USER").strip(),
        "PASSWORD": config("DB_PASSWORD").strip(),
        "HOST": config("DB_HOST").strip(),
        "PORT": config("DB_PORT", default="5432").strip(),
        "OPTIONS": {
            "sslmode": config("DB_SSLMODE", default="require").strip()
        },
    }
}

# ===============================
# 🔐 Validadores de contraseña
# ===============================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ===============================
# 🌍 Internacionalización
# ===============================
LANGUAGE_CODE = "es-es"
TIME_ZONE = "America/Santo_Domingo"
USE_I18N = True
USE_L10N = True
USE_TZ = True

# ===============================
# 📂 Archivos estáticos
# ===============================
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ===============================
# 📧 Configuración de Email (Gmail)
# ===============================
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default=EMAIL_HOST_USER)

# ===============================
# 🔒 Seguridad para Render
# ===============================
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=3600, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True, cast=bool)
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=True, cast=bool)
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=False, cast=bool)
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=False, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=False, cast=bool)

# ===============================
# 🔑 Login y Logout
# ===============================
LOGIN_REDIRECT_URL = "/home/"
LOGIN_URL = "/accounts/login/"
LOGOUT_REDIRECT_URL = "/"

# ===============================
# 🤖 Telegram Bot
# ===============================
TELEGRAM_BOT_TOKEN = config("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_CHAT_ID = config("TELEGRAM_CHAT_ID", default="")

# ===============================
# Opciones adicionales para Render
# ===============================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
