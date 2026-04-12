"""
tests/test_code_parser_negative.py
Cenários negativos e edge-cases do code_parser.
"""
from __future__ import annotations

from pathlib import Path

from src.code_parser import get_all_imports, parse_imports


def test_parse_imports_skips_syntax_error_files(tmp_path: Path) -> None:
    """Arquivo com SyntaxError não deve causar falha, apenas ser ignorado."""
    bad = tmp_path / "bad.py"
    bad.write_text("def f(\n  # SyntaxError aqui\n", encoding="utf-8")
    result = parse_imports(tmp_path)
    assert str(bad.relative_to(tmp_path)) not in result


def test_parse_imports_skips_ignored_dirs(tmp_path: Path) -> None:
    """Arquivos dentro de tests/ devem ser ignorados."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_file = tests_dir / "test_something.py"
    test_file.write_text("import pytest\n", encoding="utf-8")
    app_file = tmp_path / "app.py"
    app_file.write_text("import flask\n", encoding="utf-8")

    result = parse_imports(tmp_path)
    imports = {mod for mods in result.values() for mod in mods}
    assert "pytest" not in imports
    assert "flask" in imports


def test_parse_imports_handles_encoding_errors(tmp_path: Path) -> None:
    """Arquivo com encoding inválido não deve travar o parser."""
    bad = tmp_path / "latin.py"
    bad.write_bytes(b"import os\n# caf\xe9\n")
    result = parse_imports(tmp_path)
    imports = {mod for mods in result.values() for mod in mods}
    assert "os" in imports


def test_get_all_imports_returns_flat_set(tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    a.write_text("import requests\nfrom flask import Flask\n", encoding="utf-8")
    b = tmp_path / "b.py"
    b.write_text("import numpy\nimport requests\n", encoding="utf-8")

    result = get_all_imports(tmp_path)
    assert "requests" in result
    assert "flask" in result
    assert "numpy" in result
    assert isinstance(result, set)


def test_get_all_imports_empty_dir(tmp_path: Path) -> None:
    result = get_all_imports(tmp_path)
    assert result == set()


def test_parse_imports_raises_on_invalid_dir() -> None:
    import pytest
    with pytest.raises(ValueError):
        parse_imports(Path("/this/does/not/exist"))
