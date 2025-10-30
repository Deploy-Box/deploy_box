from abc import ABC, abstractmethod
from stacks.models import Stack

class StackManager(ABC):
    def __init__(self, stack: Stack):
        self.stack = stack

    @abstractmethod
    def get_starter_stack_iac_attributes(self) -> None:
        """Retrieve the IAC configuration for the given stack."""
        pass

    @abstractmethod
    def get_is_persistent(self) -> bool:
        """Check whether the stack is persistent."""
        pass

    @abstractmethod
    def set_is_persistent(self, is_persistent: bool) -> None:
        """Set whether the stack is persistent."""
        pass
