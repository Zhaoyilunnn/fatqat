"""Public instruction snapshots for independent program readers."""

from dataclasses import FrozenInstanceError
import operator

import pytest

import fatqat as fq
import fatqat.operations as ops
from fatqat.program import OperationInstruction


def test_snapshot_preserves_order_identity_conditions_and_unknown_operations():
    class CustomOperation(ops.Operation):
        name = "custom"

    program = fq.Program(2, 2)
    target = program.quantum_registers[0][1]
    condition_refs = tuple(program.classical_registers[0][i] for i in range(2))
    operation = CustomOperation()
    program.add(
        operation, target, condition=((condition_refs[0], 1), (condition_refs[1], 0))
    )
    program.measure((1, 0), (0, 0))
    snapshot = program.instructions
    program.add(ops.X, 0)

    assert len(snapshot) == 2
    assert len(program.instructions) == 3
    record, measurement = snapshot
    assert isinstance(record, OperationInstruction)
    assert record.operation is operation
    assert record.targets[0] is target
    assert target.register is program.quantum_registers[0]
    assert record.condition == ((condition_refs[0], 1), (condition_refs[1], 0))
    assert all(term[0] is ref for term, ref in zip(record.condition, condition_refs))
    assert isinstance(measurement, ops.Measurement)
    assert tuple(ref.index for ref in measurement.targets) == (1, 0)
    assert tuple(ref.index for ref in measurement.outputs) == (0, 0)
    assert all(
        ref.register is program.classical_registers[0] for ref in measurement.outputs
    )
    with pytest.raises(FrozenInstanceError):
        record.operation = ops.H
    with pytest.raises(FrozenInstanceError):
        measurement.outputs = ()
    with pytest.raises(TypeError):
        operator.setitem(snapshot, 0, record)
    with pytest.raises(AttributeError):
        program.instructions = ()


def test_snapshot_preserves_grouped_view():
    qubits = fq.GridRegister(2, 2)
    program = fq.Program([qubits])
    assert program.instructions == ()
    view = qubits.row(1)
    program.add(ops.H, view)
    record = program.instructions[0]
    assert record.targets[0] is view
    assert record.targets[0].register is qubits
    assert record.condition is None
