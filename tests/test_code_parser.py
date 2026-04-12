from __future__ import annotations

from pathlib import Path

import pytest

from src.code_parser import _extract_imports_from_file, get_all_imports, parse_imports


def test_extract_imports_from_file_collects_root_modules(tmp_path: Path) -> None:
    """Extrai corretamente nomes de módulos raiz a partir de imports válidos."""
    py_file = tmp_path / "sample.py"
    py_file.write_text(
        "\n".join(
            [
                "import requests",
                "import numpy as np",
                "from pandas.io import json",
                "from .local import thing",
            ]
        ),
        encoding="utf-8",
    )

    imports = _extract_imports_from_file(py_file)

    assert imports == {"requests", "numpy", "pandas"}


def test_extract_imports_from_file_returns_empty_on_syntax_error(tmp_path: Path) -> None:
    """Retorna conjunto vazio quando o arquivo contém erro de sintaxe."""
    broken_file = tmp_path / "broken.py"
    broken_file.write_text("def broken(:\n    pass\n", encoding="utf-8")

    imports = _extract_imports_from_file(broken_file)

    assert imports == set()


def test_parse_imports_ignores_test_dirs_and_ignored_files(tmp_path: Path) -> None:
    """Ignora arquivos/pastas configurados como excluídos na varredura."""
    src_file = tmp_path / "app.py"
    test_file = tmp_path / "tests" / "test_app.py"
    setup_file = tmp_path / "setup.py"

    test_file.parent.mkdir(parents=True, exist_ok=True)

    src_file.write_text("import requests\n", encoding="utf-8")
    test_file.write_text("import pytest\n", encoding="utf-8")
    setup_file.write_text("import setuptools\n", encoding="utf-8")

    parsed = parse_imports(tmp_path)

    assert set(parsed.keys()) == {"app.py"}
    assert parsed["app.py"] == {"requests"}


def test_parse_imports_raises_for_invalid_directory(tmp_path: Path) -> None:
    """Lança ValueError quando o caminho informado não é diretório."""
    invalid_path = tmp_path / "not_a_dir.py"
    invalid_path.write_text("import os\n", encoding="utf-8")

    with pytest.raises(ValueError):
        parse_imports(invalid_path)


def test_get_all_imports_flattens_results(monkeypatch, tmp_path: Path) -> None:
    """Consolida imports de múltiplos arquivos em um único conjunto."""

    def _mock_parse_imports(_root: Path) -> dict[str, set[str]]:
        return {
            "a.py": {"requests", "os"},
            "b.py": {"flask", "requests"},
        }

    monkeypatch.setattr("src.code_parser.parse_imports", _mock_parse_imports)

    all_imports = get_all_imports(tmp_path)

    assert all_imports == {"requests", "os", "flask"}
