from pathlib import Path
import os
from dotenv import load_dotenv # CEO FIX: Load environment variables securely

BASE_DIR = Path(__file__).resolve().parent.parent

# CEO FIX: Explicitly tell load_dotenv where the .env file lives!
# This prevents PythonAnywhere WSGI from failing to find your secrets.
env_path = BASE_DIR / '.env'
load_dotenv(dotenv_path=env_path) 

# CEO FIX: Secret key now pulled from environment, NOT hardcoded!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-fallback-key')

# CEO FIX: Set to 'False' in your PythonAnywhere .env file!
DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'spotaplug.pythonanywhere.com', 'spotaplug.com', 'www.spotaplug.com']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'plugs',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'plugs.middleware.VaultDoorMiddleware', # CEO FIX: The Vault Door (Admin IP Blocker & .env Protector)
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
     # CEO FIX: The Email Verification Bouncer
    'plugs.middleware.VerifyEmailMiddleware',
]

ROOT_URLCONF = 'core.urls'

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

WSGI_APPLICATION = 'core.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos' # CEO FIX: Set to your local timezone
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# CEO FIX: Paystack Keys from .env
PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY')
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')

# CEO FIX: ENTERPRISE EMAIL (RESEND) - ACTUALLY SENDS!
ANYMAIL = {
    "RESEND_API_KEY": os.getenv('RESEND_API_KEY'), # We will add this to .env
}
EMAIL_BACKEND = "anymail.backends.resend.EmailBackend"
# CEO FIX: Resend requires an email on your verified domain! Not @gmail.com!
EMAIL_HOST_USER = os.getenv('DEFAULT_FROM_EMAIL', 'no-reply@spotaplug.com') 
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# ==========================================
# CEO FIX: SEARCH DDOS SHIELD (Caching)
# ==========================================
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'spotaplug-cache',
    }
}

# ==========================================
# CEO FIX: ADMIN VAULT DOOR (IP Whitelist)
# ==========================================
# Add your home/office IP to your .env file so you can access /admin/ in production
ALLOWED_ADMIN_IPS = os.getenv('ALLOWED_ADMIN_IPS', '127.0.0.1').split(',')

# ==========================================
# 5-STAR SECURITY SETTINGS (PRODUCTION READY)
# ==========================================
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000  # 1 year strict transport security
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True