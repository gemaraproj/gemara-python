"""Packaging guarantees: PEP 420 namespace layout and the PEP 561 marker."""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _build_wheel(tmp_path: Path) -> zipfile.ZipFile:
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path)],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
    )
    wheels = sorted(tmp_path.glob("*.whl"))
    assert len(wheels) == 1, f"expected one wheel, got {wheels}"
    return zipfile.ZipFile(wheels[0])


def test_wheel_ships_py_typed(tmp_path: Path) -> None:
    with _build_wheel(tmp_path) as wheel:
        assert "gemara/v1/py.typed" in wheel.namelist()


def test_wheel_has_no_namespace_init(tmp_path: Path) -> None:
    """gemara must stay a PEP 420 implicit namespace so gemara.v2 can coexist."""
    with _build_wheel(tmp_path) as wheel:
        assert "gemara/__init__.py" not in wheel.namelist()


def test_wheel_version_is_not_zero(tmp_path: Path) -> None:
    """Defect 3: every previous artifact shipped as 0.0.0."""
    with _build_wheel(tmp_path) as wheel:
        assert wheel.filename is not None
        name = Path(wheel.filename).name
        assert "-0.0.0-" not in name, name


def test_package_imports_under_its_namespace() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import gemara.v1; print(gemara.v1.__name__)"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "gemara.v1"
