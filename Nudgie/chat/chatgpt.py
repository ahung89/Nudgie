import openai
import json
from django.contrib.auth.models import User
from typing import Optional
from Nudgie.models import Conversation
from Nudgie.chat.dialogue import load_conversation
from Nudgie.scheduling.scheduler import schedule_tasks_from_crontab_list
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
) -> dict:
    """
    Generates a message for the ChatGPT API.
    """
    if save_conversation:
        message = Conversation(
            user=user, message_type=role, dialogue_type=dialogue_type, content=content
        )
        message.save()
    return {
        CHATGPT_ROLE_KEY: role,
        CHATGPT_CONTENT_KEY: content,
    }


def generate_chatgpt_function_success_message(function_name: str) -> str:
    """
    Generates a success message for a function call.
    """
    return {
        CHATGPT_ROLE_KEY: CHATGPT_FUNCTION_ROLE,
        CHATGPT_FUNCTION_NAME_KEY: function_name,
        CHATGPT_CONTENT_KEY: CHATGPT_DEFAULT_FUNCTION_SUCCESS_MESSAGE,
    }


def handle_function_call(function_name: str, function_args: dict, user):
    """
    Handles a function call from the OpenAI API.
    """
    if function_name == CHATGPT_REGISTER_NOTIFICATIONS_FUNCTION:
        schedule_tasks_from_crontab_list(
            json.loads(function_args[CHATGPT_SCHEDULES_KEY]),
            user,
        )
    else:
        raise NotImplementedError(
            f"Function {function_name} is not implemented in ChatGPT."
        )


def call_openai_api(messages: list[str], functions: list):
    """
    Calls the OpenAI API and returns the response.
    """
    response = openai.ChatCompletion.create(
        model=CHAT_GPT_MODEL, messages=messages, functions=functions
    )
    return response.choices[0].message


def trigger_reminder(user, task_data):
    message_content = REMINDER_PROMPT.format(
        task_name=task_data.task_name,
        goal_name=task_data.goal_name,
        reminder_notes=task_data.reminder_notes,
        due_date=task_data.due_date,
    )
    messages = load_conversation(user) + generate_chat_gpt_standard_message(
        CHATGPT_USER_ROLE, message_content, user, DIALOGUE_TYPE_USER_INPUT, True
    )
    api_messages = [get_system_message_standard(), *messages]

    response_text = call_openai_api(api_messages, ONGOING_CONVO_FUNCTIONS).content
    messages.append(
        generate_chat_gpt_standard_message(
            CHATGPT_ASSISTANT_ROLE, response_text, user, DIALOGUE_TYPE_REMINDER, True
        )
    )


def trigger_nudge(user):
    messages = load_conversation(user) + [{"role": "user", "content": NUDGE_PROMPT}]
    api_messages = [get_system_message_standard(), *messages]
    print(f"API MESSAGES: {api_messages}")

    response = call_openai_api(api_messages, ONGOING_CONVO_FUNCTIONS)
    response_text = response.content
    messages.append({"role": "assistant", "content": response_text})

    system_prompt = Conversation(user=user, message_type="user", content=NUDGE_PROMPT)
    system_prompt.save()  # just for debugging

    reminder_text = Conversation(
        user=user, message_type="assistant", content=response_text
    )
    reminder_text.save()

    print(f"MESSAGES: {messages}")
    print("RESPONSE TEXT FOR GENERATED NUDGE: ", response_text)

    return None


def handle_convo(prompt, messages, user, has_nudgie_tasks) -> str:
    """
    Calls OpenAI with the user's input and responds accordingly based on the AI's
    response. Returns the final output to display to the user.
    """
    messages.append(generate_chat_gpt_standard_message(CHATGPT_USER_ROLE, prompt))
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

    if has_function_call(response):
        handle_function_call(
            response.function_call.function,
            json.loads(response.function_call.arguments),
            user,
        )
        messages.append(
            generate_chatgpt_function_success_message(
                CHATGPT_REGISTER_NOTIFICATIONS_FUNCTION
            )
        )
        # Generate a response to the user based on the function call.
        response = call_openai_api(messages, INITIAL_CONVO_FUNCTIONS)

    response_text = response.content
    messages.append(
        generate_chat_gpt_standard_message(CHATGPT_ASSISTANT_ROLE, response_text)
    )
    return response_text


def get_system_message_for_initial_convo():
    """
    Generates a base message array which contains the system prompt for the goal
    creation conversation
    """
    return generate_chat_gpt_standard_message(
        CHATGPT_SYSTEM_ROLE, INITIAL_CONVO_SYSTEM_PROMPT
    )


def get_system_message_standard():
    """
    Generates a base message array which contains the system prompt for all
    behavior outside of the goal creation conversation.
    """
    return generate_chat_gpt_standard_message(
        CHATGPT_SYSTEM_ROLE, STANDARD_SYSTEM_PROMPT
    )
