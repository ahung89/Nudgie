from django.contrib import admin

from .models import CachedApiResponse, Conversation, Goal, MockedTime, NudgieTask

admin.site.register(Conversation)
admin.site.register(NudgieTask)
admin.site.register(MockedTime)
admin.site.register(CachedApiResponse)
admin.site.register(Goal)
