"""Simulator selection and failures at the plugin boundary."""

from importlib import metadata
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import fatqat as fq
import fatqat.operations as ops
from fatqat.errors import BackendValidationError, SimulatorPluginError


@pytest.fixture(name="declarations")
def fixture_declarations(monkeypatch):
    entries = []

    def discover(**selection):
        return tuple(
            entry
            for entry in entries
            if all(getattr(entry, key) == value for key, value in selection.items())
        )

    monkeypatch.setattr(metadata, "entry_points", discover)
    return entries


def entry(name, factory=None, *, provider="test-plugin", group="fatqat.simulators.v1"):
    return SimpleNamespace(
        name=name,
        group=group,
        value=f"{provider}:Factory",
        dist=SimpleNamespace(metadata={"Name": provider}),
        load=Mock(return_value=factory),
    )


def test_matrix_matches_direct_construction_and_returns_fresh_instances(declarations):
    program = fq.Program(2, 2)
    program.add(ops.X, 0)
    program.measure_all()
    selected = fq.simulator.get("matrix", method="SV", runtime="numpy")
    direct = fq.simulator.Simulator("SV", runtime="numpy")
    assert isinstance(selected, fq.simulator.Simulator)
    assert selected is not fq.simulator.get("matrix", runtime="numpy")
    assert (
        selected.run(program, shots=7).result().get_counts()
        == direct.run(program, shots=7).result().get_counts()
        == {"10": 7}
    )


def test_discovery_is_lazy_sorted_unique_and_v1_only(declarations):
    declarations.extend(
        [
            entry("z"),
            entry("a"),
            entry("a"),
            entry("matrix"),
            entry("Bad"),
            entry("future", group="fatqat.simulators.v2"),
        ]
    )
    assert fq.simulator.available() == ("a", "matrix", "z")
    for declaration in declarations:
        declaration.load.assert_not_called()
    with pytest.raises(SimulatorPluginError, match="Unknown simulator 'future'"):
        fq.simulator.get("future")


def test_selected_factory_receives_options_and_unrelated_broken_plugin_is_not_loaded(
    declarations,
):
    options = {"profile": object(), "extra": None}
    factory = Mock(
        side_effect=lambda **kwargs: SimpleNamespace(run=lambda: None, options=kwargs)
    )
    selected = entry("custom", factory)
    broken = entry("broken")
    broken.load.side_effect = ImportError("missing native runtime")
    declarations.extend([broken, selected])
    first = fq.simulator.get("custom", **options)
    second = fq.simulator.get("custom", **options)
    assert first is not second
    assert first.options == options
    assert first.options["profile"] is options["profile"]
    factory.assert_called_with(**options)
    broken.load.assert_not_called()


def test_factory_can_receive_name_option(declarations):
    factory = Mock(side_effect=lambda **kwargs: SimpleNamespace(run=lambda: None))
    declarations.append(entry("custom", factory))

    # The positional-only selector deliberately leaves this keyword for options.
    # pylint: disable-next=kwarg-superseded-by-positional-arg
    fq.simulator.get("custom", name="device-1")

    factory.assert_called_once_with(name="device-1")


@pytest.mark.parametrize("name", [None, 42, [], True])
def test_non_string_name(name, declarations):
    with pytest.raises(TypeError, match="string"):
        fq.simulator.get(name)


@pytest.mark.parametrize(
    "name", ["", "Matrix", " matrix", "matrix ", "matrix\n", "é", "1test", "a.b"]
)
def test_invalid_name(name, declarations):
    with pytest.raises(ValueError, match="must match"):
        fq.simulator.get(name)


def test_unknown_name_lists_choices_and_environment_hint(declarations):
    declarations.append(entry("custom"))
    with pytest.raises(
        SimulatorPluginError, match="custom, matrix.*current Python environment"
    ):
        fq.simulator.get("missing")


@pytest.mark.parametrize("name", ["custom", "matrix"])
def test_conflicts_report_all_providers_without_loading(name, declarations):
    declarations.append(entry(name, provider="one"))
    if name != "matrix":
        declarations.append(entry(name, provider="two"))
    with pytest.raises(SimulatorPluginError) as error:
        fq.simulator.get(name)
    assert "one: one:Factory" in str(error.value)
    assert ("two: two:Factory" if name == "custom" else "fatqat (built-in)") in str(
        error.value
    )
    for declaration in declarations:
        declaration.load.assert_not_called()


def test_import_failure_preserves_cause_and_identity(declarations):
    declaration = entry("broken")
    cause = ImportError("runtime missing")
    declaration.load.side_effect = cause
    declarations.append(declaration)
    with pytest.raises(
        SimulatorPluginError, match="test-plugin: test-plugin:Factory"
    ) as error:
        fq.simulator.get("broken")
    assert error.value.__cause__ is cause


@pytest.mark.parametrize("factory", [None, 17, object, lambda: SimpleNamespace(run=17)])
def test_invalid_factory_or_backend(factory, declarations):
    declarations.append(entry("broken", factory))
    with pytest.raises(SimulatorPluginError, match="callable"):
        fq.simulator.get("broken")


@pytest.mark.parametrize(
    "cause", [TypeError("bad options"), BackendValidationError("bad profile")]
)
def test_factory_errors_propagate_unchanged(cause, declarations):
    declarations.append(entry("custom", Mock(side_effect=cause)))
    with pytest.raises(type(cause)) as error:
        fq.simulator.get("custom")
    assert error.value is cause


@pytest.mark.parametrize("cause", [KeyboardInterrupt(), SystemExit()])
def test_loading_does_not_swallow_process_control(cause, declarations):
    declaration = entry("custom")
    declaration.load.side_effect = cause
    declarations.append(declaration)
    with pytest.raises(type(cause)):
        fq.simulator.get("custom")
