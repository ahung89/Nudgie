from django_celery_beat.models import PeriodicTask
from datetime import datetime
from Nudgie.models import NudgieTask
from Nudgie.util.constants import (
    NUDGE_HANDLER,
    REMINDER_HANDLER,
)
from Nudgie.util.constants import (
    QUEUE_NAME,
    DIALOGUE_TYPE_NUDGE,
    DIALOGUE_TYPE_REMINDER,
)
from Nudgie.util.periodic_task_helper import (
    TaskData,
    convert_chatgpt_task_data_to_task_data,
)

CRONTAB_FIELDS = ["minute", "hour", "day_of_week"]


def schedule_periodic_task(task_data: TaskData, celery_task: str):
    """Schedule a periodic task to run at the specified crontab time.
    task_data is a dictionary of key-value pairs that will be passed as kwargs
    to the task.
    """
    PeriodicTask.objects.create(
        crontab=task_data.crontab,
        name=f"{task_data.user_id}: {task_data.dialogue_type} for {str(task_data.crontab)} created at {datetime.now().isoformat()}",
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
    schedule_periodic_task(new_task_data, NUDGE_HANDLER)


def schedule_reminder(task_data: TaskData):
    """Schedule a reminder to run at the specified crontab time.
    task_data is a dictionary of key-value pairs that will be passed as kwargs
    to the task.
    """
    new_task_data = task_data._replace(dialogue_type=DIALOGUE_TYPE_REMINDER)
    schedule_periodic_task(new_task_data, REMINDER_HANDLER)


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
