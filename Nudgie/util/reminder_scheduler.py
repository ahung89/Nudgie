from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json
from croniter import croniter
from datetime import datetime
from django.contrib.auth.models import User
from Nudgie.models import NudgieTask
from Nudgie.util.time import get_time

CRONTAB_FIELDS = ["minute", "hour", "day_of_week"]


def get_next_run_time(
    minute: int,
    hour: int,
    day_of_month: int,
    month_of_year: int,
    day_of_week: int,
    user: User,
):
    crontab_str = (
        f"{minute} {hour} " f"{day_of_month} {month_of_year} " f"{day_of_week}"
    )
    print(f"CRON_STR IS {crontab_str}")
    iter = croniter(crontab_str, get_time(user))
    next_run_time = iter.get_next(datetime)
    return next_run_time


def end_of_day(dt):
    return dt.replace(hour=23, minute=59, second=59)


def calculate_due_date(
    minute: int,
    hour: int,
    day_of_month: int,
    month_of_year: int,
    day_of_week: int,
    user: User,
):
    """Given a crontab object (key-val pairs), calculate the next due date for the task.
    By default, the due date is the end of the day of the next time the crontab
    will run. For example, if the crontab is set to run at 9:00 AM on Monday,
    the due date will be 11:59 PM on Monday.
    """
    return end_of_day(
        get_next_run_time(minute, hour, day_of_month, month_of_year, day_of_week, user)
    )


def schedule_tasks_from_crontab_list(crontab_list, user):
    for notif in crontab_list:
        notif_cron = notif["crontab"]
        notif["reminder_data"]["user_id"] = user.id

        cron_schedule, _ = CrontabSchedule.objects.get_or_create(**notif_cron)

        due_date = calculate_due_date(
            notif_cron["minute"],
            notif_cron["hour"],
            "*",
            "*",
            notif_cron["day_of_week"],
            user,
        )

        notif["reminder_data"]["due_date"] = due_date.isoformat()
        # to deserialize, call date.fromisoformat(due_date) (date being imported from datetime)
        # you can then directly use this to query the DB.

        NudgieTask.objects.create(
            user=user,
            task_name=notif["reminder_data"]["task_name"],
            goal_name=notif["reminder_data"]["goal_name"],
            due_date=due_date,
        )

        PeriodicTask.objects.create(
            crontab=cron_schedule,
            name=str(user.id)
            + "_Notification at "
            + str(notif_cron["hour"])
            + ":"
            + str(notif_cron["minute"])
            + " on "
            + str(notif_cron["day_of_week"]),
            task="Nudgie.tasks.handle_reminder",
            args=json.dumps(
                [
                    "Task scheduled for "
                    + str(notif_cron["hour"])
                    + ":"
                    + str(notif_cron["minute"])
                    + " on "
                    + str(notif_cron["day_of_week"])
                    + " completed"
                ]
            ),
            kwargs=json.dumps({**notif["reminder_data"], "dialogue_type": "reminder"}),
            queue="nudgie",
        )
