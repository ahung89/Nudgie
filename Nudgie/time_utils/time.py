from datetime import datetime

import pytz
from croniter import croniter
from django.contrib.auth.models import User
from django_celery_beat.models import CrontabSchedule

from Nudgie.constants import TIMEZONE_UTC
from Nudgie.models import MockedTime

TESTING = True


def localize(dt: datetime):
    return pytz.timezone(TIMEZONE_UTC).localize(dt)


def get_time(user: User) -> datetime:
    if TESTING:
        # that second return value is a boolean that tells us whether or not the
        # object was created. It's not terribly useful here.
        try:
            mocked_time_obj = MockedTime.objects.get(user=user)
        except MockedTime.DoesNotExist:
            # Time hasn't been mocked yet - returning actual time.
            return localize(datetime(2024, 1, 5, 7, 0, 0))

        return mocked_time_obj.mocked_time
    else:
        return localize(datetime.now())


def set_time(user: User, new_time: datetime):
    mocked_time_obj, _ = MockedTime.objects.get_or_create(
        user=user, defaults={"mocked_time": new_time}
    )

    mocked_time_obj.mocked_time = new_time
    mocked_time_obj.save()

    print(f"SETTING MOCKED TIME: {mocked_time_obj.mocked_time}")

    return mocked_time_obj.mocked_time


def get_next_run_time(
    minute: int,
    hour: int,
    day_of_month: int,
    month_of_year: int,
    day_of_week: int,
    user: User,
) -> datetime:
    """Given a crontab object (key-val pairs), calculate the next due date for the task."""
    crontab_str = (
        f"{minute} {hour} " f"{day_of_month} {month_of_year} " f"{day_of_week}"
    )
    print(f"CRON_STR IS {crontab_str}")
    iter = croniter(crontab_str, get_time(user))
    next_run_time = iter.get_next(datetime)
    return next_run_time


def get_next_run_time_from_crontab(
    crontab_schedule: CrontabSchedule, user: User
) -> datetime:
    return get_next_run_time(
        crontab_schedule.minute,
        crontab_schedule.hour,
        crontab_schedule.day_of_month,
        crontab_schedule.month_of_year,
        crontab_schedule.day_of_week,
        user,
    )


def date_to_crontab(date: datetime) -> CrontabSchedule:
    """Converts a datetime object to a CrontabSchedule object."""
    return CrontabSchedule.objects.create(
        minute=date.minute,
        hour=date.hour,
        day_of_month=date.day,
        month_of_year=date.month,
    )


def end_of_day(dt):
    return dt.replace(hour=23, minute=59, second=59)


def calculate_due_date(
    minute: int,
    hour: int,
    day_of_month: int,
    month_of_year: int,
    day_of_week: int,
    user: User,
) -> datetime:
    """Given a crontab object (key-val pairs), calculate the next due date for the task.
    By default, the due date is the end of the day of the next time the crontab
    will run. For example, if the crontab is set to run at 9:00 AM on Monday,
    the due date will be 11:59 PM on Monday.
    """
    return end_of_day(
        get_next_run_time(minute, hour, day_of_month, month_of_year, day_of_week, user)
    )


def calculate_due_date_from_crontab(crontab_schedule: CrontabSchedule, user: User):
    return calculate_due_date(
        crontab_schedule.minute,
        crontab_schedule.hour,
        crontab_schedule.day_of_month,
        crontab_schedule.month_of_year,
        crontab_schedule.day_of_week,
        user,
    )
