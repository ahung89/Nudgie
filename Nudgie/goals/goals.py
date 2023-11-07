from django.contrib.auth.models import User
from Nudgie.models import Goal
from Nudgie.time_utils.time import get_time
from datetime import timedelta


def create_goal(user: User, goal_name: str, goal_length_days: int) -> None:
    """Creates a goal for the user."""
    curr_time = get_time(user)
    end_time = curr_time + timedelta(days=goal_length_days)
    print(
        f"CREATING GOAL FOR {user.username} - {goal_name=} - {goal_length_days=} - {curr_time=} - {end_time=}"
    )
    Goal.objects.create(
        user=user,
        goal_name=goal_name,
        goal_start_date=curr_time,
        goal_end_date=end_time,
    )
