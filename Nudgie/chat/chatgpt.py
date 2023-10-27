import openai
import json
from django.contrib.auth.models import User
from typing import Optional
from Nudgie.models import Conversation
from Nudgie.chat.dialogue import load_conversation
from Nudgie.scheduling.scheduler import schedule_tasks_from_crontab_list
from Nudgie.scheduling.periodic_task_helper import TaskData
from Nudgie.config.chatgpt_inputs import (
    INITIAL_CONVO_FUNCTIONS,
    INITIAL_CONVO_SYSTEM_PROMPT,
    NUDGE_PROMPT,
    REMINDER_PROMPT,
    STANDARD_SYSTEM_PROMPT,
    ONGOING_CONVO_FUNCTIONS,
    CHAT_GPT_MODEL,
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
    DIALOGUE_TYPE_REMINDER,
    DIALOGUE_TYPE_USER_INPUT,
    DIALOGUE_TYPE_SYSTEM_MESSAGE,
    DIALOGUE_TYPE_NUDGE,
    DIALOGUE_TYPE_AI_STANDARD,
    OPENAI_MODEL_FIELD,
    OPENAI_MESSAGE_FIELD,
    OPENAI_FUNCTIONS_FIELD,
)


def has_function_call(response) -> bool:
    """
    Determines whether the response from the OpenAI API contains a function call.
    """
    return CHATGPT_FUNCTION_CALL_KEY in response


def generate_chat_gpt_standard_message(
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
        message = Conversation(
            user=user, message_type=role, dialogue_type=dialogue_type, content=content
        )
        message.save()
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
    message = generate_chat_gpt_standard_message(
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


def handle_chatgpt_function_call(function_name: str, function_args: dict, user):
    """
    Handles a function call from the OpenAI API.
    """
    if function_name == CHATGPT_REGISTER_NOTIFICATIONS_FUNCTION:
        schedule_tasks_from_crontab_list(
            function_args[CHATGPT_SCHEDULES_KEY],
            user,
        )
    else:
        raise NotImplementedError(
            f"Function {function_name} is not implemented in ChatGPT."
        )


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


def generate_and_send_reminder_or_nudge(
    user: User, message: str, is_nudge: bool
) -> None:
    """
    Prompts ChatGPT to generate a reminder or a nudge, then sends it to the user.
    """
    messages = load_conversation(user)
    generate_chat_gpt_standard_message(
        CHATGPT_USER_ROLE,
        message,
        user,
        DIALOGUE_TYPE_SYSTEM_MESSAGE,
        True,
        messages,
    )

    # Generate, package, and send the response.
    response_text = call_openai_api([get_system_message_standard(), *messages]).content
    generate_chat_gpt_standard_message(
        CHATGPT_ASSISTANT_ROLE,
        response_text,
        user,
        DIALOGUE_TYPE_NUDGE if is_nudge else DIALOGUE_TYPE_REMINDER,
        True,
        messages,
    )


def generate_and_send_reminder(user: User, task_data: TaskData) -> None:
    """
    Prompts ChatGPT to generate a reminder, then sends the reminder to the user.
    """
    generate_and_send_reminder_or_nudge(user, generate_reminder_text(task_data), False)


def generate_and_send_nudge(user: User) -> None:
    """
    Prompts ChatGPT to generate a nudge, then sends the nudge to the user.
    """
    generate_and_send_reminder_or_nudge(user, NUDGE_PROMPT, True)


def handle_convo(prompt, messages, user, has_nudgie_tasks) -> str:
    """
    Calls OpenAI with the user's input and responds accordingly based on the AI's
    response. Returns the final output to display to the user.
    """

    # Generate message and prepare API call
    generate_chat_gpt_standard_message(
        CHATGPT_USER_ROLE, prompt, user, DIALOGUE_TYPE_USER_INPUT, True, messages
    )
    api_messages = [
        get_system_message_standard()
        if has_nudgie_tasks
        else get_system_message_for_initial_convo()
    ]
    api_messages.extend(messages)

    response = call_openai_api(
        api_messages,
        ONGOING_CONVO_FUNCTIONS if has_nudgie_tasks else INITIAL_CONVO_FUNCTIONS,
    )

    # Handle function call, if necessary
    if has_function_call(response):
        handle_chatgpt_function_call(
            response.function_call.name,
            json.loads(response.function_call.arguments),
            user,
        )
        generate_chatgpt_function_success_message(
            CHATGPT_REGISTER_NOTIFICATIONS_FUNCTION, user, True, messages
        )
        # Generate a response to the user based on the function call.
        response = call_openai_api(messages, INITIAL_CONVO_FUNCTIONS)

    # Generate final response to the user
    response_text = response.content
    generate_chat_gpt_standard_message(
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
    return generate_chat_gpt_standard_message(
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
    return generate_chat_gpt_standard_message(
        CHATGPT_SYSTEM_ROLE,
        STANDARD_SYSTEM_PROMPT,
        None,
        DIALOGUE_TYPE_SYSTEM_MESSAGE,
        False,
    )
