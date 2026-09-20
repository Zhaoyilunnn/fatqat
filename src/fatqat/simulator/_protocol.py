"""Structural execution contract for simulator plugins."""

from __future__ import annotations

from typing import Any, Protocol

from ..execution import ExecutableProgram
from ..job import Job
from ..program import Program
from ..resource_layout import ResourceLayout
from ..result import Result


class SimulatorBackend(Protocol):
    """Execute programs synchronously without requiring a common base class.

    Implementations return terminal jobs and support sequential instance reuse.
    Use separate instances for concurrent calls. Release process and file
    handles before returning; any returned artifact paths must remain readable.
    This protocol does not imply sweep, Estimator, or asynchronous support.
    """

    def run(
        self,
        program: Program | ExecutableProgram,
        *,
        shots: int = 1024,
        resource_layout: ResourceLayout | None = None,
        initial_state: Any = None,
        simulation_config: dict[str, Any] | None = None,
        result_config: dict[str, Any] | None = None,
    ) -> Job[Result]:
        """Validate and execute one program, returning an already terminal job.

        Args:
            program: Native program or executable carrying its resource layout.
                The caller must not modify it or its operations during execution.
            shots: Requested sample count, default ``1024``.
            resource_layout: Optional device mapping, default ``None``. Reject
                a separate layout when the executable already carries one.
            initial_state: Backend-defined initial state, default ``None``.
            simulation_config: Backend-defined execution options; ``None`` uses
                backend defaults. Each backend documents its keys and values.
            result_config: Backend-defined result selection; ``None`` uses
                backend defaults. Each backend documents its keys and values.

        Returns:
            A completed `Job` containing a `Result`, or an error job whose
            ``result()`` raises the execution error. Only produced result fields
            belong in ``available_data``.

        Raises:
            BackendValidationError: If the request is invalid. Unsupported
                operations or non-default options must be rejected before
                execution, using ``UnsupportedOperationError`` where applicable.
        """
