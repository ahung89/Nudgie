import json
from django.contrib.auth.models import User
from django_celery_beat.models import PeriodicTask
from typing import NamedTuple, Optional, Any
from django_celery_beat.models import CrontabSchedule
from Nudgie.util.time import (
    calculate_due_date_from_crontab,
    get_next_run_time_from_crontab,
)
from Nudgie.util.constants import (
    REMINDER_DATA_AI_STRUCT_KEY,
    TASK_NAME_AI_STRUCT_KEY,
    GOAL_NAME_AI_STRUCT_KEY,
    REMINDER_NOTES_AI_STRUCT_KEY,
    CRONTAB_AI_STRUCT_KEY,
    DIALOGUE_TYPE_REMINDER,
)


class TaskData(NamedTuple):
    crontab: CrontabSchedule
    task_name: str
    goal_name: str
    user_id: int  # store user instead of the ID?
    due_date: str
    dialogue_type: str
    reminder_notes: Optional[str] = None
    next_run_time: Optional[str] = None  # only for testing tool, get rid of later

    def get_as_kwargs(self):
        return json.dumps(
            {
                "task_name": self.task_name,
                "goal_name": self.goal_name,
                "due_date": self.due_date,
                "user_id": self.user_id,
                "dialogue_type": self.dialogue_type,
                "reminder_notes": self.reminder_notes,
                "next_run_time": self.next_run_time,
            }
        )


def modify_periodic_task(
    id: int,
    crontab: Optional[CrontabSchedule] = None,
    task_name: Optional[str] = None,
    goal_name: Optional[str] = None,
    user_id: Optional[int] = None,
    due_date: Optional[str] = None,
    dialogue_type: Optional[str] = None,
    next_run_time: Optional[str] = None,
    reminder_notes: Optional[str] = None,
):
    task = PeriodicTask.objects.get(id=id)
    current_kwargs = json.loads(task.kwargs)

    for key in [
        "crontab",
        "task_name",
        "goal_name",
        "user_id",
        "due_date",
        "dialogue_type",
        "next_run_time",
        "reminder_notes",
    ]:
        value = locals()[key]
        if value is not None:
            current_kwargs[key] = value

    task.kwargs = json.dumps(current_kwargs)
    task.save()


def get_periodic_task_data(id):
    task = PeriodicTask.objects.get(id=id)
    kwargs = json.loads(task.kwargs)

    return TaskData(
        crontab=task.crontab,
        task_name=kwargs["task_name"],
        goal_name=kwargs["goal_name"],
        user_id=kwargs["user_id"],
        due_date=kwargs["due_date"],
        dialogue_type=kwargs.get("dialogue_type"),
        reminder_notes=kwargs.get("reminder_notes"),
    )


def convert_chatgpt_task_data_to_task_data(
    chatgpt_task_data: dict[Any, Any], user: User
) -> TaskData:
    """Convert a dictionary of key-value pairs from the chatgpt task data to a TaskData object."""
    cron_schedule, _ = CrontabSchedule.objects.get_or_create(
        chatgpt_task_data[CRONTAB_AI_STRUCT_KEY]
    )
    due_date = calculate_due_date_from_crontab(cron_schedule, user).isoformat()

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
        next_run_time=get_next_run_time_from_crontab(
            cron_schedule,
            user,
        ).isoformat(),
    )
