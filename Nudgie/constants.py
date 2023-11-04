QUEUE_NAME = "nudgie"

DIALOGUE_TYPE_REMINDER = "reminder"
DIALOGUE_TYPE_NUDGE = "nudge"
DIALOGUE_TYPE_DEADLINE = "deadline"
DIALOGUE_TYPE_USER_INPUT = "user_input"
DIALOGUE_TYPE_SYSTEM_MESSAGE = "system_message"
DIALOGUE_TYPE_AI_STANDARD = "ai_standard"

NUDGE_HANDLER = "Nudgie.tasks.handle_nudge"
REMINDER_HANDLER = "Nudgie.tasks.handle_reminder"
DEADLINE_HANDLER = "Nudgie.tasks.deadline_handler"

# ChatGPT notification scheduling object keys
REMINDER_DATA_AI_STRUCT_KEY = "reminder_data"
TASK_NAME_AI_STRUCT_KEY = "task_name"
GOAL_NAME_AI_STRUCT_KEY = "goal_name"
REMINDER_NOTES_AI_STRUCT_KEY = "reminder_notes"
CRONTAB_AI_STRUCT_KEY = "crontab"

# ChatGPT task identification message key
PENDING_TASKS_KEY = "PENDING_TASKS"

MAX_NUDGES_PER_REMINDER = 2
MIN_MINUTES_BETWEEN_NUDGES = 60  # minutes
MIN_TIME_BETWEEN_LAST_NUDGE_AND_DUE_DATE = 60  # minutes

# ChatGPT constants
CHATGPT_FUNCTION_CALL_KEY = "function_call"
CHATGPT_SCHEDULES_KEY = "schedules"
CHATGPT_ROLE_KEY = "role"
CHATGPT_CONTENT_KEY = "content"
CHATGPT_FUNCTION_NAME_KEY = "name"
CHATGPT_USER_ROLE = "user"
CHATGPT_ASSISTANT_ROLE = "assistant"
CHATGPT_SYSTEM_ROLE = "system"
CHATGPT_FUNCTION_ROLE = "function"

CHATGPT_DEFAULT_FUNCTION_SUCCESS_MESSAGE = "Success."

# Function names
CHATGPT_REGISTER_NOTIFICATIONS_FUNCTION = "register_notifications"
CHATGPT_COMPLETE_TASK_FUNCTION = "complete_task"

OPENAI_MODEL_FIELD = "model"
OPENAI_MESSAGE_FIELD = "messages"
OPENAI_FUNCTIONS_FIELD = "functions"

CRONTAB_FIELDS = ["minute", "hour", "day_of_week"]

# how many seconds to fast forward by when triggering a reminder for testing
TEST_FAST_FORWARD_SECONDS = 5

# Some of the periodic task fields (the ones which I need constants for right now)
PERIODIC_TASK_NEXT_RUNTIME_FIELD = "next_run_time"
PERIODIC_TASK_ID_FIELD = "periodic_task_id"
PERIODIC_TASK_USER_ID = "user_id"
PERIODIC_TASK_CRONTAB_FIELD = "crontab"

# Constants for the testing tool
CELERY_BACKEND_CLEANUP_TASK = "celery.backend_cleanup"

CHATBOT_TEMPLATE_NAME = "chatbot.html"
CHATBOT_CONVERSATION_FIELD = "conversation"
CHATBOT_TEMPLATE_SERVER_TIME_FIELD = "server_time"
CHATBOT_TEMPLATE_TASKS_FIELD = "tasks"
CONVERSATION_FRAGMENT_TEMPLATE_NAME = "conversation_fragment.html"
CONVERSATION_FRAGMENT_CONVERSATION_FIELD = "conversation"
TASKLIST_FRAGMENT_TEMPLATE_NAME = "task_list_fragment.html"
TASKLIST_FRAGMENT_TASKS_FIELD = "tasks"
TASKLIST_FRAGMENT_SERVER_TIME_FIELD = "server_time"
USER_INPUT_MESSAGE_FIELD = "message"
SENDER_MESSAGE = "sender"
SEND_TYPE_ASSISTANT = "assistant"
MESSAGE_FIELD = "message"
UTF_8 = "utf-8"

TIMEZONE_UTC = "UTC"
CHATBOT_URL_PATH = "/chatbot"

# Task Identification API Constants
TASK_IDENTIFICATION_CERTAINTY_SCORE = "certainty_score"
TASK_IDENTIFICATION_REASONING = "reasoning"

POST = "POST"
