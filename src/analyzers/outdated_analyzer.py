"""
src/analyzers/outdated_analyzer.py  –  Dev 3 | Sprint 2 | Auditoria Dev 4 Sprint 4
Verifica a defasagem (em dias) das dependências declaradas em relação às
versões mais recentes disponíveis no índice PyPI.

Paradigma: Procedimental — apenas funções, sem classes de domínio.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from src.clients.pypi_client import get_pypi_package_info

logger = logging.getLogger(__name__)

# Formato de data usado pelo PyPI na chave "upload_time"
_PYPI_DATE_FMT: str = "%Y-%m-%dT%H:%M:%S"


def _extract_package_name(dep: str) -> str:
    """
    Extrai o nome normalizado de um pacote a partir de sua string de dependência.

    Args:
        dep: String bruta de dependência (ex: "Django>=3.2", "requests==2.28.0").

    Returns:
        Nome do pacote em lowercase sem versão, extras ou operadores.
    """
    parts = re.split(r"[=><~\[]", dep)
    return parts[0].strip().lower() if parts else dep.strip().lower()


def _parse_upload_date(upload_time_str: str) -> datetime | None:
    """
    Converte a string de data do PyPI para um objeto datetime.

    Args:
        upload_time_str: String de data no formato '%Y-%m-%dT%H:%M:%S'.

    Returns:
        Objeto datetime ou None se o parse falhar.
    """
    try:
        return datetime.strptime(upload_time_str, _PYPI_DATE_FMT)
    except ValueError:
        logger.debug("Formato de data inválido: '%s'", upload_time_str)
        return None


def _compute_days_outdated(upload_time: datetime) -> int:
    """
    Calcula quantos dias se passaram desde o lançamento da versão mais recente.

    Args:
        upload_time: Data de upload da versão latest no PyPI.

    Returns:
        Número de dias de defasagem (>= 0).
    """
    return max(0, (datetime.now() - upload_time).days)


def check_outdated_dependencies(declared_deps: list[str]) -> dict[str, dict[str, Any]]:
    """
    Cruza as dependências declaradas com o índice online do PyPI e calcula
    a defasagem em dias em relação à versão 'latest' de cada pacote.

    Dependências não encontradas no PyPI ou com dados incompletos são ignoradas
    silenciosamente (sem lançar exceção), garantindo robustez do pipeline.

    Args:
        declared_deps: Lista de strings brutas de dependência declaradas
                       (ex: ["requests>=2.28.0", "numpy>=1.24.0"]).

    Returns:
        Dicionário indexado por nome do pacote:
        {
            "nome_pacote": {
                "latest_version": "X.Y.Z",
                "days_outdated": N
            }
        }
        Apenas pacotes com dados válidos são incluídos.
    """
    outdated_info: dict[str, dict[str, Any]] = {}

    for dep in declared_deps:
        base_name = _extract_package_name(dep)
        if not base_name:
            continue

        info = get_pypi_package_info(base_name)
        if not info or "info" not in info or "releases" not in info:
            logger.debug("Dados PyPI indisponíveis para '%s'", base_name)
            continue

        latest_version: str = info["info"]["version"]
        releases: dict[str, list[dict[str, Any]]] = info.get("releases", {})
        latest_files: list[dict[str, Any]] = releases.get(latest_version, [])

        if not latest_files:
            continue

        upload_time_str: str | None = latest_files[0].get("upload_time")
        if not upload_time_str:
            continue

        upload_time = _parse_upload_date(upload_time_str)
        if upload_time is None:
            continue

        outdated_info[base_name] = {
            "latest_version": latest_version,
            "days_outdated": _compute_days_outdated(upload_time),
        }

    logger.info(
        "outdated_analyzer: %d/%d pacote(s) com dados de versão disponíveis.",
        len(outdated_info),
        len(declared_deps),
    )
    return outdated_info
