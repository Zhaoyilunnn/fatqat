"""Discover simulator factories from installed distribution metadata."""

from __future__ import annotations

from importlib import metadata
import re
from typing import Any, cast

from ..errors import SimulatorPluginError
from ._protocol import SimulatorBackend
from .simulator import Simulator

_GROUP = "fatqat.simulators.v1"
_NAME = re.compile(r"[a-z][a-z0-9_-]*")


def available() -> tuple[str, ...]:
    """Return sorted, unique declared simulator names, including ``matrix``.

    Read v1 entry-point metadata without loading plugin targets. Ignore names
    outside ``[a-z][a-z0-9_-]*``. A listed name may have conflicting providers
    or an unavailable runtime; listing is not a health check. Discovery is not
    cached. Restart Python after installing or uninstalling plugins.
    """
    return tuple(
        sorted(
            {"matrix"}
            | {
                entry.name
                for entry in metadata.entry_points(group=_GROUP)
                if _NAME.fullmatch(entry.name)
            }
        )
    )


def _provider(entry: metadata.EntryPoint) -> str:
    distribution = entry.dist
    name = (
        distribution.metadata.get("Name", "unknown distribution")
        if distribution
        else "unknown distribution"
    )
    return f"{name}: {entry.value}"


def get(name: str, /, **options: Any) -> SimulatorBackend:
    """Create a simulator by its exact installed name.

    ``matrix`` selects `Simulator`; other factories come from the entry-point
    group ``fatqat.simulators.v1``. Each call invokes the selected factory;
    instances are not cached. Factories must return fresh objects and should
    only establish configuration, without starting processes or using networks.
    Only the selected plugin is loaded. A callable ``run`` is checked, but its
    signature and execution behavior remain the plugin author's responsibility.

    Args:
        name: Positional-only lowercase ASCII name matching
            ``[a-z][a-z0-9_-]*``. No case or whitespace normalization is
            performed.
        **options: Keyword arguments passed unchanged to the factory. For
            ``matrix``, these are the `Simulator` constructor options.

    Returns:
        The backend object returned by the factory, without a proxy.

    Raises:
        TypeError: If ``name`` is not a string.
        ValueError: If ``name`` has an invalid format.
        SimulatorPluginError: If the name is unknown, has multiple providers
            (including a plugin claiming ``matrix``), cannot be loaded, or has
            an invalid factory or result. Import errors retain their cause.
            Factory configuration errors propagate unchanged.
    """
    if not isinstance(name, str):
        raise TypeError("simulator name must be a string")
    if not _NAME.fullmatch(name):
        raise ValueError("simulator name must match [a-z][a-z0-9_-]*")
    entries = tuple(metadata.entry_points(group=_GROUP, name=name))
    providers = [_provider(entry) for entry in entries]
    if name == "matrix":
        providers.append("fatqat (built-in): fatqat.simulator:Simulator")
    if not providers:
        raise SimulatorPluginError(
            f"Unknown simulator {name!r}. Available: {', '.join(available())}. "
            "Install the plugin in the current Python environment."
        )
    if len(providers) > 1:
        raise SimulatorPluginError(
            f"Conflicting simulator {name!r} providers: {'; '.join(sorted(providers))}"
        )
    if name == "matrix":
        factory = Simulator
    else:
        try:
            factory = entries[0].load()
        except Exception as exc:
            raise SimulatorPluginError(
                f"Cannot load simulator {name!r} from {providers[0]}"
            ) from exc
    if not callable(factory):
        raise SimulatorPluginError(f"Simulator factory is not callable: {providers[0]}")
    backend = factory(**options)
    if not callable(getattr(backend, "run", None)):
        raise SimulatorPluginError(
            f"Simulator factory returned an object without callable run: {providers[0]}"
        )
    return cast(SimulatorBackend, backend)
