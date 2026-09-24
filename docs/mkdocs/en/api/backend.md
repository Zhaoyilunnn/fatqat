---
title: "Backend"
---

# Backend

[`Backend`][fatqat.Backend] defines a structural interface for custom execution
backends: `run(program, **options)` accepts a [`Program`][fatqat.Program] and
returns a [`Result`][fatqat.Result] directly. Implementations do not need to
inherit from `Backend`.

Each backend defines its own keyword options, defaults, validation, and produced
result fields. Import and instantiate the implementation directly, then pass it
to code that accepts a `Backend`:

```python
from fatqat import Backend, Program, Result


def execute(backend: Backend, program: Program) -> Result:
    return backend.run(program)
```

Callers can supply additional keyword options supported by their chosen backend.
The protocol does not prescribe option names or perform runtime validation.
Existing simulator and emulator APIs return `Job[Result]`; they retain that
interface and are not changed to implement this direct-result protocol.

::: fatqat.Backend
    options:
      members:
        - run
      show_bases: true
