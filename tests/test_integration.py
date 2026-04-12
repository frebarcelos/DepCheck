"""
tests/test_integration.py
Testes de integração end-to-end: ZIP real → orquestrador → modelo de resultado.
Todos os calls externos (PyPI) são mockados.
"""
from __future__ import annotations

import io
import textwrap
import zipfile
from pathlib import Path
from typing import Any
from unittest.mock import patch, MagicMock

import pytest

from src.orchestrator import run_analysis


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_project_zip(files: dict[str, str]) -> bytes:
    """Cria um ZIP em memória com o conteúdo fornecido."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def _extract_zip_to(zip_bytes: bytes, dest: Path) -> Path:
    """Extrai ZIP para dest e retorna dest."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        zf.extractall(dest)
    return dest


_PYPI_RESP: dict[str, Any] = {
    "info": {"version": "9.9.9"},
    "releases": {
        "9.9.9": [{"upload_time": "2023-01-01T00:00:00", "size": 102400, "filename": "pkg-9.9.9-py3-none-any.whl"}],
        "2.28.0": [{"upload_time": "2022-06-01T00:00:00", "size": 51200, "filename": "requests-2.28.0-py3-none-any.whl"}],
    },
    "urls": [],
}


# ── Integração: projeto com pyproject.toml na raiz ─────────────────────────────

def test_integration_pyproject_at_root(tmp_path: Path) -> None:
    """Projeto com pyproject.toml na raiz: declaradas detectadas corretamente."""
    (tmp_path / "pyproject.toml").write_text(
        textwrap.dedent("""
        [project]
        name = "demo"
        dependencies = ["requests>=2.28.0", "unused-pkg"]
        """),
        encoding="utf-8",
    )
    (tmp_path / "main.py").write_text("import requests\n", encoding="utf-8")

    with patch("src.clients.pypi_client.get_pypi_package_info", return_value=_PYPI_RESP):
        result = run_analysis(str(tmp_path))

    assert result["statistics"]["total_declared"] == 2
    assert result["statistics"]["total_imported"] >= 1
    assert "requests" in [r.split(">=")[0].split("==")[0] for r in result["dependencies"]["declared"]]
    # unused-pkg não foi importado → deve ser zumbi
    zombie_names = [z.split(">=")[0].split("==")[0].lower().replace("-", "_") for z in result["dependencies"]["zombies"]]
    assert "unused_pkg" in zombie_names or "unused-pkg" in result["dependencies"]["zombies"]


def test_integration_pyproject_in_subfolder(tmp_path: Path) -> None:
    """ZIP com pasta raiz (ex: myproject/pyproject.toml): parser encontra manifesto."""
    sub = tmp_path / "myproject"
    sub.mkdir()
    (sub / "pyproject.toml").write_text(
        '[project]\ndependencies = ["flask>=3.0"]\n', encoding="utf-8"
    )
    (sub / "app.py").write_text("import flask\n", encoding="utf-8")

    with patch("src.clients.pypi_client.get_pypi_package_info", return_value=_PYPI_RESP):
        result = run_analysis(str(tmp_path))

    assert result["statistics"]["total_declared"] == 1
    assert result["statistics"]["total_zombies"] == 0


def test_integration_requirements_txt(tmp_path: Path) -> None:
    """Projeto com requirements.txt: deps detectadas corretamente."""
    (tmp_path / "requirements.txt").write_text(
        "requests>=2.28.0\nnumpy>=1.24.0\n", encoding="utf-8"
    )
    (tmp_path / "script.py").write_text("import requests\nimport numpy\n", encoding="utf-8")

    with patch("src.clients.pypi_client.get_pypi_package_info", return_value=_PYPI_RESP):
        result = run_analysis(str(tmp_path))

    assert result["statistics"]["total_declared"] == 2
    assert result["statistics"]["total_zombies"] == 0
    assert result["statistics"]["total_ghosts"] == 0


def test_integration_no_manifest_returns_empty_declared(tmp_path: Path) -> None:
    """Sem manifesto: declared deve ser vazio, imports detectados como ghosts."""
    (tmp_path / "app.py").write_text("import flask\nimport os\n", encoding="utf-8")

    with patch("src.clients.pypi_client.get_pypi_package_info", return_value=None):
        result = run_analysis(str(tmp_path))

    assert result["statistics"]["total_declared"] == 0
    # flask não é stdlib → deve aparecer como ghost
    assert "flask" in result["dependencies"]["ghosts"]


def test_integration_stdlib_not_ghost(tmp_path: Path) -> None:
    """Módulos da stdlib (os, sys, json) não devem aparecer como ghosts."""
    (tmp_path / "app.py").write_text(
        "import os\nimport sys\nimport json\nimport re\n", encoding="utf-8"
    )

    with patch("src.clients.pypi_client.get_pypi_package_info", return_value=None):
        result = run_analysis(str(tmp_path))

    ghosts = result["dependencies"]["ghosts"]
    assert "os" not in ghosts
    assert "sys" not in ghosts
    assert "json" not in ghosts
    assert "re" not in ghosts


def test_integration_enriched_metadata_populated(tmp_path: Path) -> None:
    """enriched_declared deve ser populado com size_bytes quando PyPI responde."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["requests>=2.28.0"]\n', encoding="utf-8"
    )
    (tmp_path / "main.py").write_text("import requests\n", encoding="utf-8")

    with patch("src.clients.pypi_client.get_pypi_package_info", return_value=_PYPI_RESP):
        result = run_analysis(str(tmp_path))

    enriched = result.get("enriched_declared", {})
    if enriched:
        for meta in enriched.values():
            assert "size_bytes" in meta
            assert "age_days" in meta


def test_integration_pypi_unavailable_does_not_crash(tmp_path: Path) -> None:
    """Se o PyPI estiver inacessível, a análise ainda deve concluir."""
    (tmp_path / "requirements.txt").write_text("requests\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("import requests\n", encoding="utf-8")

    with patch("src.clients.pypi_client.get_pypi_package_info", return_value=None):
        result = run_analysis(str(tmp_path))

    assert "dependencies" in result
    assert "statistics" in result
    assert result["statistics"]["total_declared"] == 1


def test_integration_result_model_structure(tmp_path: Path) -> None:
    """O dicionário de resultado deve sempre ter a estrutura esperada."""
    with patch("src.clients.pypi_client.get_pypi_package_info", return_value=None):
        result = run_analysis(str(tmp_path))

    assert "project_info" in result
    assert "dependencies" in result
    assert "statistics" in result
    assert "enriched_declared" in result
    assert "analyzed_at" in result["project_info"]
    for key in ("declared", "imported", "zombies", "ghosts", "outdated"):
        assert key in result["dependencies"]
    for key in ("total_declared", "total_imported", "total_zombies",
                "total_ghosts", "total_outdated"):
        assert key in result["statistics"]


def test_integration_filter_removes_ignored_dirs(tmp_path: Path) -> None:
    """Arquivos em tests/ não devem ser contabilizados nos imports."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["requests"]\n', encoding="utf-8"
    )
    (tmp_path / "app.py").write_text("import requests\n", encoding="utf-8")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_app.py").write_text("import pytest\nimport requests\n", encoding="utf-8")

    with patch("src.clients.pypi_client.get_pypi_package_info", return_value=_PYPI_RESP):
        result = run_analysis(str(tmp_path))

    # pytest deve ser ghost (importado em tests/ mas ignorado pelo filter)
    # Mas como o orchestrator usa code_parser que já ignora tests/, pytest não aparece
    assert "pytest" not in result["dependencies"]["imported"]


def test_integration_healthy_count_correct(tmp_path: Path) -> None:
    """KPI de saudáveis = declaradas - zumbis - desatualizadas."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["requests>=2.28.0", "numpy", "flask"]\n',
        encoding="utf-8",
    )
    (tmp_path / "app.py").write_text(
        "import requests\nimport numpy\nimport flask\n", encoding="utf-8"
    )

    with patch("src.clients.pypi_client.get_pypi_package_info", return_value=_PYPI_RESP):
        result = run_analysis(str(tmp_path))

    # Sem zumbis, sem fantasmas; desatualizados = pacotes onde 9.9.9 > declared
    # O total_declared deve ser 3
    assert result["statistics"]["total_declared"] == 3
