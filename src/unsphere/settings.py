import os
from pathlib import Path

import sentry_sdk
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load secrets/config from a project-dir .env (chmod 700, gitignored), matching
# the zingor deployment. Absent in dev, so the in-file defaults apply there.
load_dotenv(BASE_DIR / ".env")

# Mirrors the zingor Sentry setup. DSN comes from the environment; when it is
# empty (dev, or before it is configured on the server) init is a no-op.
sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN", ""),
    # Add data like request headers and IP for users.
    # See https://docs.sentry.io/platforms/python/data-management/data-collected/
    send_default_pii=True,
    enable_logs=True,
    traces_sample_rate=1.0,  # 1.0 captures 100% of transactions for tracing
    profile_session_sample_rate=0.1,  # profile ~10% of sessions to conserve profile hours
    profile_lifecycle="trace",  # "trace" automatically runs the profiler during an active transaction
)


def _env_bool(name, default):
    return os.environ.get(name, str(default)).lower() in ("1", "true", "yes", "on")


def _env_list(name, default):
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


DEBUG = _env_bool("DEBUG", True)

# In production the SECRET_KEY must come from the environment. The insecure
# fallback is only tolerated while DEBUG is on.
SECRET_KEY = os.environ.get("SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-only-insecure-key-change-before-deploy"
    else:
        raise RuntimeError(
            "SECRET_KEY must be set in the environment when DEBUG is off"
        )

ALLOWED_HOSTS = _env_list(
    "ALLOWED_HOSTS", "localhost,127.0.0.1,unsphere.maxwelljoslyn.com"
)
CSRF_TRUSTED_ORIGINS = _env_list(
    "CSRF_TRUSTED_ORIGINS", "https://unsphere.maxwelljoslyn.com"
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "unsphere.apps.UnsphereConfig",
    "users",
    "workouts",
    "achievements",
    "gems",
    "stats",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Listed after AchievementMiddleware so it sits closer to the view: on the
    # response trip it runs first, crediting gems before achievements are
    # checked — so a future gem-count achievement sees this request's gems.
    "achievements.middleware.AchievementMiddleware",
    "gems.middleware.GemMiddleware",
]

ROOT_URLCONF = "unsphere.urls"

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
                "achievements.context_processors.nav_achievements",
                "achievements.context_processors.pending_achievements",
                "gems.context_processors.nav_gems",
                "unsphere.context_processors.build_info",
            ],
        },
    },
]

WSGI_APPLICATION = "unsphere.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "unsphere.db",
    }
}

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
# collectstatic writes here; Caddy serves /static/* directly from this dir.
STATIC_ROOT = BASE_DIR / "staticfiles"
# Content-hash static filenames so a CSS/JS change yields a new URL and browsers
# (notably mobile, which caches aggressively) can never serve a stale copy.
# Only in production: the manifest backend reads staticfiles.json, which exists
# only after collectstatic, so dev runserver keeps the plain storage.
if not DEBUG:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
        },
    }
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Production hardening. These only bite when DEBUG is off; in dev they stay
# relaxed so http://localhost keeps working.
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = _env_bool("SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "2592000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/workouts/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# Email / account confirmation.
# Point these at Mailgun in production via the environment, e.g.:
#   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
#   EMAIL_HOST=smtp.mailgun.org
#   EMAIL_PORT=587
#   EMAIL_USE_TLS=true
#   EMAIL_HOST_USER=postmaster@mg.yourdomain.com
#   EMAIL_HOST_PASSWORD=<mailgun smtp password>
#   DEFAULT_FROM_EMAIL=Unsphere <no-reply@mg.yourdomain.com>
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "2525"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "false").lower() == "true"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "no-reply@unsphere.local")

# Require email confirmation before login. Off in dev (DEBUG) so local accounts
# are usable immediately; on in production.
EMAIL_CONFIRMATION_REQUIRED = (
    os.environ.get("EMAIL_CONFIRMATION_REQUIRED", "false" if DEBUG else "true").lower()
    == "true"
)

# In-app feedback: the "Feedback" form posts a GitHub issue to this repo using
# this token. The repo is "owner/name"; the token is a PAT with issue-write
# access. Issues are filed as whoever owns the token (a deploy key won't work —
# it can push git but can't call the REST API). Both empty in dev, where the
# view reports "not configured" rather than reaching out to GitHub.
GITHUB_FEEDBACK_REPO = os.environ.get("GITHUB_FEEDBACK_REPO", "")
GITHUB_FEEDBACK_TOKEN = os.environ.get("GITHUB_FEEDBACK_TOKEN", "")
