import os
import django

# Set up the Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Nudgie.settings')
django.setup()

from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule, SolarSchedule

# Delete all the periodic tasks
PeriodicTask.objects.all().delete()

# If you want to delete all associated schedules as well
IntervalSchedule.objects.all().delete()
CrontabSchedule.objects.all().delete()
SolarSchedule.objects.all().delete()

print("All tasks and schedules cleared!")
