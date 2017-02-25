"""
Django settings for the whole project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = ')88d_*x548u8bt#r=@kt)n1w%51xq-zxjp@e7qgerfxgom15b_'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = DEBUG

ALLOWED_HOSTS = ["*"]


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'app',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    #'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'aips.api.JsonApiMiddleware',
)

ROOT_URLCONF = 'aips.urls'

WSGI_APPLICATION = 'aips.wsgi.application'

# SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        # 'ENGINE': 'django.db.backends.dummy'
        'ENGINE': 'django.db.backends.mysql',
        'HOST': '127.0.0.1', # the default "localhost" will cause a failure of connection
        'PORT': '3306',
        'NAME': 'orgs',
        'USER': 'root',
        'PASSWORD': 'root',
        'OPTIONS':{
            'init_command': 'SET storage_engine=INNODB',
        },
    }
}

AUTH_USER_MODEL  = 'app.CustomUser'

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'zh-Hans'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/
from django import VERSION as DJANGO_VERSION
CTX_MODULE = 'django.template.context_processors' \
    if DJANGO_VERSION[0] > 1 or DJANGO_VERSION[1] > 8 \
    else 'django.core.context_processors'

TEMPLATE_CONTEXT_PROCESSORS = (
    CTX_MODULE + ".debug",
    CTX_MODULE + ".request",
    CTX_MODULE + ".i18n",
    CTX_MODULE + ".static",
    CTX_MODULE + ".tz",
    CTX_MODULE + ".csrf",
    "django.contrib.auth.context_processors.auth",
    "django.contrib.messages.context_processors.messages",
)

TEMPLATE_DIRS = (
    BASE_DIR + '/templates',
)

TEMPLATES = ({
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': TEMPLATE_DIRS,
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': TEMPLATE_CONTEXT_PROCESSORS,
        'debug': TEMPLATE_DEBUG,
    }
}, )

if DJANGO_VERSION[0] > 1 or DJANGO_VERSION[1] > 8:
    del TEMPLATE_DIRS, TEMPLATE_DEBUG, TEMPLATE_CONTEXT_PROCESSORS
del CTX_MODULE


STATIC_URL = '/static/'
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "static"),
)

# Program Settings

FILE_UPLOAD_PATH = 'upload/'
FILE_UPLOAD_URL = '/upload/'

DEFAULT_CHARSET = 'utf-8'
FILE_CHARSET = DEFAULT_CHARSET

import sys
reload(sys)
sys.setdefaultencoding(DEFAULT_CHARSET)
del sys
