import openai
import json
import logging
from django.contrib.auth.models import User
from django.core.serializers import serialize
from typing import Optional
from Nudgie.models import NudgieTask
from Nudgie.chat.dialogue import load_conversation, save_line_of_speech
from Nudgie.scheduling.scheduler import schedule_tasks_from_crontab_list
from Nudgie.scheduling.periodic_task_helper import TaskData
from Nudgie.config.chatgpt_inputs import (
    INITIAL_CONVO_FUNCTIONS,
    INITIAL_CONVO_SYSTEM_PROMPT,
    DEADLINE_MISSED_PROMPT,
    NUDGE_PROMPT,
    REMINDER_PROMPT,
    STANDARD_SYSTEM_PROMPT,
    ONGOING_CONVO_FUNCTIONS,
    CHAT_GPT_MODEL,
    TASK_IDENTIFICATION_PROMPT,
    SUCCESSFUL_TASK_IDENTIFICATION_PROMPT,
    CLARIFICATION_PROMPT,
)
from Nudgie.constants import (
    CHATGPT_FUNCTION_CALL_KEY,
    CHATGPT_SCHEDULES_KEY,
    CHATGPT_ROLE_KEY,
    CHATGPT_CONTENT_KEY,
    CHATGPT_FUNCTION_NAME_KEY,
    CHATGPT_USER_ROLE,
    CHATGPT_ASSISTANT_ROLE,
    CHATGPT_SYSTEM_ROLE,
    CHATGPT_FUNCTION_ROLE,
    CHATGPT_DEFAULT_FUNCTION_SUCCESS_MESSAGE,
    CHATGPT_REGISTER_NOTIFICATIONS_FUNCTION,
    CHATGPT_COMPLETE_TASK_FUNCTION,
    DIALOGUE_TYPE_REMINDER,
    DIALOGUE_TYPE_DEADLINE,
    DIALOGUE_TYPE_USER_INPUT,
    DIALOGUE_TYPE_SYSTEM_MESSAGE,
    DIALOGUE_TYPE_NUDGE,
    DIALOGUE_TYPE_AI_STANDARD,
    OPENAI_MODEL_FIELD,
    OPENAI_MESSAGE_FIELD,
    OPENAI_FUNCTIONS_FIELD,
    PENDING_TASKS_KEY,
    TASK_IDENTIFICATION_CERTAINTY_SCORE,
    TASK_IDENTIFICATION_REASONING,
)
from Nudgie.time_utils.time import get_time

# __name__ is the name of the current module, automatically set by Python.
logger = logging.getLogger(__name__)


def has_function_call(response) -> bool:
    """
    Determines whether the response from the OpenAI API contains a function call.
    """
    return CHATGPT_FUNCTION_CALL_KEY in response


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


def handle_chatgpt_function_call(
    function_name: str, function_args: dict, user: User, messages: list
):
    """
    Handles a function call from the OpenAI API, returns the response.
    """
    if function_name == CHATGPT_REGISTER_NOTIFICATIONS_FUNCTION:
        schedule_tasks_from_crontab_list(
            function_args[CHATGPT_SCHEDULES_KEY],
            user,
        )
        generate_chatgpt_function_success_message(
            CHATGPT_REGISTER_NOTIFICATIONS_FUNCTION, user, True, messages
        )
        # Generate a response to the user based on the function call.
        return call_openai_api(messages)

    elif function_name == CHATGPT_COMPLETE_TASK_FUNCTION:
        certainty, identified_tasks, reasoning = identify_task(user.id, messages)
        if certainty == 1 or len(identified_tasks) == 1:
            # log the data point
            identified_tasks[0].completed = True
            identified_tasks[0].save()
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

    response = openai.ChatCompletion.create(**args)
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


def handle_convo(prompt, messages, user, has_nudgie_tasks) -> str:
    """
    Calls OpenAI with the user's input and responds accordingly based on the AI's
    response. Returns the final output to display to the user.
    """

    # Generate message and prepare API call
    generate_chat_gpt_message(
        CHATGPT_USER_ROLE, prompt, user, DIALOGUE_TYPE_USER_INPUT, True, messages
    )
    api_messages = prepare_api_message(messages, has_nudgie_tasks)

    response = call_openai_api(
        api_messages,
        ONGOING_CONVO_FUNCTIONS if has_nudgie_tasks else INITIAL_CONVO_FUNCTIONS,
    )

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
        tasks,
        identification_result[TASK_IDENTIFICATION_REASONING],
    )
