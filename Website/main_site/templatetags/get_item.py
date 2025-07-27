from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def to_bool(value):
    return str(value).lower() in ("true", "1", "yes", "on")