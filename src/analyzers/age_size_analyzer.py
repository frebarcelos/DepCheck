from __future__ import annotations

import re
from datetime import datetime

from src.clients.pypi_client import fetch_package_size, fetch_release_date


def _extract_version_from_dep(dep: str) -> str | None:
    """Extrai a versão pinada de uma string de dependência.

    Reconhece apenas o operador ``==`` como versão pinada. Operadores
    relacionais (``>=``, ``<=``, ``~=``, etc.) não determinam uma versão
    exata e, portanto, retornam None.

    Args:
        dep: String de dependência bruta (ex: "requests==2.28.0").

    Returns:
        Versão pinada como string (ex: "2.28.0") ou None se não pinada.

    Examples:
        >>> _extract_version_from_dep("requests==2.28.0")
        '2.28.0'
        >>> _extract_version_from_dep("requests>=2.0")
        None
        >>> _extract_version_from_dep("numpy")
        None
    """
    match = re.search(r"==\s*([^\s,;]+)", dep)
    if match:
        return match.group(1).strip()
    return None


def _compute_age_from_date(release_date_str: str | None) -> int | None:
    """Calcula o número de dias desde a data de release até hoje.

    Args:
        release_date_str: Data no formato ISO 8601 sem timezone
            (ex: "2023-04-15T10:23:45") ou None.

    Returns:
        Número de dias (int >= 0) desde o release ou None se a data for
        inválida ou None.

    Examples:
        >>> _compute_age_from_date(None)
        None
        >>> _compute_age_from_date("not-a-date")
        None
    """
    if not release_date_str:
        return None
    try:
        release_dt = datetime.strptime(release_date_str, "%Y-%m-%dT%H:%M:%S")
        delta = datetime.now() - release_dt
        return max(0, delta.days)
    except Exception:
        return None


def format_size_human(size_bytes: int) -> str:
    """Formata um valor em bytes para uma string legível por humanos.

    Args:
        size_bytes: Tamanho em bytes. Use -1 para indicar valor indisponível.

    Returns:
        String formatada como "102 KB", "2.3 MB" ou "N/D" quando
        size_bytes == -1.

    Examples:
        >>> format_size_human(-1)
        'N/D'
        >>> format_size_human(500)
        '500 B'
        >>> format_size_human(102400)
        '100.0 KB'
        >>> format_size_human(2411724)
        '2.3 MB'
    """
    if size_bytes == -1:
        return "N/D"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024**2:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / 1024 ** 2:.1f} MB"


def compute_enriched_metadata(declared: list[str]) -> dict[str, dict]:
    """Para cada dependência declarada, busca no PyPI tamanho e idade.

    A função extrai o nome base do pacote (sem operadores de versão), consulta
    o PyPI via :func:`fetch_package_size` e :func:`fetch_release_date` e
    devolve um dicionário enriquecido.

    Args:
        declared: Lista de strings brutas de dependência
            (ex: ["requests>=2.28.0", "numpy"]).

    Returns:
        Dicionário cujas chaves são nomes de pacotes em lowercase e valores
        são dicts com:
        - ``size_bytes`` (int): tamanho do pacote em bytes (-1 se
          indisponível).
        - ``age_days`` (int | None): dias desde o lançamento da versão
          (None se indisponível).

    Examples:
        >>> result = compute_enriched_metadata(["requests==2.28.0"])
        >>> "requests" in result
        True
        >>> "size_bytes" in result["requests"]
        True
    """
    result: dict[str, dict] = {}

    for dep in declared:
        # Extrair nome base do pacote (ex: "Django>=3.2" -> "django")
        name_match = re.split(r"[=><~!@\s]", dep.strip())
        base_name = name_match[0].strip().lower() if name_match else dep.strip().lower()
        if not base_name:
            continue

        pinned_version = _extract_version_from_dep(dep)

        size_bytes = fetch_package_size(base_name, pinned_version)
        release_date = fetch_release_date(base_name, pinned_version)
        age_days = _compute_age_from_date(release_date)

        result[base_name] = {
            "size_bytes": size_bytes,
            "age_days": age_days,
        }

    return result
