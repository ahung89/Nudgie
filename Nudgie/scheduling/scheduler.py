from datetime import datetime

from django.contrib.auth.models import User
from django_celery_beat.models import CrontabSchedule, PeriodicTask

from Nudgie.constants import (
    DEADLINE_HANDLER,
    DIALOGUE_TYPE_DEADLINE,
    DIALOGUE_TYPE_GOAL_END,
    DIALOGUE_TYPE_NUDGE,
    DIALOGUE_TYPE_REMINDER,
    GOAL_END_HANDLER,
    NUDGE_HANDLER,
    QUEUE_NAME,
    REMINDER_HANDLER,
)
from Nudgie.models import NudgieTask
from Nudgie.scheduling.periodic_task_helper import (
    TaskData,
    convert_chatgpt_task_data_to_task_data,
)
from Nudgie.time_utils.time import date_to_crontab, get_next_run_time_from_crontab


def schedule_deadline_task(task_data: TaskData) -> None:
    """Schedule a deadline task to run at the specified crontab time."""
    due_date_as_datetime = datetime.fromisoformat(task_data.due_date)

    print(f"creating crontab for {due_date_as_datetime}")
    crontab = date_to_crontab(due_date_as_datetime)

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
    schedule_periodic_task(
        task_data=new_task_data, celery_task=NUDGE_HANDLER, one_off=True
    )


def schedule_goal_end(task_data: TaskData):
    """Schedule the event for when a goal's end date is reached."""
    # task name is set to "" here because this is a special case. normally this object is used
    # to pass data about a task, but in this case we only need the goal data.
    new_task_data = task_data._replace(
        dialogue_type=DIALOGUE_TYPE_GOAL_END, task_name=""
    )
    schedule_periodic_task(
        task_data=new_task_data, celery_task=GOAL_END_HANDLER, one_off=True
    )


def schedule_reminder(task_data: TaskData):
    """Schedule a reminder to run at the specified crontab time.
    task_data is a dictionary of key-value pairs that will be passed as kwargs
    to the task.
    """
    new_task_data = task_data._replace(dialogue_type=DIALOGUE_TYPE_REMINDER)
    schedule_periodic_task(task_data=new_task_data, celery_task=REMINDER_HANDLER)


def schedule_tasks_from_crontab_list(crontab_list, goal_name, user):
    """Given a list of crontab objects, schedule the tasks to run at the specified times."""
    for notif in crontab_list:
        task_data = convert_chatgpt_task_data_to_task_data(notif, goal_name, user)

        schedule_nudgie_task(task_data)
        schedule_reminder(task_data)
