# ALLOWED_HOSTS = ['3.34.48.55', '127.0.0.1', 'localhost']

import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# .env 파일 로드
# 로컬에서는 .env.local 사용, 없으면 .env 사용
env_file = BASE_DIR / '.env.local'
if not env_file.exists():
    env_file = BASE_DIR / '.env'

load_dotenv(env_file)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-default-key-change-this')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', 'localhost').split(',') if h.strip()]

# CSRF 검증 실패 시 기본 403 디버그 화면 대신 로그인 페이지로 안내
CSRF_FAILURE_VIEW = 'pricehub.views.csrf_failure'

# HTTPS 하드닝 — nginx 등 리버스 프록시가 TLS를 종료하고 서비스하는 배포라면
# .env에 USE_HTTPS=True 로 켤 것. 기본값 False라 아직 HTTP로만 운영 중이어도
# 이 설정 때문에 접속이 막히지는 않는다 (그런 경우엔 반드시 켜야 세션/CSRF
# 쿠키가 Secure 플래그 없이 평문 HTTP로 새어나가는 걸 막을 수 있다).
USE_HTTPS = os.getenv('USE_HTTPS', 'False') == 'True'

SESSION_COOKIE_SECURE = USE_HTTPS
CSRF_COOKIE_SECURE = USE_HTTPS
CSRF_COOKIE_HTTPONLY = True
SECURE_SSL_REDIRECT = USE_HTTPS

if USE_HTTPS:
    # nginx/ALB 등이 TLS 종료 후 X-Forwarded-Proto 헤더로 넘겨주는 구성을 가정.
    # 리버스 프록시 없이 Django가 TLS를 직접 종료한다면 이 줄은 지울 것.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = 31536000  # 1년
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'django_filters',
    'pricehub',
]

# DRF — 외부 연동 API(Authorization: Api-Key ...)에 기본 레이트리밋 적용.
# 캐시 백엔드를 따로 지정하지 않으면 Django 기본 LocMemCache를 쓰는데,
# 이건 프로세스 로컬이라 워커가 여러 개면(gunicorn -w N 등) 워커별로 한도가
# 따로 적용된다. 정확한 전역 제한이 필요하면 CACHES에 Redis 등 공유 캐시를 설정할 것.
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'pricehub.throttling.APIKeyRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'api_key': os.getenv('API_THROTTLE_RATE', '300/min'),
    },
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'pricehub' / 'templates'],
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

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME', 'pokemon_card_db'),
        'USER': os.getenv('DB_USER', 'root'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
        }
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'