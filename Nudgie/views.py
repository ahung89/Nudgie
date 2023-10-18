from datetime import datetime
import json
from django.forms import model_to_dict
import pytz
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django_celery_beat.models import PeriodicTask, CrontabSchedule
from django.contrib.auth.models import User
from requests import get

from Nudgie.util.reminder_scheduler import get_next_run_time
from Nudgie.util.time import get_time
from .tasks import add
from .integrations.chatgpt import handle_convo
from .models import Conversation, NudgieTask

def add_numbers(request):
    result = None
    if request.method == 'POST':
        num1 = int(request.POST.get('num1'))
        num2 = int(request.POST.get('num2'))
        result = add.delay(num1, num2).get()
    
    return render(request, 'add.html', {'result': result})

def get_task_list_with_next_run(user : User):
    """helper view for getting list of PeriodicTasks for the test tool"""
    tasks = PeriodicTask.objects.all().order_by('crontab__minute', 'crontab__hour', 'crontab__day_of_week')

    return [
        {
            **model_to_dict(task),
            'next_run_time': get_next_run_time(crontab_str = f"{task.crontab.minute} {task.crontab.hour} "
                                               f"{task.crontab.day_of_month} {task.crontab.month_of_year} "
                                               f"{task.crontab.day_of_week}",
                                               user = user)
        }
        for task in tasks
    ]

def chatbot_view(request):
    load_conversation(request)

    #for testing tool
    tasks = get_task_list_with_next_run(request.user)

    return render(request, 'chatbot.html', {
        'conversation': request.session['conversation'],
        'server_time': get_time(request.user).strftime('%Y-%m-%d %H:%M:%S'),
        'tasks': tasks
    })

def load_conversation(request):
    #check if the convo is in the request session
    if 'conversation' not in request.session:
        lines = Conversation.objects.filter(user=request.user).order_by('timestamp') 
        convo = [{"role": line.message_type,
                        "content": line.content} for line in lines]
        request.session['conversation'] = convo

def get_task_list_display(request):
    return render(request, 'task_list_fragment.html',
                   {'tasks': get_task_list_with_next_run(request.user),
                    'server_time': get_time(request.user).strftime('%Y-%m-%d %H:%M:%S')})

#for the initial conversation flow
def chatbot_api(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        user_input = data.get('message')
        datetime_str = data.get('datetime')

        # get the passed-in datetime into the same form as the date in the NudgieTask
        # this passed-in datetime is the user-side time. don't replace it with the mocked value for the
        # server time since this simulates what the user sends in when he texts.
        naive_datetime = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S")
        print(naive_datetime)
        my_timezone = pytz.timezone('UTC')  # Replace with your time zone
        aware_datetime = my_timezone.localize(naive_datetime)
        formatted_datetime = aware_datetime.strftime('%Y-%m-%dT%H:%M:%S')
        print(formatted_datetime)

        print(f"RECEIVED INPUT. User input: {user_input}")
        load_conversation(request)
        convo = request.session['conversation']

        #determine which flow to use
        has_nudgie_tasks = NudgieTask.objects.filter(user=request.user).exists()
        print(f"HAS NUDGIE TASKS? {has_nudgie_tasks}")

        bot_response = handle_convo(user_input, convo, request.user, has_nudgie_tasks)

        user_convo_entry = Conversation(user=request.user, message_type='user',
                                         content=user_input)
        ai_convo_entry = Conversation(user=request.user, message_type='assistant',
                                       content=bot_response)

        user_convo_entry.save()
        ai_convo_entry.save()
        request.session['conversation'] = convo

        return JsonResponse({
            'sender': 'assistant',
            'message': bot_response
        })

def reset_user_data(request):
    request.session['conversation'] = []
    Conversation.objects.filter(user=request.user).delete()
    NudgieTask.objects.filter(user=request.user).delete()
    PeriodicTask.objects.filter(name__startswith=f'{request.user.id}').delete()
    CrontabSchedule.objects.exclude(periodictask__isnull=False).delete()

    return HttpResponseRedirect('/chatbot')

# TODO: get rid of this soon, was just to test the celery beat integration.
def schedule_task(request):
    message = ''
    if request.method =='POST':
        schedule_time_str = request.POST.get('schedule_time')
        # the second argument means to display the date in the format of YYYY-MM-DDTHH:MM, 
        # where T is the separator between date and time... for example 2021-07-01T12:00
        # T stands for time, and it's the ISO 8601 standard for datetime formatting
        schedule_time = datetime.strptime(schedule_time_str, '%Y-%m-%dT%H:%M')

        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute=schedule_time.minute,
            hour=schedule_time.hour,
            day_of_week='*',
            day_of_month=schedule_time.day,
            month_of_year=schedule_time.month,
        )

        PeriodicTask.objects.create(
            crontab=schedule,
            name=request.user.username + 'Notification at ' + str(schedule_time),
            task='Nudgie.tasks.notify',
            args=json.dumps(['Task scheduled for ' + str(schedule_time) + ' completed']),
            queue='nudgie'
        )
        
        message = f"Task scheduled for {schedule_time}"
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return render(request, 'schedule.html', {'message': message, 'current_time': current_time})
