import json
from django_celery_beat.models import PeriodicTask
from typing import NamedTuple, Optional
from django_celery_beat.models import CrontabSchedule


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
