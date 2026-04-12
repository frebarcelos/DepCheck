"""
tests/test_e2e.py  –  Dev 3 | Sprint 4
Testes Ponta a Ponta (End-to-End) do pipeline completo:
  ZIP upload → extração → filtro → parsing → AST → análise → relatório

Simula um repositório mockado "pesado" com:
  - Múltiplos arquivos .py com imports reais
  - pyproject.toml e requirements.txt com dependências variadas
  - Presença de zumbis, fantasmas e dependências desatualizadas (via mock PyPI)
  - Diretórios ignorados (tests/, docs/, .venv/)

Paradigma: Procedimental — sem classes, apenas funções e fixtures de arquivo.
"""
from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from src.decompressor import cleanup_session, extract_zip
from src.filter import filter_extracted
from src.orchestrator import run_analysis
from core.results_model import get_empty_result_model


# ──────────────────────────────────────────────────────────────────────────────
# Constantes do repositório mockado
# ──────────────────────────────────────────────────────────────────────────────

MOCK_PYPROJECT = """\
[project]
name = "heavy-mock-project"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "requests>=2.28.0",
    "numpy>=1.24.0",
    "pandas>=2.0.0",
    "flask>=2.3.0",
    "sqlalchemy>=2.0.0",
    "pillow>=10.0.0",
    "celery>=5.3.0",
    "zombie-package>=1.0.0",
]
"""

MOCK_REQUIREMENTS = """\
click>=8.0.0
rich>=13.0.0
httpx>=0.25.0
"""

# Arquivo .py com imports de pacotes declarados + fantasma + stdlib
MOCK_MAIN_PY = """\
import os
import sys
import json
import logging
from pathlib import Path

import requests
import numpy as np
import pandas as pd
from flask import Flask
import sqlalchemy
from PIL import Image

# Fantasma: importado mas não declarado
import boto3

logger = logging.getLogger(__name__)

def main() -> None:
    app = Flask(__name__)
    df = pd.DataFrame()
    arr = np.array([])
    r = requests.get("http://example.com")
    img = Image.new("RGB", (100, 100))
    session = sqlalchemy.create_engine("sqlite:///:memory:")
    client = boto3.client("s3")
    logger.info("Pipeline executado com sucesso.")

if __name__ == "__main__":
    main()
"""

# Segundo arquivo .py com mais imports
MOCK_UTILS_PY = """\
import re
import uuid
import hashlib
from typing import Any, Dict, List

import click
import rich
import httpx

def process(data: List[Dict[str, Any]]) -> str:
    return hashlib.md5(str(data).encode()).hexdigest()
"""

# Arquivo .py em diretório ignorado — NÃO deve ser analisado
MOCK_TEST_PY = """\
import pytest
import requests
import pandas

def test_something():
    assert True
"""

# Arquivo .py em docs/ — NÃO deve ser analisado
MOCK_DOCS_PY = """\
import sphinx
import docutils
"""


# ──────────────────────────────────────────────────────────────────────────────
# Builders de fixture (procedimental)
# ──────────────────────────────────────────────────────────────────────────────

def build_heavy_mock_zip(tmp_path: Path) -> Path:
    """
    Constrói um ZIP simulando um repositório Python com múltiplos módulos,
    arquivos de manifesto e diretórios que devem ser ignorados.
    """
    zip_path = tmp_path / "heavy_mock_project.zip"

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Manifesto de dependências
        zf.writestr("pyproject.toml", MOCK_PYPROJECT)
        zf.writestr("requirements.txt", MOCK_REQUIREMENTS)

        # Código-fonte principal
        zf.writestr("src/main.py", MOCK_MAIN_PY)
        zf.writestr("src/utils.py", MOCK_UTILS_PY)
        zf.writestr("src/__init__.py", "")

        # Módulo de negócio adicional
        zf.writestr("src/business/core.py", "import celery\nimport redis\ndef task(): pass")
        zf.writestr("src/business/__init__.py", "")

        # Módulo de API
        zf.writestr("api/routes.py", "import flask\nfrom flask import Blueprint\nroutes = Blueprint('api', __name__)")
        zf.writestr("api/__init__.py", "")

        # Arquivos em diretórios IGNORADOS — não devem aparecer na análise AST
        zf.writestr("tests/test_main.py", MOCK_TEST_PY)
        zf.writestr("docs/conf.py", MOCK_DOCS_PY)
        zf.writestr(".venv/lib/site-packages/requests/__init__.py", "# venv file")

    return zip_path


def build_minimal_clean_zip(tmp_path: Path) -> Path:
    """
    Constrói um ZIP mínimo sem zumbis, fantasmas ou desatualizados —
    para testar o caminho feliz de projeto saudável.
    """
    zip_path = tmp_path / "clean_project.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("requirements.txt", "click>=8.0.0\n")
        zf.writestr("main.py", "import click\n\ndef main(): click.echo('ok')\n")
    return zip_path


def get_fake_pypi_response(package: str) -> dict[str, Any]:
    """Simula resposta da API do PyPI para testes sem acesso real à internet."""
    versions: dict[str, Any] = {
        "requests": {"latest_version": "2.31.0", "days_outdated": 120},
        "numpy": {"latest_version": "1.26.0", "days_outdated": 80},
        "pandas": {"latest_version": "2.1.0", "days_outdated": 30},
        "flask": {"latest_version": "3.0.0", "days_outdated": 200},
        "sqlalchemy": {"latest_version": "2.0.23", "days_outdated": 15},
        "pillow": {"latest_version": "10.1.0", "days_outdated": 0},
        "celery": {"latest_version": "5.3.6", "days_outdated": 45},
        "zombie-package": {"latest_version": "1.0.0", "days_outdated": 0},
        "click": {"latest_version": "8.1.7", "days_outdated": 60},
        "rich": {"latest_version": "13.7.0", "days_outdated": 10},
        "httpx": {"latest_version": "0.25.2", "days_outdated": 5},
    }
    return versions.get(package, {"latest_version": "unknown", "days_outdated": 0})


# ──────────────────────────────────────────────────────────────────────────────
# Testes E2E — Repositório Pesado (com zumbi, fantasma, desatualizados)
# ──────────────────────────────────────────────────────────────────────────────

def test_e2e_extracao_filtragem_completa(tmp_path: Path) -> None:
    """
    E2E: ZIP → extração → filtro.
    Verifica que apenas arquivos .py fora de dirs ignorados são retornados.
    """
    zip_path = build_heavy_mock_zip(tmp_path)
    sid = "e2e-filter-sprint4"

    extract_dir = extract_zip(zip_path, session_id=sid)
    py_files = filter_extracted(extract_dir)

    try:
        # Arquivos em tests/, docs/, .venv/ não devem aparecer
        relative_paths = {str(f.relative_to(extract_dir)) for f in py_files}
        for path in relative_paths:
            assert "tests" not in path.split("/"), f"Arquivo de tests/ não deveria aparecer: {path}"
            assert "docs" not in path.split("/"), f"Arquivo de docs/ não deveria aparecer: {path}"
            assert ".venv" not in path.split("/"), f"Arquivo de .venv/ não deveria aparecer: {path}"

        # Arquivos do código-fonte devem aparecer
        assert any("main.py" in p for p in relative_paths), "src/main.py deve ser incluído"
        assert any("utils.py" in p for p in relative_paths), "src/utils.py deve ser incluído"
    finally:
        cleanup_session(sid)


def test_e2e_analise_detecta_zumbi(tmp_path: Path) -> None:
    """
    E2E: ZIP → extração → análise.
    Verifica que 'zombie-package' é detectado como zumbi (declarado mas não importado).
    """
    zip_path = build_heavy_mock_zip(tmp_path)
    sid = "e2e-zombie-sprint4"

    extract_dir = extract_zip(zip_path, session_id=sid)

    try:
        with patch("src.clients.pypi_client.fetch_latest_version") as mock_pypi:
            mock_pypi.side_effect = lambda pkg: get_fake_pypi_response(pkg)
            result = run_analysis(str(extract_dir))

        zombies = result.get("dependencies", {}).get("zombies", [])
        zombie_names = [z.lower() for z in zombies]

        assert any("zombie" in z for z in zombie_names), (
            f"'zombie-package' deve ser detectado como zumbi. Zumbis encontrados: {zombies}"
        )
    finally:
        cleanup_session(sid)


def test_e2e_analise_detecta_fantasma(tmp_path: Path) -> None:
    """
    E2E: ZIP → extração → análise.
    Verifica que 'boto3' é detectado como fantasma (importado mas não declarado).
    """
    zip_path = build_heavy_mock_zip(tmp_path)
    sid = "e2e-ghost-sprint4"

    extract_dir = extract_zip(zip_path, session_id=sid)

    try:
        with patch("src.clients.pypi_client.fetch_latest_version") as mock_pypi:
            mock_pypi.side_effect = lambda pkg: get_fake_pypi_response(pkg)
            result = run_analysis(str(extract_dir))

        ghosts = result.get("dependencies", {}).get("ghosts", [])
        ghost_names = [g.lower() for g in ghosts]

        assert "boto3" in ghost_names, (
            f"'boto3' deve ser detectado como fantasma. Fantasmas encontrados: {ghosts}"
        )
    finally:
        cleanup_session(sid)


def test_e2e_modelo_de_resultado_completo(tmp_path: Path) -> None:
    """
    E2E: Verifica que o dicionário de resultado contém todas as chaves
    obrigatórias do modelo padronizado do orquestrador.
    """
    zip_path = build_heavy_mock_zip(tmp_path)
    sid = "e2e-model-sprint4"

    extract_dir = extract_zip(zip_path, session_id=sid)

    try:
        with patch("src.clients.pypi_client.fetch_latest_version") as mock_pypi:
            mock_pypi.side_effect = lambda pkg: get_fake_pypi_response(pkg)
            result = run_analysis(str(extract_dir))

        # Verifica estrutura do modelo de resultado
        assert "project_info" in result, "Campo 'project_info' obrigatório"
        assert "dependencies" in result, "Campo 'dependencies' obrigatório"
        assert "statistics" in result, "Campo 'statistics' obrigatório"

        deps = result["dependencies"]
        for key in ("declared", "imported", "zombies", "ghosts", "outdated"):
            assert key in deps, f"Campo 'dependencies.{key}' obrigatório"

        stats = result["statistics"]
        for key in ("total_declared", "total_imported", "total_zombies", "total_ghosts", "total_outdated"):
            assert key in stats, f"Campo 'statistics.{key}' obrigatório"
    finally:
        cleanup_session(sid)


def test_e2e_estatisticas_coerentes(tmp_path: Path) -> None:
    """
    E2E: Verifica que as estatísticas retornadas são numericamente coerentes
    com as listas de dependências presentes no resultado.
    """
    zip_path = build_heavy_mock_zip(tmp_path)
    sid = "e2e-stats-sprint4"

    extract_dir = extract_zip(zip_path, session_id=sid)

    try:
        with patch("src.clients.pypi_client.fetch_latest_version") as mock_pypi:
            mock_pypi.side_effect = lambda pkg: get_fake_pypi_response(pkg)
            result = run_analysis(str(extract_dir))

        deps = result["dependencies"]
        stats = result["statistics"]

        assert stats["total_declared"] == len(deps["declared"])
        assert stats["total_imported"] == len(deps["imported"])
        assert stats["total_zombies"] == len(deps["zombies"])
        assert stats["total_ghosts"] == len(deps["ghosts"])
        assert stats["total_outdated"] == len(deps["outdated"])
    finally:
        cleanup_session(sid)


# ──────────────────────────────────────────────────────────────────────────────
# Testes E2E — Projeto Limpo (caminho feliz)
# ──────────────────────────────────────────────────────────────────────────────

def test_e2e_projeto_limpo_sem_problemas(tmp_path: Path) -> None:
    """
    E2E: Projeto saudável (sem zumbi, sem fantasma) deve retornar listas vazias
    para zombies e ghosts.
    """
    zip_path = build_minimal_clean_zip(tmp_path)
    sid = "e2e-clean-sprint4"

    extract_dir = extract_zip(zip_path, session_id=sid)

    try:
        with patch("src.clients.pypi_client.fetch_latest_version") as mock_pypi:
            mock_pypi.side_effect = lambda pkg: {"latest_version": "8.1.7", "days_outdated": 0}
            result = run_analysis(str(extract_dir))

        zombies = result.get("dependencies", {}).get("zombies", [])
        ghosts = result.get("dependencies", {}).get("ghosts", [])

        assert len(zombies) == 0, f"Projeto limpo não deve ter zumbis: {zombies}"
        assert len(ghosts) == 0, f"Projeto limpo não deve ter fantasmas: {ghosts}"
    finally:
        cleanup_session(sid)


def test_e2e_analise_com_erro_pypi_nao_quebra_pipeline(tmp_path: Path) -> None:
    """
    E2E: Instabilidade HTTP no PyPI não deve derrubar o pipeline.
    As análises de zumbi e fantasma devem continuar funcionando.
    """
    zip_path = build_heavy_mock_zip(tmp_path)
    sid = "e2e-pypi-fail-sprint4"

    extract_dir = extract_zip(zip_path, session_id=sid)

    try:
        with patch("src.clients.pypi_client.fetch_latest_version", side_effect=Exception("timeout")):
            # O pipeline não deve lançar exceção
            result = run_analysis(str(extract_dir))

        # Zumbis e fantasmas ainda devem ser calculados
        assert "zombies" in result.get("dependencies", {})
        assert "ghosts" in result.get("dependencies", {})
    finally:
        cleanup_session(sid)
