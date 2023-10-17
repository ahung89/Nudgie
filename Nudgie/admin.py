from django.contrib import admin

from .models import Conversation, NudgieTask

admin.site.register(Conversation)
admin.site.register(NudgieTask)