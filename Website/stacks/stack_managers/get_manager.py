from stacks.stack_managers.Redis.redis import RedisStackManager
from stacks.stack_managers.Pong.Pong import PongStackManager
from stacks.stack_managers.stack_manager import StackManager
from stacks.stack_managers.django import DjangoStackManager
from stacks.stack_managers.mern import MERNStackManager
from stacks.models import Stack, PurchasableStack

STACK_MANAGER_MAPPING: dict[str, type[StackManager]] = {
    "DJANGO": DjangoStackManager,
    "MERN": MERNStackManager,
    "REDIS": RedisStackManager,
    "PONG": PongStackManager,
}

def get_stack_manager(stack: Stack) -> StackManager:
    stack_type = stack.purchased_stack.type

    stack_manager_class = STACK_MANAGER_MAPPING.get(stack_type.upper())
    if not stack_manager_class:
        raise ValueError(f"Unsupported stack type: {stack_type}")

    return stack_manager_class(stack=stack)

def create_purchasable_stacks() -> None:
    for stack_manager_class in STACK_MANAGER_MAPPING.values():
        purchasable_stack_info = stack_manager_class.get_purchasable_stack_info()
        PurchasableStack.objects.get_or_create(
            type=purchasable_stack_info["type"].upper(),
            variant=purchasable_stack_info["variant"].upper(),
            version=purchasable_stack_info["version"].upper(),
            defaults={
                "name": purchasable_stack_info["name"],
                "description": purchasable_stack_info["description"],
                "price_id": purchasable_stack_info["price_id"],
                "features": purchasable_stack_info["features"],
            }
        )


create_purchasable_stacks()