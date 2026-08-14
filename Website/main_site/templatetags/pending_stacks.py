from django import template


register = template.Library()

stacksDict = {
    "mern": False,
    "mean": True,
    "mevn": True,
    "mobile": False,
    "llm": True,
    "ai_data": True,
    "computer_vision": True,
    "image_gen": True,
    "ai_agents": True,
    "lamp": True,
}


@register.simple_tag
def pending_stacks(stackType):
    return stacksDict[stackType]