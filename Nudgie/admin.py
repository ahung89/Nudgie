from django.contrib import admin

from .models import Conversation, NudgieTask, MockedTime

admin.site.register(Conversation)
admin.site.register(NudgieTask)
admin.site.register(MockedTime)
