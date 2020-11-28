# Sets up django environment. Used by other scripts to run the stand alone app in the sample Django project.
import os
import django
from django.conf import settings

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "django_improve_form"))


def boot_django():
    settings.configure(
        BASE_DIR=BASE_DIR,
        DEBUG=True,
        DATABASES={
            "default":{
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
            }
        },
        INSTALLED_APPS=(
            'django.contrib.contenttypes',
            'django.contrib.auth',
            # 'django_registration',
            "django_improve_form",
        ),
        # ROOT_URLCONF='django_improve_form.urls_activation',
        ROOT_URLCONF='django_improve_form.tests.urls_simple',
        TEMPLATES=[
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'DIRS': [os.path.join(BASE_DIR, 'templates')],
                # 'DIRS': [],
                'APP_DIRS': True,
                # 'OPTIONS': {
                #     'context_processors': [
                #         'django.template.context_processors.debug',
                #         'django.template.context_processors.request',
                #         'django.contrib.auth.context_processors.auth',
                #         'django.contrib.messages.context_processors.messages',
                #     ],
                # },
            },
        ],

        TIME_ZONE="UTC",
        USE_TZ=True,
    )
    django.setup()
