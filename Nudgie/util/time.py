from datetime import datetime
from django.contrib.auth.models import User
from Nudgie.models import MockedTime

TESTING = True

def get_time(user : User):
    if TESTING:
        # that second return value is a boolean that tells us whether or not the
        # object was created. It's not terribly useful here.
        try:
            mocked_time_obj = MockedTime.objects.get(user = user)
        except MockedTime.DoesNotExist:
            # Time hasn't been mocked yet - returning actual time.
            return datetime.now()

        print(f'USING MOCKED TIME: {mocked_time_obj.mocked_time}')
        return mocked_time_obj.mocked_time
    else:
        return datetime.now()

def set_time(user : User, new_time : datetime):
    mocked_time_obj, _ = MockedTime.objects.get_or_create(
        user=user, 
        defaults={
            'mocked_time': new_time
        }
    )

    mocked_time_obj.mocked_time = new_time
    mocked_time_obj.save()

    print(f'SETTING MOCKED TIME: {mocked_time_obj.mocked_time}')

    return mocked_time_obj.mocked_time