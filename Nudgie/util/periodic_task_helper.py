import json
from django_celery_beat.models import PeriodicTask
from typing import NamedTuple, Optional
from django_celery_beat.models import CrontabSchedule


class TaskData(NamedTuple):
    crontab: CrontabSchedule
    task_name: str
    goal_name: str
    user_id: int
    due_date: str
    dialogue_type: str
    next_run_time: Optional[str] = None  # only for testing tool, get rid of later


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
    )
