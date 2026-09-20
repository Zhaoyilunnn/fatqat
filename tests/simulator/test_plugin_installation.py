"""Exercise real wheel metadata and imports in an isolated subprocess."""

import base64
import csv
import hashlib
import io
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import venv
import zipfile


def test_installed_plugin_discovery_and_execution(tmp_path):
    # Build a dependency-free wheel with standard dist-info and RECORD files.
    # No build frontend or network access is needed for this tiny test package.
    info = "fatqat_test_plugin-1.0.dist-info"
    files = {
        "fatqat_test_plugin.py": textwrap.dedent("""\
            from fatqat.simulator import Simulator

            def create(**options):
                return Simulator(**options)
            """),
        "fatqat_broken_plugin.py": "raise RuntimeError('must only load on selection')\n",
        f"{info}/METADATA": "Metadata-Version: 2.1\nName: fatqat-test-plugin\nVersion: 1.0\n",
        f"{info}/WHEEL": "Wheel-Version: 1.0\nGenerator: fatqat-test\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        f"{info}/entry_points.txt": (
            "[fatqat.simulators.v1]\n"
            "test-installed = fatqat_test_plugin:create\n"
            "test-broken = fatqat_broken_plugin:create\n"
            "[fatqat.simulators.v2]\n"
            "test-future = fatqat_broken_plugin:create\n"
        ),
    }
    record = io.StringIO(newline="")
    writer = csv.writer(record)
    wheel = tmp_path / "fatqat_test_plugin-1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, content in files.items():
            data = content.encode()
            digest = (
                base64.urlsafe_b64encode(hashlib.sha256(data).digest())
                .rstrip(b"=")
                .decode()
            )
            writer.writerow((name, f"sha256={digest}", len(data)))
            archive.writestr(name, data)
        writer.writerow((f"{info}/RECORD", "", ""))
        archive.writestr(f"{info}/RECORD", record.getvalue())

    environment = tmp_path / "environment"
    venv.EnvBuilder(with_pip=True, system_site_packages=True).create(environment)
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    # A nested venv inherits the base interpreter, not the parent venv's
    # packages. Pass the active test environment's import paths explicitly.
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        str(Path(path).resolve()) for path in sys.path if path
    )
    subprocess.run(
        [str(python), "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    script = """
import sys
import fatqat as fq
import fatqat.operations as ops
from fatqat.errors import SimulatorPluginError
assert "fatqat_test_plugin" not in sys.modules
assert "fatqat_broken_plugin" not in sys.modules
names = fq.simulator.available()
assert "test-installed" in names
assert "test-broken" in names
assert "test-future" not in names
assert "fatqat_test_plugin" not in sys.modules
assert "fatqat_broken_plugin" not in sys.modules
backend = fq.simulator.get("test-installed", method="SV", runtime="numpy")
program = fq.Program(2, 2)
program.add(ops.X, 0)
program.measure_all()
assert backend.run(program, shots=9).result().get_counts() == {"10": 9}
assert "fatqat_broken_plugin" not in sys.modules
try:
    fq.simulator.get("test-broken")
except SimulatorPluginError as error:
    assert isinstance(error.__cause__, RuntimeError)
else:
    raise AssertionError("broken plugin was accepted")
"""
    result = subprocess.run(
        [str(python), "-c", script],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr
