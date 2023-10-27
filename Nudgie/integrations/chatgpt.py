import openai
import json
from Nudgie.models import Conversation
from Nudgie.util.dialogue import load_conversation
from Nudgie.util.reminder_scheduler import schedule_tasks_from_crontab_list
from Nudgie.config.chatgpt_inputs import (
    INITIAL_CONVO_FUNCTIONS,
    INITIAL_CONVO_SYSTEM_PROMPT,
    NUDGE_PROMPT,
    REMINDER_PROMPT,
    STANDARD_SYSTEM_PROMPT,
    ONGOING_CONVO_FUNCTIONS,
    CHAT_GPT_MODEL,
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
    print(f"REMINDER-TRIGGERING MESSAGE: {message_content}")
    messages = load_conversation(user) + [{"role": "user", "content": message_content}]
    api_messages = [get_system_message_standard(), *messages]
    print(f"API MESSAGES: {api_messages}")

    response = call_openai_api(api_messages, ONGOING_CONVO_FUNCTIONS)
    response_text = response.content
    messages.append({"role": "assistant", "content": response_text})

    system_prompt = Conversation(
        user=user, message_type="user", content=message_content
    )
    system_prompt.save()  # just for debugging

    reminder_text = Conversation(
        user=user,
        message_type="assistant",
        content=response_text,
        dialogue_type="reminder",
    )
    reminder_text.save()

    print(f"MESSAGES: {messages}")
    print("RESPONSE TEXT FOR GENERATED REMINDER: ", response_text)


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


def handle_convo(prompt, messages, user, has_nudgie_tasks):
    messages.append({"role": "user", "content": prompt})
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

    if "function_call" in response:
        schedule_tasks_from_crontab_list(
            json.loads(response.function_call.arguments)["schedules"],
            user,
        )
        messages.append(
            {
                "role": "function",
                "name": "register_notifications",
                "content": "Success.",
            }
        )
        response = call_openai_api(messages, INITIAL_CONVO_FUNCTIONS)

    response_text = response.content
    messages.append({"role": "assistant", "content": response_text})
    return response_text


def get_system_message_for_initial_convo():
    """
    Generates a base message array which contains the system prompt for the goal
    creation conversation
    """
    return {"role": "system", "content": INITIAL_CONVO_SYSTEM_PROMPT}


def get_system_message_standard():
    """
    Generates a base message array which contains the system prompt for all
    behavior outside of the goal creation conversation.
    """
    return {"role": "system", "content": STANDARD_SYSTEM_PROMPT}
