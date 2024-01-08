import json
from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.forms import model_to_dict
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django_celery_beat.models import CrontabSchedule, PeriodicTask

from Nudgie.chat.dialogue import load_conversation
from Nudgie.scheduling.periodic_task_helper import get_periodic_task_data
from Nudgie.time_utils.time import get_next_run_time_from_crontab, get_time, set_time

from .chat.chatgpt import handle_convo
from .constants import (
    CELERY_BACKEND_CLEANUP_TASK,
    CHATBOT_CONVERSATION_FIELD,
    CHATBOT_TEMPLATE_NAME,
    CHATBOT_TEMPLATE_SERVER_TIME_FIELD,
    CHATBOT_TEMPLATE_TASKS_FIELD,
    CHATBOT_URL_PATH,
    CONVERSATION_FRAGMENT_CONVERSATION_FIELD,
    CONVERSATION_FRAGMENT_TEMPLATE_NAME,
    DIALOGUE_TYPE_DEADLINE,
    DIALOGUE_TYPE_GOAL_END,
    DIALOGUE_TYPE_NUDGE,
    DIALOGUE_TYPE_REMINDER,
    MESSAGE_FIELD,
    PERIODIC_TASK_ID_FIELD,
    PERIODIC_TASK_NEXT_RUNTIME_FIELD,
    PERIODIC_TASK_USER_ID,
    POST,
    QUEUE_NAME,
    SEND_TYPE_ASSISTANT,
    SENDER_MESSAGE,
    TASKLIST_FRAGMENT_SERVER_TIME_FIELD,
    TASKLIST_FRAGMENT_TASKS_FIELD,
    TASKLIST_FRAGMENT_TEMPLATE_NAME,
    TEST_FAST_FORWARD_SECONDS,
    USER_INPUT_MESSAGE_FIELD,
    UTF_8,
)
from .models import CachedApiResponse, Conversation, Goal, MockedTime, NudgieTask
from .tasks import deadline_handler, goal_end_handler, handle_nudge, handle_reminder


def get_task_list_with_next_run(user: User):
    """helper view for getting list of PeriodicTasks for the test tool"""
    tasks = sorted(
        PeriodicTask.objects.exclude(task=CELERY_BACKEND_CLEANUP_TASK),
        key=lambda task: datetime.fromisoformat(
            json.loads(task.kwargs)[PERIODIC_TASK_NEXT_RUNTIME_FIELD]
        ),
    )

    return [{**model_to_dict(task)} for task in tasks]


def chatbot_view(request):
    """The main view for the chatbot - displays a chat window as well as some controls."""
    convo = load_conversation(request.user)

    # for testing tool
    tasks = get_task_list_with_next_run(request.user)

    return render(
        request,
        CHATBOT_TEMPLATE_NAME,
        {
            CHATBOT_CONVERSATION_FIELD: convo,
            CHATBOT_TEMPLATE_SERVER_TIME_FIELD: get_time(request.user).isoformat(),
            CHATBOT_TEMPLATE_TASKS_FIELD: tasks,
        },
    )


def get_conversation_display(request):
    """Contents of the conversation window (shows all of the things that have been said so far)"""
    return render(
        request,
        CONVERSATION_FRAGMENT_TEMPLATE_NAME,
        {CONVERSATION_FRAGMENT_CONVERSATION_FIELD: load_conversation(request.user)},
    )


def get_task_list_display(request):
    """Retrieves task list for display in the sidebar"""
    return render(
        request,
        TASKLIST_FRAGMENT_TEMPLATE_NAME,
        {
            TASKLIST_FRAGMENT_TASKS_FIELD: get_task_list_with_next_run(request.user),
            TASKLIST_FRAGMENT_SERVER_TIME_FIELD: get_time(request.user).isoformat(),
        },
    )


def fast_forward(target_time: datetime, user: User):
    """
    Fast forward the system time to the target time. This is for testing purposes only.
    """
    target_time += timedelta(seconds=TEST_FAST_FORWARD_SECONDS)
    print(f"FAST FORWARDING TO {target_time=}. {get_time(user)=}")
    set_time(user, target_time)


def trigger_task(request: HttpRequest) -> HttpResponse:
    """
    This is the API for triggering a task. It is for testing purposes only.
    """
    task_id = json.loads(request.body.decode(UTF_8))[PERIODIC_TASK_ID_FIELD]
    task_data = get_periodic_task_data(task_id)

    crontab = task_data.crontab
    fast_forward(
        datetime.fromisoformat(task_data.next_run_time),
        request.user,
    )

    if task_data.dialogue_type == DIALOGUE_TYPE_REMINDER:
        result = handle_reminder.apply_async(
            args=(
                task_id,
            ),  # you MUST have the comma after the id or else it won't be treated as a tuple
            queue=QUEUE_NAME,
        ).get()
    elif task_data.dialogue_type == DIALOGUE_TYPE_NUDGE:
        result = handle_nudge.apply_async(
            args=(task_id,),
            queue=QUEUE_NAME,
        ).get()
    elif task_data.dialogue_type == DIALOGUE_TYPE_DEADLINE:
        result = deadline_handler.apply_async(
            args=(task_id,),
            queue=QUEUE_NAME,
        ).get()
    elif task_data.dialogue_type == DIALOGUE_TYPE_GOAL_END:
        result = goal_end_handler.apply_async(
            args=(task_id,),
            queue=QUEUE_NAME,
        ).get()

    print(f"RESULT OF TASK TRIGGER: {result}")

    return HttpResponse(status=204)


# for the initial conversation flow
def chatbot_api(request):
    """Handles all of the chat messages sent by the user."""
    if request.method == POST:
        data = json.loads(request.body.decode(UTF_8))
        user_input = data.get(USER_INPUT_MESSAGE_FIELD)

        bot_response = handle_convo(
            user_input, load_conversation(request.user), request.user
        )

        return JsonResponse(
            {SENDER_MESSAGE: SEND_TYPE_ASSISTANT, MESSAGE_FIELD: bot_response}
        )


def reset_user_data(request):
    """Resets all of the user's data, including conversations, nudgie tasks, and periodic tasks. For easier testing."""
    Conversation.objects.filter(user=request.user).delete()
    NudgieTask.objects.filter(user=request.user).delete()
    # PeriodicTask.objects.filter(name__startswith=f"{request.user.id}").delete()
    PeriodicTask.objects.filter(
        kwargs__contains=f'"{PERIODIC_TASK_USER_ID}": {request.user.id}'
    ).delete()
    Goal.objects.filter(user=request.user).delete()
    CrontabSchedule.objects.exclude(periodictask__isnull=False).delete()
    MockedTime.objects.filter(user=request.user).delete()

    return HttpResponseRedirect(CHATBOT_URL_PATH)


def clear_cache(request):
    """Clears all of the cached API responses."""
    CachedApiResponse.objects.all().delete()

    return HttpResponseRedirect(CHATBOT_URL_PATH)


# TODO: get rid of this soon, was just to test the celery beat integration.
def schedule_task(request):
    message = ""
    if request.method == "POST":
        schedule_time_str = request.POST.get("schedule_time")
        # the second argument means to display the date in the format of YYYY-MM-DDTHH:MM,
        # where T is the separator between date and time... for example 2021-07-01T12:00
        # T stands for time, and it's the ISO 8601 standard for datetime formatting
        schedule_time = datetime.strptime(schedule_time_str, "%Y-%m-%dT%H:%M")

        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute=schedule_time.minute,
            hour=schedule_time.hour,
            day_of_week="*",
            day_of_month=schedule_time.day,
            month_of_year=schedule_time.month,
        )

        PeriodicTask.objects.create(
            crontab=schedule,
            name=request.user.username + "Notification at " + str(schedule_time),
            task="Nudgie.tasks.notify",
            args=json.dumps(
                ["Task scheduled for " + str(schedule_time) + " completed"]
            ),
            queue="nudgie",
        )

        message = f"Task scheduled for {schedule_time}"

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return render(
        request, "schedule.html", {"message": message, "current_time": current_time}
    )
