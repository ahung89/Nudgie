import json
from django_celery_beat.models import PeriodicTask


def get_periodic_task_data(id):
    task = PeriodicTask.objects.get(id=id)
    kwargs = json.loads(task.kwargs)
    return {**kwargs, "crontab": task.crontab}
