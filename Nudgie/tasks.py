import json
from celery import shared_task

from Nudgie.util.reminder_scheduler import calculate_due_date
from Nudgie.integrations.chatgpt import trigger_nudge, trigger_reminder
from Nudgie.util.time import get_time
from .models import Conversation, NudgieTask
from django_celery_beat.models import PeriodicTask
from django.contrib.auth.models import User
from datetime import timedelta

MAX_NUDGES_PER_REMINDER = 2
MIN_MINUTES_BETWEEN_NUDGES = 60 #minutes

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
def handle_nudge(task_name, due_date, user_id):
    '''
    A nudge must know the due date, task name, and related notes/info. It must not
    fire off if the task has already been completed, or if the due date was missed.
    '''
    print(f"handling nudge for task {task_name} due on {due_date}")

    filtered_tasks = NudgieTask.objects.filter(task_name=task_name, due_date=due_date, user_id = user_id)
    user = User.objects.get(id = user_id)

    assert len(filtered_tasks) == 1, f"expected 1 task, got {len(filtered_tasks)}"

    ##only trigger the nudge if the task hasn't already been completed.
    #TODO: also check if the due date has passed.
    if not filtered_tasks[0].completed:
        print("task incomplete, sending nudge")
        #reminder message comes from the PeriodicTask kwargs. it's associated with the nudge.
        trigger_nudge(user)
        #TODO: deactivate nudge

def generate_nudges(due_time, user, task):
    current_time = get_time(user)
    total_interval = (due_time - current_time).total_seconds() / 60
    
    num_nudges_that_fit = int(total_interval // MIN_MINUTES_BETWEEN_NUDGES)
    actual_num_nudges = min(MAX_NUDGES_PER_REMINDER, num_nudges_that_fit)

    if actual_num_nudges == 0:
        print("Not enough time to schedule any nudges.")
        return

    actual_interval = total_interval / actual_num_nudges

    for i in range(actual_num_nudges):
        next_nudge_time = current_time + timedelta(minutes=(i + 1) * actual_interval)
        print(f"Scheduling nudge {i+1} at {next_nudge_time}")
        task_data = json.loads(task.kwargs)
        task_data['next_run_time'] = next_nudge_time.isoformat()
        task.kwargs = json.dumps(task_data)

        # schedule the nudge
        PeriodicTask.objects.create(
            crontab=task.crontab,
            name=str(user.id) + '_Nudge at ' + str(next_nudge_time.hour) + ':' + str(next_nudge_time.minute),
            task='Nudgie.tasks.handle_nudge',
            kwargs=json.dumps({**json.loads(task.kwargs), 'dialogue_type' : 'nudge'}),
            one_off=True,
            queue='nudgie'
        )

#TODO: refactor this
#TODO: Just pass in ID for periodic task and pull the rest of the info instead
#of passing in all the info individually
@shared_task
def handle_reminder(task_name, due_date, user_id, periodic_task_id):
    print(f"handling reminder for task {task_name} due on {due_date}")

    filtered_tasks = NudgieTask.objects.filter(task_name=task_name, due_date=due_date, user_id = user_id)
    user = User.objects.get(id = user_id)
    # all_tasks = NudgieTask.objects.filter(user = user)

    assert len(filtered_tasks) == 1, f"expected 1 task, got {len(filtered_tasks)}"
    
    print(f"periodic_task_id: {periodic_task_id}")
    #retrieve task data to use for triggering reminder (and for updating the due date)
    task = PeriodicTask.objects.get(id = periodic_task_id)
    task_data = json.loads(task.kwargs)

    if not filtered_tasks[0].completed:
        print("task incomplete, sending reminder")
        trigger_reminder(user, task_data)

    #calculate the next due-date and save it to the PeriodicTask
    crontab_schedule = task.crontab
    crontab_dict = {
        'minute': crontab_schedule.minute,
        'hour': crontab_schedule.hour,
        'day_of_week': crontab_schedule.day_of_week
    }
    
    new_due_date = calculate_due_date(crontab_dict, user)
    print(f'NEW DUE DATE: {new_due_date}')
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
    #Generate nudges.
    generate_nudges(new_due_date, user, task)

    return task_name