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
            "django_improve_form",
        ),
        TIME_ZONE="UTC",
        USE_TZ=True,
    )
    django.setup()
