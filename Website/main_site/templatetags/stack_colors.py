from django import template

register = template.Library()

@register.filter
def stack_bg_color(stack_type):
    return {
        "mern": "bg-emerald-200",
        "django": "bg-blue-200",
        "mean": "bg-pink-300",
        "lamp": "bg-yellow-200",
        "mevn": "bg-purple-200",
    }.get(stack_type, "bg-zinc-50")