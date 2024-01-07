"""
This file handles all functionality related to designing the AI's system prompt.
"""

from django.contrib.auth.models import User
from httpx import get

from Nudgie.config.chatgpt_inputs import (
    GOAL_COMPLETION_FRAGMENT,
    INITIAL_CONVO_SYSTEM_PROMPT,
    STANDARD_SYSTEM_PROMPT,
    TIME_REMAINING_FRAGMENT,
)
from Nudgie.constants import GOAL_END_DATE_FIELD
from Nudgie.goals.goals import get_current_goal
from Nudgie.models import Goal
from Nudgie.time_utils.time import get_time


def add_goal_completion_info(func) :
    """
    Decorates the system message with a goal completion fragment if any goals have been completed by
    the user in the past. This way, the AI can draw on knowledge of the user's performance on past goals
    in order to make better-informed messages.
    """
    def wrapper(user: User) -> str:
        message = func(user)
        user_has_completed_goals = Goal.objects.filter(
            goal_end_date__lt=get_time(user)
        ).exists()

        print(f"{user_has_completed_goals=}")

        return (
            message
            if not user_has_completed_goals
            else f"{message}\n\n{GOAL_COMPLETION_FRAGMENT.format(GOAL_LIST='', SUMMARY_OF_GOALS='')}"
        )
    return wrapper


def append_remaining_time_info(func) :
    """
    Pulls the upcoming goal from the DB and checks how much time remains between now and the goal's end date. Then
    appends this to the message by setting the appropriate fields (goal_end_date, current_time, hours_remaining, minutes_remaining,
    and seconds_remaining) on the TIME_REMAINING_FRAGMENT template string.
    """
    def wrapper(user: User) -> str:
        message = func(user)
        curr_time = get_time(user)

        goal = get_current_goal(user)

        remaining_time = goal.goal_end_date - curr_time
        days = remaining_time.days
        hours, remainder = divmod(remaining_time.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        return f"{message}\n\n{TIME_REMAINING_FRAGMENT.format(
            goal_end_date=goal.goal_end_date.isoformat(),
            current_time=get_time(user).isoformat(),
            days_remaining=days,
            hours_remaining=hours,
            minutes_remaining=minutes,
            seconds_remaining=seconds
        )}"
    
    return wrapper

@add_goal_completion_info
@append_remaining_time_info
def get_standard_system_prompt(user: User) -> str:
    """
    Get the system prompt for all behavior outside of the goal creation conversation.
    """
    return STANDARD_SYSTEM_PROMPT

@add_goal_completion_info
def get_initial_system_prompt(user: User) -> str:
    """
    Get the system prompt for the goal creation conversation.
    """
    return INITIAL_CONVO_SYSTEM_PROMPT



