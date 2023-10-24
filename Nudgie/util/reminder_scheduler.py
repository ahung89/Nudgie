from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json
from croniter import croniter
from datetime import datetime
from django.contrib.auth.models import User
from Nudgie.models import NudgieTask
from Nudgie.util.constants import (
    REMINDER_DATA_AI_STRUCT_KEY,
    TASK_NAME_AI_STRUCT_KEY,
    GOAL_NAME_AI_STRUCT_KEY,
    REMINDER_NOTES_AI_STRUCT_KEY,
    CRONTAB_AI_STRUCT_KEY,
)
from typing import Any
from Nudgie.util.time import get_time
from Nudgie.util.constants import (
    QUEUE_NAME,
    DIALOGUE_TYPE_NUDGE,
    DIALOGUE_TYPE_REMINDER,
)
from Nudgie.util.periodic_task_helper import TaskData

CRONTAB_FIELDS = ["minute", "hour", "day_of_week"]


def schedule_periodic_task(task_data: TaskData, celery_task: str):
    """Schedule a periodic task to run at the specified crontab time.
    task_data is a dictionary of key-value pairs that will be passed as kwargs
    to the task.
    """
    PeriodicTask.objects.create(
        crontab=task_data.crontab,
        name=f"{task_data.dialogue_type} for {str(task_data.crontab)}",
        task=celery_task,
        kwargs=task_data.get_as_kwargs(),
        one_off=task_data.dialogue_type == DIALOGUE_TYPE_NUDGE,
        queue=QUEUE_NAME,
    )


def schedule_nudge(task_data: TaskData):
    """Schedule a nudge to run at the specified crontab time.
    task_data is a dictionary of key-value pairs that will be passed as kwargs
    to the task.
    """
    new_task_data = task_data._replace(dialogue_type=DIALOGUE_TYPE_NUDGE)
    schedule_periodic_task(task_data, new_task_data)


def schedule_reminder(task_data: TaskData):
    """Schedule a reminder to run at the specified crontab time.
    task_data is a dictionary of key-value pairs that will be passed as kwargs
    to the task.
    """
    new_task_data = task_data._replace(dialogue_type=DIALOGUE_TYPE_REMINDER)
    schedule_periodic_task(task_data, new_task_data)


def get_next_run_time(
    minute: int,
    hour: int,
    day_of_month: int,
    month_of_year: int,
    day_of_week: int,
    user: User,
):
    """Given a crontab object (key-val pairs), calculate the next due date for the task."""
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
) -> datetime:
    """Given a crontab object (key-val pairs), calculate the next due date for the task.
    By default, the due date is the end of the day of the next time the crontab
    will run. For example, if the crontab is set to run at 9:00 AM on Monday,
    the due date will be 11:59 PM on Monday.
    """
    return end_of_day(
        get_next_run_time(minute, hour, day_of_month, month_of_year, day_of_week, user)
    )


def convert_chatgpt_task_data_to_task_data(
    chatgpt_task_data: dict[Any, Any], user: User
) -> TaskData:
    """Convert a dictionary of key-value pairs from the chatgpt task data to a TaskData object."""
    cron_schedule, _ = CrontabSchedule.objects.get_or_create(
        chatgpt_task_data[CRONTAB_AI_STRUCT_KEY]
    )
    due_date = calculate_due_date(
        cron_schedule.minute,
        cron_schedule.hour,
        cron_schedule.day_of_month,
        cron_schedule.month_of_year,
        cron_schedule.day_of_week,
        user,
    ).isoformat()

    return TaskData(
        crontab=cron_schedule,
        task_name=chatgpt_task_data[REMINDER_DATA_AI_STRUCT_KEY][
            TASK_NAME_AI_STRUCT_KEY
        ],
        goal_name=chatgpt_task_data[REMINDER_DATA_AI_STRUCT_KEY][
            GOAL_NAME_AI_STRUCT_KEY
        ],
        user_id=user.id,
        due_date=due_date,
        dialogue_type=DIALOGUE_TYPE_REMINDER,  # Always reminders, the AI doesn't schedule nudges
        reminder_notes=chatgpt_task_data[REMINDER_DATA_AI_STRUCT_KEY][
            REMINDER_NOTES_AI_STRUCT_KEY
        ],
    )


def schedule_tasks_from_crontab_list(crontab_list, user):
    """Given a list of crontab objects, schedule the tasks to run at the specified times."""
    for notif in crontab_list:
        task_data = convert_chatgpt_task_data_to_task_data(notif, user)

        NudgieTask.objects.create(
            user=user,
            task_name=task_data.task_name,
            goal_name=task_data.goal_name,
            due_date=task_data.due_date,
        )

        schedule_reminder(task_data)
