"""
URL configuration for Nudgie project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("schedule/", views.schedule_task, name="schedule_task"),
    path("chatbot/", views.chatbot_view, name="chatbot"),
    path("chatbot/api/", views.chatbot_api, name="chatbot_api"),
    path("clear_cache/", views.clear_cache, name="clear_cache"),
    path("reset_user_data/", views.reset_user_data, name="reset_user_data"),
    path("get_task_list/", views.get_task_list_display, name="task_list"),
    path(
        "get_conversation_display/",
        views.get_conversation_display,
        name="conversation_display",
    ),
    path("trigger_task/", views.trigger_task, name="trigger_task"),
    path("accounts/", include("allauth.urls")),
]
