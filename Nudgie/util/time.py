from datetime import datetime
from django.contrib.auth.models import User
from Nudgie.models import MockedTime
import pytz

TESTING = True


def localize(dt: datetime):
    return pytz.timezone("UTC").localize(dt)


def get_time(user: User) -> datetime:
    if TESTING:
        # that second return value is a boolean that tells us whether or not the
        # object was created. It's not terribly useful here.
        try:
            mocked_time_obj = MockedTime.objects.get(user=user)
        except MockedTime.DoesNotExist:
            # Time hasn't been mocked yet - returning actual time.
            return localize(datetime.now())

        print(f"USING MOCKED TIME: {mocked_time_obj.mocked_time}")
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
