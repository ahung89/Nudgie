from datetime import datetime
import json
from django.shortcuts import render
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from .tasks import add

def add_numbers(request):
    result = None
    if request.method == 'POST':
        num1 = int(request.POST.get('num1'))
        num2 = int(request.POST.get('num2'))
        result = add.delay(num1, num2).get()
    
    return render(request, 'add.html', {'result': result})

def schedule_task(request):
    message = ''
    if request.method =='POST':
        schedule_time_str = request.POST.get('schedule_time')
        # the second argument means to display the date in the format of YYYY-MM-DDTHH:MM, 
        # where T is the separator between date and time... for example 2021-07-01T12:00
        # T stands for time, and it's the ISO 8601 standard for datetime formatting
        schedule_time = datetime.strptime(schedule_time_str, '%Y-%m-%dT%H:%M:%S')

        schedule, _ = IntervalSchedule.objects.get_or_create(every=10, period=IntervalSchedule.SECONDS)
        PeriodicTask.objects.create(interval=schedule, name='Notification at ' + 
                                     str(schedule_time), task='Nudgie.tasks.notify',
                                       args=json.dumps(['Task completed!']))
        
        message = f"Task scheduled for {schedule_time}"
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return render(request, 'schedule.html', {'message': message, 'current_time': current_time})
