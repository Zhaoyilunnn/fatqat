"""Structural interface for custom execution backends."""

from typing import Any, Protocol

from .program import Program
from .result import Result


class Backend(Protocol):
    """Run a program using a backend's own execution options.

    Implementations need not inherit from this protocol. Each backend defines
    and documents its supported options and the result fields it produces.
    """

    def run(self, program: Program, /, **options: Any) -> Result:
        """Execute one program and return its result.

        Args:
            program: Program to execute.
            **options: Backend-specific execution options.

        Returns:
            The result produced by the backend.
        """
