from django_celery_beat.models import PeriodicTask
from datetime import datetime
from django.contrib.auth.models import User
from django_celery_beat.models import CrontabSchedule
from Nudgie.models import NudgieTask
from Nudgie.time_utils.time import get_next_run_time_from_crontab
from Nudgie.constants import (
    DEADLINE_HANDLER,
    NUDGE_HANDLER,
    REMINDER_HANDLER,
    QUEUE_NAME,
    DIALOGUE_TYPE_NUDGE,
    DIALOGUE_TYPE_REMINDER,
    DIALOGUE_TYPE_DEADLINE,
)
from Nudgie.scheduling.periodic_task_helper import (
    TaskData,
    convert_chatgpt_task_data_to_task_data,
)


def schedule_deadline_task(task_data: TaskData) -> None:
    """Schedule a deadline task to run at the specified crontab time."""
    due_date_as_datetime = datetime.fromisoformat(task_data.due_date)
    print(f"creating crontab for {due_date_as_datetime}")
    crontab, _ = CrontabSchedule.objects.get_or_create(
        minute=due_date_as_datetime.minute,
        hour=due_date_as_datetime.hour,
        day_of_month=due_date_as_datetime.day,
        month_of_year=due_date_as_datetime.month,
    )
    # Update the TaskData job non-destructively
    task_data = task_data._replace(
        crontab=crontab,
        dialogue_type=DIALOGUE_TYPE_DEADLINE,
        next_run_time=get_next_run_time_from_crontab(
            crontab, User.objects.get(id=task_data.user_id)
        ).isoformat(),
    )
    schedule_periodic_task(task_data, DEADLINE_HANDLER, True)


def schedule_nudgie_task(task_data: TaskData) -> None:
    """Creates a NudgieTask, indicating an outstanding task. NudgieTasks are used as a source of truth as to which tasks
    are still pending completion, and which have been completed. Each time a NudgieTask is logged in the database, a new
    deadline job is also scheduled. This deadline job, when triggered, will notify the user that he failed to complete the
    task on time."""
    user = User.objects.get(id=task_data.user_id)
    NudgieTask.objects.create(
        user=user,
        task_name=task_data.task_name,
        goal_name=task_data.goal_name,
        due_date=task_data.due_date,
    )

    schedule_deadline_task(task_data)


def schedule_periodic_task(
    task_data: TaskData, celery_task: str, one_off: bool = False
):
    """Schedule a periodic task to run at the specified crontab time.
    task_data is a dictionary of key-value pairs that will be passed as kwargs
    to the task.
    """
    PeriodicTask.objects.create(
        crontab=task_data.crontab,
        name=f"{task_data.user_id}: {task_data.dialogue_type} for {str(task_data.crontab)} created at {datetime.now().isoformat()}",
        task=celery_task,
        kwargs=task_data.get_as_kwargs(),
        one_off=one_off,
        queue=QUEUE_NAME,
    )


def schedule_nudge(task_data: TaskData):
    """Schedule a nudge to run at the specified crontab time.
    task_data is a dictionary of key-value pairs that will be passed as kwargs
    to the task.
    """
    new_task_data = task_data._replace(dialogue_type=DIALOGUE_TYPE_NUDGE)
    schedule_periodic_task(new_task_data, NUDGE_HANDLER, True)


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

        schedule_nudgie_task(task_data)
        schedule_reminder(task_data)
