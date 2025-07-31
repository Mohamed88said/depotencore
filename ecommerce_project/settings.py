from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'rue^n8=efh-(8nytxd&ew05b(9ti^5_mk+t221m*_(auu5ev6e'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'store.apps.StoreConfig',
    'accounts.apps.AccountsConfig',
    'marketing.apps.MarketingConfig',
    'captcha',
    'channels',
    'blog',
    'dashboard',
    'admin_panel',
    'returns.apps.ReturnsConfig',
    'chat.apps.ChatConfig',
    'delivery',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'ecommerce_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'store.context_processors.categories',
            ],
        },
    },
]

WSGI_APPLICATION = 'ecommerce_project.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# Configuration WhiteNoise pour ajouter charset=utf-8 aux fichiers JavaScript
WHITENOISE_MIMETYPES = {
    '.js': 'text/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.woff2': 'font/woff2',
    '.woff': 'font/woff',
    '.ttf': 'font/ttf',
    '.eot': 'application/vnd.ms-fontobject',
}

# Configuration des en-têtes de cache
WHITENOISE_MAX_AGE = 31536000  # 1 an pour les fichiers statiques

# Configuration de sécurité pour les cookies
# Configuration de sécurité
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Configuration CSP pour remplacer X-Frame-Options
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "https://js.stripe.com", "https://www.paypal.com", "https://cdn.jsdelivr.net", "https://unpkg.com", "https://cdnjs.cloudflare.com")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://cdn.jsdelivr.net", "https://unpkg.com", "https://cdnjs.cloudflare.com")
CSP_FONT_SRC = ("'self'", "https://fonts.gstatic.com", "https://cdnjs.cloudflare.com")
CSP_IMG_SRC = ("'self'", "data:", "https:", "http:")
CSP_CONNECT_SRC = ("'self'", "https://api.stripe.com", "https://www.paypal.com", "wss:", "ws:")
CSP_FRAME_ANCESTORS = ("'self'",)

# Configuration WhiteNoise
WHITENOISE_MIMETYPES = {
    '.js': 'text/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.woff2': 'font/woff2',
    '.woff': 'font/woff',
    '.ttf': 'font/ttf',
    '.eot': 'application/vnd.ms-fontobject',
}

WHITENOISE_MAX_AGE = 31536000  # 1 an

# Configuration des cookies sécurisés
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True
    SESSION_COOKIE_HTTPONLY = True

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.CustomUser'

SITE_ID = 1
SITE_URL = 'http://127.0.0.1:8000'
ADMIN_EMAILS = ['mohamedsaiddiallo88@gmail.com']

ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_LOGIN_METHODS = {'email', 'username'}
ACCOUNT_EMAIL_AUTHENTICATION = True

ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*', 'user_type*', 'captcha*']
ACCOUNT_LOWERCASE_EMAIL = True

LOGIN_REDIRECT_URL = '/accounts/profile/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/accounts/profile/'
ACCOUNT_SIGNUP_REDIRECT_URL = '/accounts/profile/'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'mohamedsaiddiallo88@gmail.com'
EMAIL_HOST_PASSWORD = 'gmqylnuvrqgmqmsl'
DEFAULT_FROM_EMAIL = 'mohamedsaiddiallo88@gmail.com'

ACCOUNT_FORMS = {
    'signup': 'accounts.forms.SignUpForm',
    'login': 'accounts.forms.LoginForm',
}
ACCOUNT_ADAPTER = 'accounts.adapters.CustomAccountAdapter'


PRODUCTS_PER_PAGE = 9

RECAPTCHA_PUBLIC_KEY = '6Ld2ilErAAAAANKz1d0dytvMyM0SuTq_ir4tULYz'
RECAPTCHA_PRIVATE_KEY = '6Ld2ilErAAAAAPE2ZJM_7n3CzI1gdFWqTRKtWKWU'

# Configuration Stripe
STRIPE_PUBLIC_KEY = 'pk_test_...'  # À remplacer par votre clé publique Stripe
STRIPE_SECRET_KEY = 'sk_test_...'  # À remplacer par votre clé secrète Stripe

# Configuration PayPal
PAYPAL_CLIENT_ID = 'your_paypal_client_id'  # À remplacer par votre client ID PayPal
PAYPAL_CLIENT_SECRET = 'your_paypal_client_secret'  # À remplacer par votre secret PayPal
PAYPAL_MODE = 'sandbox'  # 'sandbox' pour test, 'live' pour production

SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Configuration CSP pour remplacer X-Frame-Options
SECURE_CONTENT_SECURITY_POLICY = {
    'frame-ancestors': ["'self'"],
    'default-src': ["'self'"],
    'script-src': ["'self'", "'unsafe-inline'", "https://js.stripe.com", "https://www.paypal.com", "https://cdn.jsdelivr.net", "https://unpkg.com", "https://cdnjs.cloudflare.com"],
    'style-src': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://cdn.jsdelivr.net", "https://unpkg.com", "https://cdnjs.cloudflare.com"],
    'font-src': ["'self'", "https://fonts.gstatic.com", "https://cdnjs.cloudflare.com"],
    'img-src': ["'self'", "data:", "https:", "http:"],
    'connect-src': ["'self'", "https://api.stripe.com", "https://www.paypal.com", "wss:", "ws:"],
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'store': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False,
        },
    },
}

ASGI_APPLICATION = 'ecommerce_project.asgi.application'
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('127.0.0.1', 6379)],
        },
    },
}


handler404 = 'store.views.custom_404'

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True
    SESSION_COOKIE_HTTPONLY = True