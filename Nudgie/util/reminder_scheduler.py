from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json

CRONTAB_FIELDS = ['minute', 'hour', 'day_of_week']

def convert_crontab_val_if_necessary(s):
    try:
        if s != '*':
            return int(s)
    except ValueError:
        raise ValueError(f"Failed to convert s. Must have a value of '*' or an integer. s = {s}")

def schedule_tasks_from_crontab_list(crontab_list):
    for notif in crontab_list:
        # validate and convert crontabs
        for field in CRONTAB_FIELDS:
            notif[field] = convert_crontab_val_if_necessary(notif[field])

        cron_schedule, _ = CrontabSchedule.objects.get_or_create(**notif)
        
        PeriodicTask.objects.create(
            crontab=cron_schedule,
            name='Notification at ' + str(notif['hour']) + ':' + str(notif['minute'])
              + ' on ' + str(notif['day_of_week']),
            task='Nudgie.tasks.notify',
            args=json.dumps(['Task scheduled for ' + str(notif['hour']) + ':'
                              + str(notif['minute']) + ' on ' + str(notif['day_of_week'])
                              + ' completed']),
            queue='nudgie'
        )
