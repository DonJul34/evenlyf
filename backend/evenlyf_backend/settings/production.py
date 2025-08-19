"""
Paramètres de production pour evenlyf_backend.
Configuration sécurisée pour l'environnement de production.
"""

from .base import *
from decouple import config

# =============================================================================
# PRODUCTION SETTINGS
# =============================================================================

# Debug et sécurité
DEBUG = False
ALLOWED_HOSTS = [
    'evenlyf.com', 
    'www.evenlyf.com', 
    '127.0.0.1', 
    'localhost',
    config('PRODUCTION_HOST', default=''),
]

# CORS pour la production
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    config('FRONTEND_URL', default='https://evenlyf.com'),
    'https://evenlyf.com',
    'https://www.evenlyf.com',
]

# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# HTTPS settings
USE_TLS = config('USE_TLS', default=True, cast=bool)
if USE_TLS:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# =============================================================================
# EMAIL CONFIGURATION - AZURE
# =============================================================================

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# Configuration Azure App pour l'envoi d'emails
EMAIL_HOST = 'smtp-mail.outlook.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('AZURE_EMAIL_HOST_USER', default='support@evenlyf.com')
EMAIL_HOST_PASSWORD = config('AZURE_EMAIL_HOST_PASSWORD', default='')

# Configuration Azure AD pour l'authentification SMTP
AZURE_TENANT_ID = config('AZURE_TENANT_ID', default='')
AZURE_CLIENT_ID = config('AZURE_CLIENT_ID', default='')
AZURE_CLIENT_SECRET = config('AZURE_CLIENT_SECRET', default='')

# =============================================================================
# LOGGING CONFIGURATION - SIMPLE POUR PRODUCTION
# =============================================================================

# Configuration de logging simple qui fonctionne
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# =============================================================================
# SESSION ET CSRF CONFIGURATION
# =============================================================================

# Session configuration
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'

# CSRF configuration
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_TRUSTED_ORIGINS = [
    'https://evenlyf.com',
    'https://www.evenlyf.com',
]

# =============================================================================
# CACHE CONFIGURATION (optionnel pour Redis)
# =============================================================================

# Cache avec Redis si disponible
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
        }
    }

# =============================================================================
# STATICFILES CONFIGURATION
# =============================================================================

# Collecte des fichiers statiques pour la production
STATIC_ROOT = '/opt/evenlyf/backend/staticfiles'
MEDIA_ROOT = '/opt/evenlyf/backend/media' 