from celery import Celery

app = Celery('tasks', broker='pyamqp://guest@localhost//', backend='rpc://')

@app.task(queue="nudgie")
def add(x, y):
    return x + y