from Nudgie.models import Conversation

def load_conversation(user):
    #check if the convo is in the request session
    lines = Conversation.objects.filter(user=user).order_by('timestamp') 
    return [{"role": line.message_type,
                    "content": line.content} for line in lines]