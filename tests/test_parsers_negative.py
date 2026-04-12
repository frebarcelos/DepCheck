"""
tests/test_parsers_negative.py
Cenários negativos e edge-cases dos parsers de manifesto.
Cobre linhas de erro não testadas em test_parsers.py.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from src.parsers.pyproject_parser import parse_pyproject
from src.parsers.requirements_parser import parse_requirements


# ── pyproject_parser ────────────────────────────────────────────────────────


def test_pyproject_raises_when_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        parse_pyproject(Path("/nonexistent/pyproject.toml"))


def test_pyproject_raises_on_invalid_toml(tmp_path: Path) -> None:
    bad = tmp_path / "pyproject.toml"
    bad.write_text("[[[ invalid toml", encoding="utf-8")
    with pytest.raises(ValueError, match="TOML"):
        parse_pyproject(bad)


def test_pyproject_pep621_dependencies(tmp_path: Path) -> None:
    f = tmp_path / "pyproject.toml"
    f.write_text(
        textwrap.dedent("""
        [project]
        name = "demo"
        dependencies = ["requests>=2.0", "flask"]
        """),
        encoding="utf-8",
    )
    result = parse_pyproject(f)
    assert "requests" in result
    assert "flask" in result


def test_pyproject_poetry_dependencies(tmp_path: Path) -> None:
    f = tmp_path / "pyproject.toml"
    f.write_text(
        textwrap.dedent("""
        [tool.poetry.dependencies]
        python = "^3.10"
        requests = "^2.28"
        numpy = "*"
        """),
        encoding="utf-8",
    )
    result = parse_pyproject(f)
    assert "requests" in result
    assert "numpy" in result
    assert "python" not in result  # deve ser ignorado


def test_pyproject_empty_dependencies(tmp_path: Path) -> None:
    f = tmp_path / "pyproject.toml"
    f.write_text("[project]\nname = 'x'\n", encoding="utf-8")
    result = parse_pyproject(f)
    assert result == {}


def test_pyproject_normalizes_hyphens_to_underscore(tmp_path: Path) -> None:
    f = tmp_path / "pyproject.toml"
    f.write_text('[project]\ndependencies = ["my-package>=1.0"]\n', encoding="utf-8")
    result = parse_pyproject(f)
    assert "my_package" in result


# ── requirements_parser ─────────────────────────────────────────────────────


def test_requirements_raises_when_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        parse_requirements(Path("/nonexistent/requirements.txt"))


def test_requirements_ignores_comments() -> None:
    from pathlib import Path
    import tempfile
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        f.write("# this is a comment\nrequests>=2.0\n")
        name = f.name
    result = parse_requirements(Path(name))
    assert "requests" in result
    assert len(result) == 1


def test_requirements_ignores_blank_lines(tmp_path: Path) -> None:
    f = tmp_path / "requirements.txt"
    f.write_text("\n\n  \nflask>=3.0\n\n", encoding="utf-8")
    result = parse_requirements(f)
    assert "flask" in result


def test_requirements_ignores_pip_flags(tmp_path: Path) -> None:
    f = tmp_path / "requirements.txt"
    f.write_text(
        "-r base.txt\n-e .\n--index-url https://pypi.org\nnumpy\n",
        encoding="utf-8",
    )
    result = parse_requirements(f)
    assert list(result.keys()) == ["numpy"]


def test_requirements_strips_inline_comments(tmp_path: Path) -> None:
    f = tmp_path / "requirements.txt"
    f.write_text("requests>=2.0  # needed for auth\n", encoding="utf-8")
    result = parse_requirements(f)
    assert "requests" in result


def test_requirements_extracts_version(tmp_path: Path) -> None:
    f = tmp_path / "requirements.txt"
    f.write_text("flask==3.0.0\n", encoding="utf-8")
    result = parse_requirements(f)
    assert result.get("flask") == "==3.0.0"


def test_requirements_empty_file(tmp_path: Path) -> None:
    f = tmp_path / "requirements.txt"
    f.write_text("", encoding="utf-8")
    result = parse_requirements(f)
    assert result == {}
