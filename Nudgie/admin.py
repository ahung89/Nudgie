from django.contrib import admin

from .models import Conversation, Task

admin.site.register(Conversation)
admin.site.register(Task)