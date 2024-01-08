from datetime import datetime, timedelta

from celery import shared_task
from django.contrib.auth.models import User
from django_celery_beat.models import PeriodicTask

from Nudgie.chat.chatgpt import (
    generate_and_send_deadline,
    generate_and_send_nudge,
    generate_and_send_performance_summary,
    generate_and_send_reminder,
)
from Nudgie.config.chatgpt_inputs import PERFORMANCE_DATA_TEMPLATE_FOR_ONE_TASK
from Nudgie.scheduling.scheduler import create_nudgie_task, schedule_nudge
from Nudgie.time_utils.time import (
    calculate_due_date_from_crontab,
    get_next_run_time_from_crontab,
    get_time,
)

from .constants import (
    MAX_NUDGES_PER_REMINDER,
    MIN_MINUTES_BETWEEN_NUDGES,
    MIN_TIME_BETWEEN_LAST_NUDGE_AND_DUE_DATE,
)
from .models import Goal, NudgieTask, Task
from .scheduling.periodic_task_helper import (
    TaskData,
    get_periodic_task_data,
    modify_periodic_task,
)

# for app.autodiscover_tasks() to work, you need to define a tasks.py file in each app.
# that's why this file is here.
# in larger projects, you might have multiple apps, each with their own tasks.py file, each
# of which defines celery tasks.


def get_nudgie_task(task_name: str, user_id: str, due_date: datetime) -> NudgieTask:
    """Queries DB for a single NudgieTask object."""
    filtered_tasks = NudgieTask.objects.filter(
        task__name=task_name, user_id=user_id, due_date=due_date
    )

    assert len(filtered_tasks) == 1, f"expected 1 task, got {len(filtered_tasks)}"

    return filtered_tasks[0]


def deactivate_nudge(periodic_task_id: int) -> None:
    """Deactivates a nudge by deleting the periodic task associated with the nudge (because it's set
    to one-off, this will happen automatically in production, so the explicit deactivation is just for
    the test tool)
    """
    PeriodicTask.objects.get(id=periodic_task_id).delete()


# shared_task is different from app.task in that it doesn't require a celery app to be defined.
# this is so that it can be used in other apps. The thing is, reusable apps cannot depend
# on the project itself. So you can't import the celery app from the project.
@shared_task
def handle_nudge(periodic_task_id) -> None:
    """
    A nudge must know the due date, task name, and related notes/info. It must not
    fire off if the task has already been completed, or if the due date was missed.
    """
    task_data = get_periodic_task_data(periodic_task_id)
    print(f"handling nudge for task {task_data.task_name} due on {task_data.due_date}")

    nudgie_task = get_nudgie_task(
        task_data.task_name,
        task_data.user_id,
        datetime.fromisoformat(task_data.due_date),
    )

    # only trigger the nudge if the task hasn't already been completed.
    if not nudgie_task.completed:
        print("task incomplete, sending nudge")
        generate_and_send_nudge(User.objects.get(id=task_data.user_id))

    deactivate_nudge(periodic_task_id)


@shared_task
def goal_end_handler(periodic_task_id) -> None:
    """
    Calculates the performance data and sends a message to the user congratulating him and giving him
    a breakdown of his performance on each task. Closes out the goal.
    """
    task_data = get_periodic_task_data(periodic_task_id)
    goal_name = task_data.goal_name

    goal = Goal.objects.get(goal_name=goal_name)
    tasks = Task.objects.filter(goal=goal)

    performance_data = ""
    for task in tasks:
        nudgie_tasks = NudgieTask.objects.filter(task=task)
        completion_count = sum(
            1 for nudgie_task in nudgie_tasks if nudgie_task.completed
        )
        completion_rate = str((completion_count / len(nudgie_tasks)) * 100) + "%"
        performance_data += PERFORMANCE_DATA_TEMPLATE_FOR_ONE_TASK.format(
            task_name=task.name,
            num_completed=completion_count,
            num_total=len(nudgie_tasks),
            completion_rate=completion_rate,
        )

        print(
            f"PERFORMANCE DATA DEBUG: {task.name} completed {completion_count} out of {len(nudgie_tasks)} tasks "
            f"for a completion rate of {completion_rate}"
        )

    aggregated_data = performance_data
    generate_and_send_performance_summary(
        User.objects.get(id=task_data.user_id), goal_name, aggregated_data
    )


@shared_task
def deadline_handler(periodic_task_id) -> None:
    """
    When a deadline is reached, if the task has not yet been completed, the user will be notified of his failure to complete the task on time.
    """
    task_data = get_periodic_task_data(periodic_task_id)
    print(
        f"handling deadline for task {task_data.task_name} due on {task_data.due_date}"
    )

    nudgie_task = get_nudgie_task(
        task_data.task_name,
        task_data.user_id,
        datetime.fromisoformat(task_data.due_date),
    )

    if not nudgie_task.completed:
        print("task incomplete, sending deadline notification")
        generate_and_send_deadline(task_data)
        # TODO: log datapoint or otherwise make it visible in the UI that the user missed the deadline

    # Deactivate the task. Only necessary when manually triggering for testing, in production
    # the one-off switch should take care of this.
    PeriodicTask.objects.get(id=periodic_task_id).delete()


def generate_nudges(user: User, task_data: TaskData) -> None:
    """Generate nudges for a reminder. The number of nudges is determined by the
    time between the due date and the current time, with a bit of cushion added to the end.
    """
    last_possible_nudge_time = datetime.fromisoformat(task_data.due_date) - timedelta(
        minutes=MIN_TIME_BETWEEN_LAST_NUDGE_AND_DUE_DATE
    )
    current_time = get_time(user)
    total_interval = (last_possible_nudge_time - current_time).total_seconds() / 60

    num_nudges_that_fit = int(total_interval // MIN_MINUTES_BETWEEN_NUDGES)
    actual_num_nudges = min(MAX_NUDGES_PER_REMINDER, num_nudges_that_fit)

    if actual_num_nudges == 0:
        print("Not enough time to schedule any nudges.")
        return

    actual_interval = total_interval / actual_num_nudges

    for i in range(actual_num_nudges):
        next_nudge_time = current_time + timedelta(minutes=(i + 1) * actual_interval)
        print(f"Scheduling nudge {i+1} at {next_nudge_time}")
        task_data = task_data._replace(next_run_time=next_nudge_time.isoformat())

        schedule_nudge(task_data)


def handle_due_date_update(
    task_data: TaskData, user: User, periodic_task_id: str
) -> None:
    """Updates the due date and modifies the periodic task accordingly. Also creates a new
    NudgieTask for the next due date.
    """
    new_due_date = calculate_due_date_from_crontab(task_data.crontab, user)
    task_data = task_data._replace(
        due_date=new_due_date.isoformat(),
        next_run_time=get_next_run_time_from_crontab(
            task_data.crontab,
            user,
        ).isoformat(),
    )

    modify_periodic_task(periodic_task_id, task_data)
    # create a new NudgieTask for the next due date
    create_nudgie_task(task_data._replace(due_date=new_due_date.isoformat()))


@shared_task
def handle_reminder(periodic_task_id):
    """If the task for the scheduled reminder hasn't yet been completed, sends a reminder and generates nudges
    for the reminder. Also updates the due date and updates the PeriodicTask accordingly, as well as creating
    a new NudgieTask."""
    task_data = get_periodic_task_data(periodic_task_id)
    print(
        f"handling reminder for task {task_data.task_name} due on {task_data.due_date}"
    )

    user = User.objects.get(id=task_data.user_id)
    nudgie_task = get_nudgie_task(
        task_data.task_name,
        task_data.user_id,
        datetime.fromisoformat(task_data.due_date),
    )

    # retrieve task data to use for triggering reminder (and for updating the due date)
    if not nudgie_task.completed:
        print("task incomplete, sending reminder")
        generate_and_send_reminder(user, task_data)
        generate_nudges(user, task_data)

    handle_due_date_update(task_data, user, periodic_task_id)
