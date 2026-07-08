"""
Django settings for the LaaCLab (pitch-clara) project.

Reads configuration from environment variables (optionally a local .env file),
so the same settings work in development and behind nginx in production.
"""

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load variables from a local .env file if present (development convenience).
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


# --- Core -------------------------------------------------------------------

# DEBUG defaults to True so a fresh clone runs with `runserver` and no .env.
# Production MUST set DJANGO_DEBUG=0 (see .env.example / README).
DEBUG = env_bool("DJANGO_DEBUG", True)

# An insecure hardcoded key is tolerated only in DEBUG (developer convenience).
# With DEBUG off, a real DJANGO_SECRET_KEY is required or startup fails loudly —
# this prevents shipping the publicly-known key to production (cookie/token forgery).
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-dev-only-do-not-use-in-production"
    else:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is off."
        )

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")


# --- Applications -----------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "rest_framework",
    "django_filters",
    # Local
    "core",
    "catalog",
    "community",
    "alerts",
    "accounts",
    "bugs",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise serves static files in production right after security.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # allauth requires its account middleware.
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.modules",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# --- Database ---------------------------------------------------------------
# Configured from DATABASE_URL (dj-database-url). Docker/production point it at
# MySQL; with no DATABASE_URL a local SQLite file is used, so `runserver` works
# out of the box without a database server.

DATABASES = {
    "default": dj_database_url.config(
        env="DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=int(os.getenv("DJANGO_CONN_MAX_AGE", "600")),
    )
}

# MySQL: use full unicode (utf8mb4) and strict mode.
if DATABASES["default"]["ENGINE"] == "django.db.backends.mysql":
    DATABASES["default"].setdefault("OPTIONS", {}).update(
        {"charset": "utf8mb4", "init_command": "SET sql_mode='STRICT_TRANS_TABLES'"}
    )


# --- Authentication (django-allauth) ----------------------------------------

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

SITE_ID = 1

# Modern allauth (>=65) configuration.
ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = os.getenv("ACCOUNT_EMAIL_VERIFICATION", "none")
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGIN_ON_SIGNUP = True

LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "account_login"

# In development, print emails to the console instead of sending them.
EMAIL_BACKEND = os.getenv(
    "DJANGO_EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)


# --- REST API (Django REST Framework) ---------------------------------------
# Session auth (the same login the screens use) drives the browsable API and
# CSRF-protected writes. Everything requires authentication by default.

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}


# --- Celery -------------------------------------------------------------------
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", False)
CELERY_TASK_EAGER_PROPAGATES = True


# Bug classifier backend: "embedding" (fastembed, prod) | "fake" (tests).
BUGS_CLASSIFIER = os.getenv("BUGS_CLASSIFIER", "embedding")


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --- Internationalization ---------------------------------------------------

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True


# --- Static & media files ---------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Compressed, cache-busted static files served by WhiteNoise in production.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --- Security (tightened automatically when DEBUG is off) -------------------

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "3600"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # nginx terminates TLS and forwards this header.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
