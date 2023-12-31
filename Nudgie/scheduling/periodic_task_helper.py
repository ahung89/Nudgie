import json
from typing import Any, NamedTuple, Optional

from django.contrib.auth.models import User
from django_celery_beat.models import CrontabSchedule, PeriodicTask

from Nudgie.constants import (
    CRONTAB_AI_STRUCT_KEY,
    DIALOGUE_TYPE_REMINDER,
    PERIODIC_TASK_CRONTAB_FIELD,
    REMINDER_DATA_AI_STRUCT_KEY,
    REMINDER_NOTES_AI_STRUCT_KEY,
    TASK_NAME_AI_STRUCT_KEY,
)
from Nudgie.time_utils.time import (
    calculate_due_date_from_crontab,
    get_next_run_time_from_crontab,
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
                k: v
                for k, v in self._asdict().items()
                if k != PERIODIC_TASK_CRONTAB_FIELD
            }
        )

    def __str__(self):
        return (
            f"TaskData(crontab={self.crontab}, task_name={self.task_name}, "
            f"goal_name={self.goal_name}, user_id={self.user_id}, "
            f"due_date={self.due_date}, dialogue_type={self.dialogue_type}, "
            f"reminder_notes={self.reminder_notes}, "
            f"next_run_time={self.next_run_time})"
        )


def modify_periodic_task(id: int, task_data: Optional[TaskData] = None):
    """
    Modifies a periodic task by updating the crontab and kwargs fields with the
    values provided in task_data.
    """
    task = PeriodicTask.objects.get(id=id)
    current_kwargs = json.loads(task.kwargs)

    if task_data:
        task_data_dict = task_data._asdict()

        for key, value in task_data_dict.items():
            if value is not None:
                if key is PERIODIC_TASK_CRONTAB_FIELD:
                    task.crontab = value
                else:
                    current_kwargs[key] = value

        task.kwargs = json.dumps(current_kwargs)
        task.save()


def get_periodic_task_data(id):
    task = PeriodicTask.objects.get(id=id)
    kwargs = json.loads(task.kwargs)

    return TaskData(crontab=task.crontab, **kwargs)


def convert_chatgpt_task_data_to_task_data(
    chatgpt_task_data: dict[Any, Any], goal_name: str, user: User
) -> TaskData:
    print("creating CrontabSchedule for", chatgpt_task_data[CRONTAB_AI_STRUCT_KEY])

    """
    Convert a dictionary of key-value pairs from the chatgpt task data 
    to a TaskData object.
    """
    cron_schedule, _ = CrontabSchedule.objects.get_or_create(
        **chatgpt_task_data[CRONTAB_AI_STRUCT_KEY]
    )
    due_date = calculate_due_date_from_crontab(cron_schedule, user).isoformat()

    return TaskData(
        crontab=cron_schedule,
        task_name=chatgpt_task_data[REMINDER_DATA_AI_STRUCT_KEY][
            TASK_NAME_AI_STRUCT_KEY
        ],
        goal_name=goal_name,
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
