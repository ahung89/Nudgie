from datetime import datetime
from django.contrib.auth.models import User
from Nudgie.models import MockedTime

TESTING = True

def get_time(user : User):
    if TESTING:
        # that second return value is a boolean that tells us whether or not the
        # object was created. It's not terribly useful here.
        mocked_time_obj, _ = MockedTime.objects.get_or_create(
            user=user, 
            defaults={
                'mocked_time': datetime.now()
            }
        )

        print(f'USING MOCKED TIME: {mocked_time_obj.mocked_time}')

        return mocked_time_obj.mocked_time
    else:
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')