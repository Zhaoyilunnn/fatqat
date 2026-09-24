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

::: fatqat.Backend
    options:
      members:
        - run
      show_bases: true
