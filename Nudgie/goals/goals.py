from datetime import timedelta

from django.contrib.auth.models import User

from Nudgie.models import Goal
from Nudgie.time_utils.time import get_time


def create_goal(user: User, goal_name: str, goal_length_days: int) -> Goal:
    """Creates a goal for the user."""
    curr_time = get_time(user)
    end_time = curr_time + timedelta(days=goal_length_days)
    print(
        f"CREATING GOAL FOR {user.username} - {goal_name=} - {goal_length_days=} - {curr_time=} - {end_time=}"
    )
    return Goal.objects.create(
        user=user,
        goal_name=goal_name,
        goal_start_date=curr_time,
        goal_end_date=end_time,
    )


def get_current_goal(user: User) -> Goal:
    """Returns the current goal for the user."""
    curr_time = get_time(user)
    return Goal.objects.filter(
        goal_start_date__lte=curr_time,
        goal_end_date__gte=curr_time,
        completed=False,
        failed=False,
    ).first()
