from django import template
import json

register = template.Library()

@register.filter
def get_attr_from_json(value, arg):
    try:
        parsed_value = json.loads(value)
        return parsed_value.get(arg, "")
    except:
        return "BRUH YOU FUCKED UP YOUR PARSING"
    
    # This whole file is kind of overkill. I could've just pre-processed the data in the view.
    # However it's more fun to do it this way.