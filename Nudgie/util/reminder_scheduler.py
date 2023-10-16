from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json

CRONTAB_FIELDS = ['minute', 'hour', 'day_of_week']

def schedule_tasks_from_crontab_list(crontab_list, user_id):
    for notif in crontab_list:
        notif_cron = notif['crontab']
        notif['reminder_data']['user_id'] = user_id

        cron_schedule, _ = CrontabSchedule.objects.get_or_create(**notif_cron)
        
        PeriodicTask.objects.create(
            crontab=cron_schedule,
            name='Notification at ' + str(notif_cron['hour']) + ':' + str(notif_cron['minute'])
              + ' on ' + str(notif_cron['day_of_week']),
            task='Nudgie.tasks.notify',
            args=json.dumps(['Task scheduled for ' + str(notif_cron['hour']) + ':'
                              + str(notif_cron['minute']) + ' on ' + str(notif_cron['day_of_week'])
                              + ' completed']),
            kwargs=json.dumps(notif['reminder_data']),
            queue='nudgie'
        )
