---
title: Simulator plugins
---

# Simulator plugins

Use `fatqat.simulator.get()` to select an installed simulator by name. The
built-in `matrix` name creates the existing general simulator; direct
`Simulator("SV")` construction remains supported.

```python
import fatqat as fq

backend = fq.simulator.get("matrix", method="SV", runtime="numpy")
program = fq.Program(1, 1)
program.measure_all()
result = backend.run(program, shots=10).result()
```

`available()` returns sorted, unique declared names without importing plugin
targets. It does not check runtime availability. Names must match
`[a-z][a-z0-9_-]*`; invalid installed names are omitted. `get()` rejects invalid
input rather than stripping whitespace or changing case. A conflicting name
appears once in the listing, but selecting it raises `SimulatorPluginError`
with all provider distributions and entry-point targets. This also applies to
plugins claiming the reserved `matrix` name.

Each call invokes the factory with the supplied keyword arguments unchanged.
Instances and discovery results are not cached. Install plugins into the
current Python environment and restart Python after installation or removal.

## Publish a backend

Declare a callable class or factory function in the plugin's `pyproject.toml`:

```toml
[project.entry-points."fatqat.simulators.v1"]
example = "example_backend:ExampleSimulator"
```

The name `example` is illustrative, not an available package. Declare the
FatQat version range actually tested in your package dependencies. The group
version describes the factory and execution protocol, independently of the
FatQat package version. Only `v1` is discovered.

Factories must create fresh backend objects and should only establish
configuration. Defer subprocesses, network access, and program execution to
`run()`. Loading is lazy and restricted to the selected name. Import failures
are wrapped in `SimulatorPluginError` with the original cause; non-callable
factories and objects without a callable `run` also raise that error. Errors
from the factory itself propagate unchanged so configuration failures retain
their meaning. Unknown names report available choices and the installation
environment requirement.

## Execution contract

Implement [`SimulatorBackend`][fatqat.simulator.SimulatorBackend] structurally;
inheritance is optional. The loader only checks that `run` is callable. Plugin
authors must verify the full signature and behavior through type checking and
contract tests.

`run()` accepts a `Program` or `ExecutableProgram`. Read native programs through
[`Program.instructions`][fatqat.Program.instructions]; see
[Read instructions](program.md#read-instructions). An executable carries its
resource layout; reject a second layout supplied by the caller. Document the
supported operations, dimensions, initial states, configuration keys, result
fields, and defaults. Reject unsupported operations and non-default options
before execution rather than silently ignoring them.

Execution is synchronous: return an already terminal `Job[Result]`. Validation
errors raise directly; execution failures produce an error job whose `result()`
raises the execution error. Sequential instance reuse is supported; use separate
instances for concurrent calls. Release file and process handles before
returning, and keep any promised artifacts at persistent paths. There is no
required `close()` method, cancellation, sweep, or `Estimator` support.

Only produced fields belong in `Result.available_data`. Counts follow classical
register declaration order and slot order, with slot zero on the left; repeated
writes use the last value. See [Result](result.md) for the shared result contract.
Plugin installation metadata does not distribute a native runtime by itself;
plugin packages remain responsible for their runtime dependencies.

## Reference

::: fatqat.simulator.available

::: fatqat.simulator.get

::: fatqat.simulator.SimulatorBackend

::: fatqat.errors.SimulatorPluginError
