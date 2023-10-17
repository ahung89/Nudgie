from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json
from croniter import croniter
from datetime import datetime
from Nudgie import models
from Nudgie.models import NudgieTask

CRONTAB_FIELDS = ['minute', 'hour', 'day_of_week']

def get_next_run_time(crontab):
    iter = croniter(crontab, datetime.now())
    next_run_time = iter.get_next(datetime)
    return next_run_time

def end_of_day(dt):
    return dt.replace(hour=23, minute=59, second=59)

def calculate_due_date(crontab):
    """Given a crontab object, calculate the next due date for the task.
    By default, the due date is the end of the day of the next time the crontab
    will run. For example, if the crontab is set to run at 9:00 AM on Monday,
    the due date will be 11:59 PM on Monday.
    """
    #convert to string form
    cron_str = f"{crontab['minute']} {crontab['hour']} * * {crontab['day_of_week']}"
    print(f'CRON_STR IS {cron_str}')
    return end_of_day(get_next_run_time(cron_str))

def schedule_tasks_from_crontab_list(crontab_list, user_id):
    for notif in crontab_list:
        notif_cron = notif['crontab']
        notif['reminder_data']['user_id'] = user_id

        cron_schedule, _ = CrontabSchedule.objects.get_or_create(**notif_cron)

        due_date = calculate_due_date(notif_cron)

        notif['reminder_data']['due_date'] = due_date.isoformat()
        #to deserialize, call date.fromisoformat(due_date) (date being imported from datetime)
        #you can then directly use this to query the DB.
        
        NudgieTask.objects.create(
            user = models.User.objects.get(id=user_id), #TODO: just pass in the user object?
            task_name = notif['reminder_data']['task_name'],
            goal_name = notif['reminder_data']['goal_name'],
            due_date = due_date
        )

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
