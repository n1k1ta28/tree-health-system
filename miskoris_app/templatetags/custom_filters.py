
import base64
from django import template

register = template.Library()

@register.filter
def base64encode(value):
    """Converts binary data to a base64-encoded string"""
    if value:
        return base64.b64encode(value).decode('utf-8')
    return value