import openai
import json
from Nudgie.util.reminder_scheduler import schedule_tasks_from_crontab_list
from Nudgie.config.chatgpt_inputs import (INITIAL_CONVO_FUNCTIONS, 
                                          INITIAL_CONVO_SYSTEM_PROMPT,
                                          STANDARD_SYSTEM_PROMPT,
                                          ONGOING_CONVO_FUNCTIONS,
                                          CHAT_GPT_MODEL)

def handle_convo(prompt, messages, user, has_nudgie_tasks):
    messages.append({'role': 'user', 'content': prompt})
    api_messages = [get_system_message_standard() if has_nudgie_tasks
                        else get_system_message_for_initial_convo()]
    api_messages.extend(messages)
    response = openai.ChatCompletion.create(
        model=CHAT_GPT_MODEL, 
        messages=api_messages,
        functions=ONGOING_CONVO_FUNCTIONS if has_nudgie_tasks else INITIAL_CONVO_FUNCTIONS
    )

    if 'function_call' in response.choices[0].message:
        schedule_tasks_from_crontab_list(json.loads(response.choices[0].message.
                                                    function_call.arguments)['schedules'],
                                                      user)
        messages.append({
            'role': 'function',
            'name': 'register_notifications',
            'content': 'Success.'
        })
        response = openai.ChatCompletion.create(
            model=CHAT_GPT_MODEL, messages=messages, functions=INITIAL_CONVO_FUNCTIONS
        )


    responseText = response.choices[0].message.content
    messages.append({'role': 'assistant', 'content': responseText})
    return responseText

def get_system_message_for_initial_convo():
    '''
    Generates a base message array which contains the system prompt for the goal
    creation conversation
    '''
    return {'role': 'system', 'content': INITIAL_CONVO_SYSTEM_PROMPT}

def get_system_message_standard():
    '''
    Generates a base message array which contains the system prompt for all
    behavior outside of the goal creation conversation.
    '''
    return {'role': 'system', 'content': STANDARD_SYSTEM_PROMPT}