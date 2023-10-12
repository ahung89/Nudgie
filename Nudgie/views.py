from datetime import datetime
import json
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django_celery_beat.models import PeriodicTask, CrontabSchedule
from .tasks import add
from .integrations.chatgpt import get_goal_creation_base_message, goal_creation_convo
from django.core.cache import cache

def add_numbers(request):
    result = None
    if request.method == 'POST':
        num1 = int(request.POST.get('num1'))
        num2 = int(request.POST.get('num2'))
        result = add.delay(num1, num2).get()
    
    return render(request, 'add.html', {'result': result})

def chatbot_view(request):
    conversation = request.session.get('conversation', [])
    return render(request, 'chatbot.html', {'conversation': conversation})

#for the initial conversation flow
def chatbot_api(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        user_input = data.get('message')

        # api_messages = request.session.get('api_messages', get_goal_creation_base_message())
        api_messages = cache.get('api_messages', get_goal_creation_base_message())

        bot_response = goal_creation_convo(user_input, api_messages)

        # update the displayed conversation, save it to the session. the session persists
        # across requests and is cleared when the browser is closed.
        conversation = request.session.get('conversation', [])
        conversation.append({'sender': 'User', 'message' : user_input})        
        conversation.append({'sender': 'Bot', 'message' : bot_response})

        cache.set('conversation', conversation)
        #request.session['conversation'] = conversation

        cache.set('api_messages', api_messages)
        #request.session['api_messages'] = api_messages

        return JsonResponse({
            'sender': 'Bot',
            'message': bot_response
        })

def clear_chat():
    cache.clear()
    return HttpResponseRedirect('/chatbot')

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
            name='Notification at ' + str(schedule_time),
            task='Nudgie.tasks.notify',
            args=json.dumps(['Task scheduled for ' + str(schedule_time) + ' completed']),
            queue='nudgie'
        )
        
        message = f"Task scheduled for {schedule_time}"
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return render(request, 'schedule.html', {'message': message, 'current_time': current_time})
