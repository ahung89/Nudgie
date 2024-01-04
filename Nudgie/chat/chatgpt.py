import json
import logging
from typing import Optional

import openai
from django.contrib.auth.models import User
from django.core.serializers import serialize
from django.db.models import Min

from Nudgie.chat.dialogue import load_conversation, save_line_of_speech
from Nudgie.config.chatgpt_inputs import (
    CHAT_GPT_MODEL,
    CLARIFICATION_PROMPT,
    DEADLINE_MISSED_PROMPT,
    GOAL_COMPLETION_FRAGMENT,
    INITIAL_CONVO_FUNCTIONS,
    INITIAL_CONVO_SYSTEM_PROMPT,
    NUDGE_PROMPT,
    ONGOING_CONVO_FUNCTIONS,
    REMINDER_PROMPT,
    STANDARD_SYSTEM_PROMPT,
    SUCCESSFUL_TASK_IDENTIFICATION_PROMPT,
    TASK_IDENTIFICATION_PROMPT,
)
from Nudgie.constants import (
    CHATGPT_ASSISTANT_ROLE,
    CHATGPT_COMPLETE_TASK_FUNCTION,
    CHATGPT_CONTENT_KEY,
    CHATGPT_DEFAULT_FUNCTION_SUCCESS_MESSAGE,
    CHATGPT_FUNCTION_CALL_KEY,
    CHATGPT_FUNCTION_NAME_KEY,
    CHATGPT_FUNCTION_ROLE,
    CHATGPT_GOAL_LENGTH_DAYS,
    CHATGPT_GOAL_NAME_KEY,
    CHATGPT_INITIAL_GOAL_SETUP,
    CHATGPT_ROLE_KEY,
    CHATGPT_SCHEDULES_KEY,
    CHATGPT_SYSTEM_ROLE,
    CHATGPT_USER_ROLE,
    DIALOGUE_TYPE_AI_STANDARD,
    DIALOGUE_TYPE_DEADLINE,
    DIALOGUE_TYPE_GOAL_END,
    DIALOGUE_TYPE_NUDGE,
    DIALOGUE_TYPE_REMINDER,
    DIALOGUE_TYPE_SYSTEM_MESSAGE,
    DIALOGUE_TYPE_USER_INPUT,
    NUDGIE_TASK_DUE_DATE_FIELD,
    NUDGIE_TASK_TASK_NAME_FIELD,
    OPENAI_FUNCTIONS_FIELD,
    OPENAI_MESSAGE_FIELD,
    OPENAI_MODEL_FIELD,
    PENDING_TASKS_KEY,
    REMINDER_DATA_AI_STRUCT_KEY,
    TASK_IDENTIFICATION_CERTAINTY_SCORE,
    TASK_IDENTIFICATION_NUDGIE_TASK_ID,
    TASK_IDENTIFICATION_REASONING,
)
from Nudgie.goals.goals import create_goal
from Nudgie.models import Goal, NudgieTask
from Nudgie.scheduling.periodic_task_helper import TaskData
from Nudgie.scheduling.scheduler import (
    schedule_goal_end,
    schedule_tasks_from_crontab_list,
)
from Nudgie.time_utils.time import (
    date_to_crontab,
    get_next_run_time_from_crontab,
    get_time,
)

# __name__ is the name of the current module, automatically set by Python.
logger = logging.getLogger(__name__)
client = openai.OpenAI()


def has_function_call(response) -> bool:
    """
    Determines whether the response from the OpenAI API contains a function call.
    """
    return (
        hasattr(response, CHATGPT_FUNCTION_CALL_KEY)
        and response.function_call is not None
    )


def generate_chat_gpt_message(
    role: str,
    content: str,
    user: Optional[User],
    dialogue_type: Optional[str],
    save_conversation: bool = True,
    messages: Optional[list] = None,
) -> dict:
    """
    Generates a message for the ChatGPT API.
    """
    if save_conversation:
        save_line_of_speech(user, role, dialogue_type, content)
    message = {
        CHATGPT_ROLE_KEY: role,
        CHATGPT_CONTENT_KEY: content,
    }

    if messages is not None:
        messages.append(message)

    return message


def generate_chatgpt_function_success_message(
    function_name: str,
    user: Optional[User],
    save_conversation: bool = False,
    messages: Optional[list] = None,
) -> str:
    """
    Generates a success message for a function call.
    """
    message = generate_chat_gpt_message(
        CHATGPT_FUNCTION_ROLE,
        CHATGPT_DEFAULT_FUNCTION_SUCCESS_MESSAGE,
        DIALOGUE_TYPE_SYSTEM_MESSAGE,
        save_conversation,
        False,
    )

    message[CHATGPT_FUNCTION_NAME_KEY] = function_name

    if messages is not None:
        messages.append(message)

    return message


def handle_goal_creation(user: User, goal_name: str, goal_length_days: int) -> None:
    """Create goal and schedule event for goal end"""
    goal = create_goal(
        user=user, goal_name=goal_name, goal_length_days=goal_length_days
    )
    crontab = date_to_crontab(goal.goal_end_date)

    schedule_goal_end(
        TaskData(
            crontab=crontab,
            task_name="",  # special case. we only need the goal-related data.
            user_id=user.id,
            goal_name=goal_name,
            due_date=goal.goal_end_date.isoformat(),
            next_run_time=get_next_run_time_from_crontab(crontab, user).isoformat(),
            dialogue_type=DIALOGUE_TYPE_GOAL_END,
        )
    )


def handle_chatgpt_function_call(
    function_name: str, function_args: dict, user: User, messages: list
):
    """
    Handles a function call from the OpenAI API, returns the response.
    """
    if function_name == CHATGPT_INITIAL_GOAL_SETUP:
        schedule_tasks_from_crontab_list(
            function_args[CHATGPT_SCHEDULES_KEY],
            function_args[CHATGPT_GOAL_NAME_KEY],
            user,
        )
        generate_chatgpt_function_success_message(
            CHATGPT_INITIAL_GOAL_SETUP, user, True, messages
        )
        handle_goal_creation(
            user,
            function_args[CHATGPT_GOAL_NAME_KEY],
            function_args[CHATGPT_GOAL_LENGTH_DAYS],
        )

        # Generate a response to the user based on the function call.
        return call_openai_api(messages)

    elif function_name == CHATGPT_COMPLETE_TASK_FUNCTION:
        certainty, identified_task, reasoning = identify_task(user.id, messages)
        if certainty == 1:
            # log the data point
            identified_task.completed = True
            identified_task.save()
            generate_chat_gpt_message(
                CHATGPT_USER_ROLE,
                SUCCESSFUL_TASK_IDENTIFICATION_PROMPT,
                user,
                DIALOGUE_TYPE_SYSTEM_MESSAGE,
                True,
                messages,
            )
            return call_openai_api(messages)
        else:
            generate_chat_gpt_message(
                CHATGPT_USER_ROLE,
                CLARIFICATION_PROMPT,
                user,
                DIALOGUE_TYPE_SYSTEM_MESSAGE,
                True,
                messages,
            )
            # confirm_task(identified_tasks, user, messages)
            return call_openai_api(messages, ONGOING_CONVO_FUNCTIONS)
    else:
        raise NotImplementedError(f"Function {function_name} is not implemented.")


def call_openai_api(messages: list[str], functions: Optional[list] = None):
    """
    Calls the OpenAI API and returns the response.
    """
    args = {OPENAI_MODEL_FIELD: CHAT_GPT_MODEL, OPENAI_MESSAGE_FIELD: messages}
    if functions is not None:
        args[OPENAI_FUNCTIONS_FIELD] = functions

    response = client.chat.completions.create(**args)
    return response.choices[0].message


def generate_reminder_text(task_data: TaskData) -> str:
    return REMINDER_PROMPT.format(
        task_name=task_data.task_name,
        goal_name=task_data.goal_name,
        reminder_notes=task_data.reminder_notes,
        due_date=task_data.due_date,
    )


def generate_deadline_missed_text(task_data: TaskData) -> str:
    return DEADLINE_MISSED_PROMPT.format(
        current_time=get_time(User.objects.get(id=task_data.user_id)).isoformat(),
        due_date=task_data.due_date,
        task_details=str(task_data),
    )


def generate_and_send_message_to_user(
    user: User, message: str, dialogue_type: str
) -> None:
    """
    Prompts ChatGPT to generate a reminder or a nudge, then sends it to the user.
    """
    messages = load_conversation(user)
    generate_chat_gpt_message(
        role=CHATGPT_USER_ROLE,
        content=message,
        user=user,
        dialogue_type=DIALOGUE_TYPE_SYSTEM_MESSAGE,
        save_conversation=True,
        messages=messages,
    )

    # Generate, package, and send the response.
    response_text = call_openai_api([get_system_message_standard(), *messages]).content
    generate_chat_gpt_message(
        role=CHATGPT_ASSISTANT_ROLE,
        content=response_text,
        user=user,
        dialogue_type=dialogue_type,
        save_conversation=True,
        messages=messages,
    )


def generate_and_send_reminder(user: User, task_data: TaskData) -> None:
    """
    Prompts ChatGPT to generate a reminder, then sends the reminder to the user.
    """
    generate_and_send_message_to_user(
        user, generate_reminder_text(task_data), DIALOGUE_TYPE_REMINDER
    )


def generate_and_send_nudge(user: User) -> None:
    """
    Prompts ChatGPT to generate a nudge, then sends the nudge to the user.
    """
    generate_and_send_message_to_user(user, NUDGE_PROMPT, DIALOGUE_TYPE_NUDGE)


def generate_and_send_deadline(task_data: TaskData) -> None:
    """
    Prompts ChatGPT to generate a deadline, then sends the deadline to the user.
    """
    generate_and_send_message_to_user(
        User.objects.get(id=task_data.user_id),
        generate_deadline_missed_text(task_data),
        DIALOGUE_TYPE_DEADLINE,
    )


def prepare_api_message(messages: list, has_nudgie_tasks: bool) -> list:
    """
    Prepares the messages to send to the OpenAI API.
    """
    api_messages = [
        get_system_message_standard()
        if has_nudgie_tasks
        else get_system_message_for_initial_convo()
    ]
    api_messages.extend(messages)

    return api_messages


def get_functions(has_nudgie_tasks: bool) -> str:
    """
    Selects the functions to pass to OpenAI.
    """
    return ONGOING_CONVO_FUNCTIONS if has_nudgie_tasks else INITIAL_CONVO_FUNCTIONS


def handle_convo(
    prompt,
    messages,
    user,
) -> str:
    """
    Calls OpenAI with the user's input and responds accordingly based on the AI's
    response. Returns the final output to display to the user.
    """

    # Generate message and prepare API call
    generate_chat_gpt_message(
        CHATGPT_USER_ROLE, prompt, user, DIALOGUE_TYPE_USER_INPUT, True, messages
    )

    has_nudgie_tasks = NudgieTask.objects.filter(user=user).exists()

    api_messages = prepare_api_message(messages, has_nudgie_tasks)

    response = call_openai_api(api_messages, get_functions(has_nudgie_tasks))

    # Handle function call, if necessary
    if has_function_call(response):
        response = handle_chatgpt_function_call(
            response.function_call.name,
            json.loads(response.function_call.arguments),
            user,
            messages,
        )

    # Generate final response to the user
    response_text = response.content
    generate_chat_gpt_message(
        CHATGPT_ASSISTANT_ROLE,
        response_text,
        user,
        DIALOGUE_TYPE_AI_STANDARD,
        True,
        messages,
    )

    return response_text


def get_system_message_for_initial_convo():
    """
    Generates a base message array which contains the system prompt for the goal
    creation conversation
    """
    return generate_chat_gpt_message(
        CHATGPT_SYSTEM_ROLE,
        INITIAL_CONVO_SYSTEM_PROMPT,
        None,
        DIALOGUE_TYPE_SYSTEM_MESSAGE,
        False,
    )


def get_decorated_system_message(message: str) -> str:
    """
    Decorates the system message with a goal completion fragment if any goals have been completed by
    the user in the past.
    """

    user_has_completed_goals = True  # TODO: implement logic

    return (
        message
        if not user_has_completed_goals
        else f"{message}\n\n{GOAL_COMPLETION_FRAGMENT.format(GOAL_LIST='', SUMMARY_OF_GOALS='')}"
    )


def get_system_message_standard():
    """
    Generates a base message array which contains the system prompt for all
    behavior outside of the goal creation conversation.
    """
    return generate_chat_gpt_message(
        CHATGPT_SYSTEM_ROLE,
        STANDARD_SYSTEM_PROMPT,
        None,
        DIALOGUE_TYPE_SYSTEM_MESSAGE,
        False,
    )


def get_task_identification_message(
    nudgie_tasks: list[NudgieTask], user: User, messages: list
):
    """
    Generates a message to prompt the AI to perform a task identification task.
    """
    return generate_chat_gpt_message(
        CHATGPT_USER_ROLE,
        TASK_IDENTIFICATION_PROMPT.format(
            **{PENDING_TASKS_KEY: serialize("json", nudgie_tasks)}
        ),
        user,
        DIALOGUE_TYPE_SYSTEM_MESSAGE,
        True,
        messages,
    )


def identify_task(user_id: str, messages: list) -> (float, list[NudgieTask]):
    user = User.objects.get(id=user_id)
    tasks = NudgieTask.objects.filter(
        user_id=user_id,
        completed=False,
        due_date__gt=get_time(user),
    )

    # If there are any tasks with the same task_name, remove whichever one has the greatest due_date.
    tasks = remove_duplicate_tasks(tasks)

    # If there's only one task, there's no need to perform complex task identification.
    if tasks.count() == 1:
        print("only one task, skipping chatGPT task identification task query")
        return 1, [tasks[0]], ""

    # Perform complex task identification using the AI
    get_task_identification_message(tasks, user, messages)
    response = call_openai_api(messages, ONGOING_CONVO_FUNCTIONS)
    print(f"response for task identification: {response.content}")

    # Make the AI aware that it already executed the function call.
    save_line_of_speech(
        user, CHATGPT_ASSISTANT_ROLE, DIALOGUE_TYPE_SYSTEM_MESSAGE, response.content
    )
    messages.append(
        {
            CHATGPT_ROLE_KEY: CHATGPT_ASSISTANT_ROLE,
            CHATGPT_CONTENT_KEY: response.content,
        }
    )

    identification_result = json.loads(response.content)

    return (
        identification_result[TASK_IDENTIFICATION_CERTAINTY_SCORE],
        next(
            (
                task
                for task in tasks
                if task.id == identification_result[TASK_IDENTIFICATION_NUDGIE_TASK_ID]
            ),
            None,
        ),
        identification_result[TASK_IDENTIFICATION_REASONING],
    )


def remove_duplicate_tasks(tasks):
    # Annotate each task_name with the earliest due_date
    min_dates = tasks.values(NUDGIE_TASK_TASK_NAME_FIELD).annotate(
        min_due_date=Min(NUDGIE_TASK_DUE_DATE_FIELD)
    )

    task_ids_to_keep = []

    for item in min_dates:
        task = tasks.get(
            task_name=item[NUDGIE_TASK_TASK_NAME_FIELD], due_date=item["min_due_date"]
        )
        task_ids_to_keep.append(task.id)

    return tasks.filter(id__in=task_ids_to_keep)
