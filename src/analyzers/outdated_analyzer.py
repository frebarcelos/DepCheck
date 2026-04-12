"""
src/analyzers/outdated_analyzer.py  –  Dev 3 | Sprint 2 | Sprint 4
Verifica a defasagem (em dias) das dependências declaradas em relação às
versões mais recentes disponíveis no índice PyPI.
Expansão Sprint 4: inclui size_bytes no resultado.

Paradigma: Procedimental — apenas funções, sem classes de domínio.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from src.clients.pypi_client import fetch_package_size, get_pypi_package_info

logger = logging.getLogger(__name__)

# Formatos de data aceitos pelo parser (PyPI às vezes inclui microsegundos)
_PYPI_DATE_FMTS: tuple[str, ...] = (
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
)


def _extract_package_name(dep: str) -> str:
    """
    Extrai o nome normalizado de um pacote a partir de sua string de dependência.

    Args:
        dep: String bruta de dependência (ex: "Django>=3.2", "requests==2.28.0").

    Returns:
        Nome do pacote em lowercase sem versão, extras ou operadores.
    """
    parts = re.split(r"[=><~!\[\s]", dep)
    return parts[0].strip().lower() if parts else dep.strip().lower()


def _extract_declared_version(dep: str) -> str | None:
    """
    Extrai a versão declarada de uma string de dependência.

    Reconhece ``==``, ``>=``, ``~=`` e ``<=``. Retorna None quando nenhum
    operador de versão está presente.

    Args:
        dep: String bruta de dependência (ex: "requests>=2.28.0").

    Returns:
        String da versão (ex: "2.28.0") ou None se não houver versão declarada.
    """
    match = re.search(r"[><=~!]{1,2}\s*([0-9][^\s,;]*)", dep)
    return match.group(1).strip() if match else None


def _version_tuple(version_str: str) -> tuple[int, ...]:
    """
    Converte uma string de versão em tupla de inteiros para comparação.

    Parte não numérica (ex: ".post1", "rc1") é ignorada.

    Args:
        version_str: String de versão (ex: "2.28.0").

    Returns:
        Tupla de inteiros (ex: (2, 28, 0)).
    """
    parts = re.split(r"[.\-]", version_str)
    result: list[int] = []
    for p in parts:
        m = re.match(r"(\d+)", p)
        if m:
            result.append(int(m.group(1)))
    return tuple(result) if result else (0,)


def _version_is_outdated(declared: str | None, latest: str) -> bool:
    """
    Retorna True se a versão declarada for anterior à versão latest do PyPI.

    Quando nenhuma versão está declarada (dep sem operador), considera
    que o pacote pode estar desatualizado e retorna True.

    Args:
        declared: Versão declarada no projeto (pode ser None).
        latest: Versão mais recente disponível no PyPI.

    Returns:
        True se declared < latest ou declared é None.
    """
    if declared is None:
        return True
    return _version_tuple(declared) < _version_tuple(latest)


def _parse_upload_date(upload_time_str: str) -> datetime | None:
    """
    Converte a string de data do PyPI para um objeto datetime.

    Tenta múltiplos formatos para lidar com datas com e sem microsegundos.

    Args:
        upload_time_str: String de data retornada pelo PyPI.

    Returns:
        Objeto datetime ou None se o parse falhar em todos os formatos.
    """
    for fmt in _PYPI_DATE_FMTS:
        try:
            return datetime.strptime(upload_time_str, fmt)
        except ValueError:
            continue
    logger.debug("Formato de data não reconhecido: '%s'", upload_time_str)
    return None


def _compute_days_since(upload_time: datetime) -> int:
    """
    Calcula quantos dias se passaram desde uma data de upload.

    Args:
        upload_time: Data de referência.

    Returns:
        Número de dias (>= 0).
    """
    return max(0, (datetime.now() - upload_time).days)


def check_outdated_dependencies(declared_deps: list[str]) -> dict[str, dict[str, Any]]:
    """
    Cruza as dependências declaradas com o índice online do PyPI e identifica
    as que estão desatualizadas em relação à versão 'latest' de cada pacote.

    Um pacote é considerado desatualizado quando a versão declarada no projeto
    é anterior (numericamente) à versão mais recente disponível no PyPI.
    Quando o projeto não declara versão para um pacote, assume-se desatualizado.

    Dependências não encontradas no PyPI ou com dados incompletos são ignoradas
    silenciosamente (sem lançar exceção), garantindo robustez do pipeline.

    Args:
        declared_deps: Lista de strings brutas de dependência declaradas
                       (ex: ["requests>=2.28.0", "numpy>=1.24.0"]).

    Returns:
        Dicionário indexado por nome do pacote — **apenas** pacotes cujos
        dados indicam desatualização:
        {
            "nome_pacote": {
                "latest_version": "X.Y.Z",
                "declared_version": "A.B.C" | None,
                "days_outdated": N,
                "size_bytes": M
            }
        }
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
        declared_version = _extract_declared_version(dep)

        # Só incluir se houver desatualização real
        if not _version_is_outdated(declared_version, latest_version):
            logger.debug(
                "'%s' está atualizado: declarado=%s latest=%s",
                base_name,
                declared_version,
                latest_version,
            )
            continue

        releases: dict[str, list[dict[str, Any]]] = info.get("releases", {})

        # Preferir a data da versão declarada; cair na versão latest se indisponível
        ref_version = declared_version if declared_version and declared_version in releases else latest_version
        ref_files: list[dict[str, Any]] = releases.get(ref_version, [])

        upload_time: datetime | None = None
        for file_info in ref_files:
            upload_time_str: str | None = file_info.get("upload_time")
            if upload_time_str:
                upload_time = _parse_upload_date(upload_time_str)
                if upload_time:
                    break

        days_outdated = _compute_days_since(upload_time) if upload_time else 0

        size_bytes = fetch_package_size(base_name, latest_version)

        outdated_info[base_name] = {
            "latest_version": latest_version,
            "declared_version": declared_version,
            "days_outdated": days_outdated,
            "size_bytes": size_bytes,
        }

    logger.info(
        "outdated_analyzer: %d/%d pacote(s) desatualizado(s) encontrado(s).",
        len(outdated_info),
        len(declared_deps),
    )
    return outdated_info
