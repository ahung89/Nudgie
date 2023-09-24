from tasks import add
import time

result = add.delay(4, 4)
#result.ready() #this will return False
print(result.get(timeout=1))

#wait for 3 seconds before requesting the result
# time.sleep(3)
# print(result.get(timeout=1)) #this will not work without configuring Celery to use a result backend