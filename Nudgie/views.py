from datetime import datetime
import json
import re
from urllib import request
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django_celery_beat.models import PeriodicTask, CrontabSchedule
from .tasks import add
from .integrations.chatgpt import get_system_message, goal_creation_convo
from django.core.cache import cache
from .models import Conversation

def add_numbers(request):
    result = None
    if request.method == 'POST':
        num1 = int(request.POST.get('num1'))
        num2 = int(request.POST.get('num2'))
        result = add.delay(num1, num2).get()
    
    return render(request, 'add.html', {'result': result})

def chatbot_view(request):
    load_conversation(request)
    return render(request, 'chatbot.html', {'conversation': request.session['conversation']})

def load_conversation(request):
    #check if the convo is in the request session
    if 'conversation' not in request.session:
        lines = Conversation.objects.filter(user=request.user).order_by('timestamp') 
        convo = [{"role": line.message_type,
                        "content": line.content} for line in lines]
        request.session['conversation'] = convo

#for the initial conversation flow
def chatbot_api(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        user_input = data.get('message')

        print(f"RECEIVED INPUT. User input: {user_input}")
        load_conversation(request)
        convo = request.session['conversation']

        bot_response = goal_creation_convo(user_input, convo, request.user.id)

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

def clear_chat(request):
    #clear the conversation from the session
    request.session['conversation'] = []
    Conversation.objects.filter(user=request.user).delete()
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
            name='Notification at ' + str(schedule_time),
            task='Nudgie.tasks.notify',
            args=json.dumps(['Task scheduled for ' + str(schedule_time) + ' completed']),
            queue='nudgie'
        )
        
        message = f"Task scheduled for {schedule_time}"
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return render(request, 'schedule.html', {'message': message, 'current_time': current_time})
