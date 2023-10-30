QUEUE_NAME = "nudgie"

DIALOGUE_TYPE_REMINDER = "reminder"
DIALOGUE_TYPE_NUDGE = "nudge"
DIALOGUE_TYPE_USER_INPUT = "user_input"
DIALOGUE_TYPE_SYSTEM_MESSAGE = "system_message"
DIALOGUE_TYPE_AI_STANDARD = "ai_standard"

NUDGE_HANDLER = "Nudgie.tasks.handle_nudge"
REMINDER_HANDLER = "Nudgie.tasks.handle_reminder"

# ChatGPT notification scheduling object keys
REMINDER_DATA_AI_STRUCT_KEY = "reminder_data"
TASK_NAME_AI_STRUCT_KEY = "task_name"
GOAL_NAME_AI_STRUCT_KEY = "goal_name"
REMINDER_NOTES_AI_STRUCT_KEY = "reminder_notes"
CRONTAB_AI_STRUCT_KEY = "crontab"

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
CHATGPT_REGISTER_NOTIFICATIONS_FUNCTION = "register_notifications"

OPENAI_MODEL_FIELD = "model"
OPENAI_MESSAGE_FIELD = "messages"
OPENAI_FUNCTIONS_FIELD = "functions"

# how many seconds to fast forward by when triggering a reminder for testing
TEST_FAST_FORWARD_SECONDS = 5
