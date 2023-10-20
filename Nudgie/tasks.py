import json
from celery import shared_task

from Nudgie.util.reminder_scheduler import calculate_due_date
from .models import NudgieTask
from django_celery_beat.models import PeriodicTask
from django.contrib.auth.models import User

# for app.autodiscover_tasks() to work, you need to define a tasks.py file in each app. 
# that's why this file is here.
# in larger projects, you might have multiple apps, each with their own tasks.py file, each
# of which defines celery tasks.

# shared_task is different from app.task in that it doesn't require a celery app to be defined.
# this is so that it can be used in other apps. The thing is, reusable apps cannot depend
# on the project itself. So you can't import the celery app from the project.
@shared_task
def add(x, y):
    return x + y

@shared_task
def mul(x, y):
    return x * y

@shared_task
def xsum(numbers):
    return sum(numbers)

@shared_task
def notify(message):
    print(f"ATTENTION! {message}")
    return message

@shared_task
def handle_reminder(task_name, due_date, user_id, periodic_task_id):
    print(f"handling reminder for task {task_name} due on {due_date}")

    filtered_tasks = NudgieTask.objects.filter(task_name=task_name, due_date=due_date, user_id = user_id)
    # all_tasks = NudgieTask.objects.filter(user = user)

    assert len(filtered_tasks) == 1, f"expected 1 task, got {len(filtered_tasks)}"

    if not filtered_tasks[0].completed:
        print("task incomplete, sending reminder")

    #calculate the next due-date and save it to the PeriodicTask
    task = PeriodicTask.objects.get(id = periodic_task_id)
    crontab_schedule = task.crontab
    crontab_dict = {
        'minute': crontab_schedule.minute,
        'hour': crontab_schedule.hour,
        'day_of_week': crontab_schedule.day_of_week
    }
    
    user = User.objects.get(id = user_id)
    new_due_date = calculate_due_date(crontab_dict, user)

    print(f'NEW DUE DATE: {new_due_date}')

    task_data = json.loads(task.kwargs)
    task_data['due_date'] = new_due_date.isoformat()
    task.kwargs = json.dumps(task_data)

    task.save()

    #Create a new NudgieTask object with the new due date
    NudgieTask.objects.create(
        user = user,
        task_name = task_name,
        goal_name = task_data['goal_name'],
        due_date = new_due_date
    )

    return task_name