QUEUE_NAME = "nudgie"

DIALOGUE_TYPE_REMINDER = "reminder"
DIALOGUE_TYPE_NUDGE = "nudge"

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