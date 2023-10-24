import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
# This sets the environment variable DJANGO_SETTINGS_MODULE to 'proj.settings', making
# the settings module accessible. It is absolutely critical, otherwise Celery won't recognize
# that it's running with Django.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Nudgie.settings")

app = Celery("Nudgie")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
#
# ANDREW EXPLANATION: django.conf:settings indicates that celery should use the settings
# defined in the settings.py file for its config. namespace='CELERY' means that only
# the settings in settings.py that start with CELERY_ will be used by celery. This helps keep Celery-specific
# settings separated. E.g. a setting named 'CELERY_BROKER_URL' would be used at celery, but a setting named 'BROKER_URL' wouldnt't.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
# this way you don't need to manually register all of your tasks via CELERY_IMPORTS
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
