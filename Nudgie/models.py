from django.contrib.auth.models import User
from django.db import models

class Conversation(models.Model):
    #the ForeignKey method creates a one-to-many relationship between the User and
    #Conversation models.
    #Setting on_delete=models.CASCADE will delete all conversations associated with a user
    #when that user is deleted.
    #The related_name attribute allows us to access all conversations associated with a
    #user by using user.conversations.all(). Dope, right?
    user = models.ForeignKey(User, related_name='conversations', on_delete=models.CASCADE)
    message_type = models.CharField(max_length=20, choices=[('user', 'User'), ('assistant', 'Assistant')])
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Conversation with {self.user.username} - {self.timestamp}"

class Task(models.Model):
    user = models.ForeignKey(User, related_name='tasks', on_delete=models.CASCADE)
    #eventually i'm going to want to store a description of the habit and goal, for
    #richer detailing.
    habit_name = models.CharField(max_length=100)
    goal_name = models.CharField(max_length=100)
    due_date = models.DateField()