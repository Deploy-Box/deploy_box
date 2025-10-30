from stacks.stack_managers.stack_manager import StackManager
from stacks.stack_managers.django import DjangoStackManager
from stacks.stack_managers.mern import MERNStackManager
from stacks.models import Stack

STACK_MANAGER_MAPPING = {
    "DJANGO": DjangoStackManager,
    "MERN": MERNStackManager,
}

def get_stack_manager(stack: Stack) -> StackManager:
    stack_type = stack.purchased_stack.type

    stack_manager_class = STACK_MANAGER_MAPPING.get(stack_type.upper())
    if not stack_manager_class:
        raise ValueError(f"Unsupported stack type: {stack_type}")

    return stack_manager_class(stack=stack)