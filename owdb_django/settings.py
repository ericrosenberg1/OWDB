import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# =============================================================================
# Core Settings
# =============================================================================

SECRET_KEY = os.getenv('APP_SECRET_KEY', 'django-insecure-development-key-change-in-production')

# Toggle debug via APP_ENV; defaults to True unless APP_ENV=production
APP_ENV = os.getenv('APP_ENV', 'development')
DEBUG = APP_ENV != 'production'

ALLOWED_HOSTS = [
    'wrestlingdb.org',
    'www.wrestlingdb.org',
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    'web',  # Docker service hostname for internal API calls
]

# Add any extra hosts from environment
EXTRA_HOSTS = os.getenv('EXTRA_ALLOWED_HOSTS', '')
if EXTRA_HOSTS:
    ALLOWED_HOSTS.extend(EXTRA_HOSTS.split(','))

# =============================================================================
# Security Settings (Production)
# =============================================================================

# If behind a reverse proxy (Traefik, Nginx, Caddy)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# CSRF trusted origins
CSRF_TRUSTED_ORIGINS = [
    'https://wrestlingdb.org',
    'https://www.wrestlingdb.org',
]

if not DEBUG:
    # Production security settings
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# =============================================================================
# Application Definition
# =============================================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'rest_framework.authtoken',
    'django_celery_beat',
    # Local
    'owdb_django.owdbapp',
    'wrestlebot_api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Serve static files efficiently
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'owdb_django.urls'

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

WSGI_APPLICATION = 'owdb_django.wsgi.application'

# =============================================================================
# Database Configuration (PostgreSQL only)
# =============================================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'owdb'),
        'USER': os.getenv('DB_USER', 'owdb'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'CONN_MAX_AGE': 60,  # Connection pooling
        'OPTIONS': {
            'connect_timeout': 10,
        },
    }
}

# =============================================================================
# Cache Configuration (Redis)
# =============================================================================

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
        'KEY_PREFIX': 'owdb',
    }
}

# Use Redis for sessions
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# =============================================================================
# Celery Configuration
# =============================================================================

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes

# Celery Beat schedule - 2X FREQUENCY for faster database building
CELERY_BEAT_SCHEDULE = {
    'reset-daily-api-limits': {
        'task': 'owdb_django.owdbapp.tasks.reset_daily_api_limits',
        'schedule': 86400.0,  # Every 24 hours
    },
    'warm-stats-cache': {
        'task': 'owdb_django.owdbapp.tasks.warm_stats_cache',
        'schedule': 300.0,  # Every 5 minutes for real-time stats
    },
    'cleanup-inactive-api-keys': {
        'task': 'owdb_django.owdbapp.tasks.cleanup_inactive_api_keys',
        'schedule': 604800.0,  # Every 7 days
    },
    # ==========================================================================
    # Web Scraping tasks - 2X FREQUENCY (doubled for faster database building)
    # ==========================================================================
    'scrape-wikipedia-wrestlers': {
        'task': 'owdb_django.owdbapp.tasks.scrape_wikipedia_wrestlers',
        'schedule': 60.0,  # Every minute for continuous training
        'args': (20,),  # Smaller batches to keep runs short
    },
    'scrape-wikipedia-promotions': {
        'task': 'owdb_django.owdbapp.tasks.scrape_wikipedia_promotions',
        'schedule': 300.0,  # Every 5 minutes
        'args': (15,),
    },
    'scrape-wikipedia-events': {
        'task': 'owdb_django.owdbapp.tasks.scrape_wikipedia_events',
        'schedule': 60.0,  # Every minute alongside wrestlers
        'args': (20,),
    },
    'scrape-cagematch-wrestlers': {
        'task': 'owdb_django.owdbapp.tasks.scrape_cagematch_wrestlers',
        'schedule': 1200.0,  # Every 20 minutes (respect site limits)
        'args': (12,),
    },
    'scrape-cagematch-events': {
        'task': 'owdb_django.owdbapp.tasks.scrape_cagematch_events',
        'schedule': 1200.0,  # Every 20 minutes
        'args': (12,),
    },
    'scrape-profightdb-wrestlers': {
        'task': 'owdb_django.owdbapp.tasks.scrape_profightdb_wrestlers',
        'schedule': 1200.0,  # Every 20 minutes
        'args': (15,),
    },
    'scrape-profightdb-events': {
        'task': 'owdb_django.owdbapp.tasks.scrape_profightdb_events',
        'schedule': 1200.0,  # Every 20 minutes
        'args': (15,),
    },
    'get-scraper-stats': {
        'task': 'owdb_django.owdbapp.tasks.get_scraper_stats',
        'schedule': 3600.0,  # Every hour
    },
    # ==========================================================================
    # API tasks - movies, games, books, podcasts
    # ==========================================================================
    'fetch-tmdb-specials': {
        'task': 'owdb_django.owdbapp.tasks.fetch_tmdb_specials',
        'schedule': 21600.0,  # Every 6 hours (was 12)
        'args': (30,),
    },
    'fetch-rawg-videogames': {
        'task': 'owdb_django.owdbapp.tasks.fetch_rawg_videogames',
        'schedule': 86400.0,  # Every 24 hours (limited monthly quota)
        'args': (30,),
    },
    'fetch-openlibrary-books': {
        'task': 'owdb_django.owdbapp.tasks.fetch_openlibrary_books',
        'schedule': 21600.0,  # Every 6 hours (was 12)
        'args': (30,),
    },
    'fetch-googlebooks-books': {
        'task': 'owdb_django.owdbapp.tasks.fetch_googlebooks_books',
        'schedule': 86400.0,  # Every 24 hours (daily quota)
        'args': (20,),
    },
    'fetch-itunes-podcasts': {
        'task': 'owdb_django.owdbapp.tasks.fetch_itunes_podcasts',
        'schedule': 21600.0,  # Every 6 hours (was 12)
        'args': (30,),
    },
    'fetch-podcastindex-podcasts': {
        'task': 'owdb_django.owdbapp.tasks.fetch_podcastindex_podcasts',
        'schedule': 21600.0,  # Every 6 hours (was 12)
        'args': (30,),
    },
    # ==========================================================================
    # WrestleBot AI tasks - 4X FREQUENCY for faster database building
    # ==========================================================================
    'wrestlebot-discovery-cycle': {
        'task': 'owdb_django.owdbapp.tasks.wrestlebot_discovery_cycle',
        'schedule': 60.0,  # Every minute for continuous improvement
        'args': (10,),  # Tighter batches to finish quickly
    },
    'wrestlebot-cleanup-logs': {
        'task': 'owdb_django.owdbapp.tasks.wrestlebot_cleanup_old_logs',
        'schedule': 604800.0,  # Every 7 days
    },
    'wrestlebot-reset-limits': {
        'task': 'owdb_django.owdbapp.tasks.wrestlebot_reset_daily_limits',
        'schedule': 86400.0,  # Every 24 hours
    },
    'wrestlebot-get-stats': {
        'task': 'owdb_django.owdbapp.tasks.wrestlebot_get_stats',
        'schedule': 600.0,  # Every 10 minutes for fresher dashboards
    },
    'wrestlebot-health-check': {
        'task': 'owdb_django.owdbapp.tasks.wrestlebot_health_check',
        'schedule': 120.0,  # Every 2 minutes to catch freezes fast
    },
    'wrestlebot-restart-stale': {
        'task': 'owdb_django.owdbapp.tasks.restart_stale_bot_tasks',
        'schedule': 300.0,  # Every 5 minutes
    },
    # ==========================================================================
    # Image Fetch Tasks (Wikimedia Commons CC Images)
    # ==========================================================================
    'fetch-wrestler-images': {
        'task': 'owdb_django.owdbapp.tasks.fetch_wrestler_images',
        'schedule': 21600.0,  # Every 6 hours
        'args': (20,),  # 20 wrestlers per batch
    },
    'fetch-promotion-images': {
        'task': 'owdb_django.owdbapp.tasks.fetch_promotion_images',
        'schedule': 43200.0,  # Every 12 hours
        'args': (10,),
    },
    'fetch-venue-images': {
        'task': 'owdb_django.owdbapp.tasks.fetch_venue_images',
        'schedule': 43200.0,  # Every 12 hours
        'args': (10,),
    },
    'fetch-title-images': {
        'task': 'owdb_django.owdbapp.tasks.fetch_title_images',
        'schedule': 43200.0,  # Every 12 hours
        'args': (10,),
    },
    'fetch-event-images': {
        'task': 'owdb_django.owdbapp.tasks.fetch_event_images',
        'schedule': 43200.0,  # Every 12 hours
        'args': (15,),
    },
}

# =============================================================================
# Scraper & API Configuration
# =============================================================================

SCRAPER_CONFIG = {
    # Global settings
    'enabled': os.getenv('SCRAPER_ENABLED', 'true').lower() == 'true',
    'user_agent': 'OWDBBot/1.0 (+https://wrestlingdb.org/about/bot)',

    # Wikipedia settings
    'wikipedia': {
        'enabled': True,
        'requests_per_minute': 30,
        'requests_per_hour': 500,
        'requests_per_day': 5000,
    },

    # Cagematch settings (more conservative - fan-run site)
    'cagematch': {
        'enabled': True,
        'requests_per_minute': 5,
        'requests_per_hour': 60,
        'requests_per_day': 500,
    },

    # ProFightDB settings
    'profightdb': {
        'enabled': True,
        'requests_per_minute': 5,
        'requests_per_hour': 60,
        'requests_per_day': 500,
    },
}

# API Keys (set via environment variables)
TMDB_API_KEY = os.getenv('TMDB_API_KEY')
RAWG_API_KEY = os.getenv('RAWG_API_KEY')
IGDB_CLIENT_ID = os.getenv('IGDB_CLIENT_ID')
IGDB_CLIENT_SECRET = os.getenv('IGDB_CLIENT_SECRET')
GOOGLE_BOOKS_API_KEY = os.getenv('GOOGLE_BOOKS_API_KEY')
PODCAST_INDEX_API_KEY = os.getenv('PODCAST_INDEX_API_KEY')
PODCAST_INDEX_API_SECRET = os.getenv('PODCAST_INDEX_API_SECRET')
LISTEN_NOTES_API_KEY = os.getenv('LISTEN_NOTES_API_KEY')

# =============================================================================
# WrestleBot AI Configuration
# =============================================================================

# Ollama settings (self-hosted AI)
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
WRESTLEBOT_AI_MODEL = os.getenv('WRESTLEBOT_AI_MODEL', 'llama3.2')

# WrestleBot is enabled by default but can be disabled via env var
WRESTLEBOT_ENABLED = os.getenv('WRESTLEBOT_ENABLED', 'true').lower() == 'true'

# =============================================================================
# Password Validation
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# =============================================================================
# Internationalization
# =============================================================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# =============================================================================
# Static Files
# =============================================================================

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'static_collected'

# Use WhiteNoise for serving static files efficiently
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# =============================================================================
# Default Field Type
# =============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =============================================================================
# Authentication
# =============================================================================

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'index'
LOGOUT_REDIRECT_URL = 'index'

# =============================================================================
# Email Configuration
# =============================================================================

# Email backend - use SMTP for production
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'true').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'OWDB <noreply@wrestlingdb.org>')

# Email verification settings
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS = 24

# =============================================================================
# Error Notifications (500 errors sent to admins)
# =============================================================================

# Admins receive email notifications for 500 errors
ADMINS = [
    ('Eric', 'e@ericgroup.us'),
]

# Server email (From address for error emails)
SERVER_EMAIL = os.getenv('SERVER_EMAIL', 'errors@wrestlingdb.org')

# =============================================================================
# Logging
# =============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'django.request': {
            'handlers': ['mail_admins', 'console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}


# =============================================================================
# Django REST Framework Settings
# =============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '10000/hour',  # High limit for WrestleBot
    },
}

# WrestleBot API Token (set via environment variable)
WRESTLEBOT_API_TOKEN = os.getenv('WRESTLEBOT_API_TOKEN', '')
