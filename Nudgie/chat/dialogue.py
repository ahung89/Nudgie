from Nudgie.models import Conversation
from django.contrib.auth.models import User


def load_conversation(user):
    # check if the convo is in the request session
    lines = Conversation.objects.filter(user=user).order_by("timestamp")
    return [{"role": line.message_type, "content": line.content} for line in lines]


def save_line_of_speech(
    user: User, message_type: str, dialogue_type: str, content: str
):
    """Saves a line of conversation to the database."""
    message = Conversation(
        user=user,
        message_type=message_type,
        dialogue_type=dialogue_type,
        content=content,
    )
    message.save()
