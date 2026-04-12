"""
src/parsers/requirements_parser.py  –  Dev 3 | Sprint 1
Extrai as dependências declaradas em um requirements.txt (ou variante).
Ignora comentários, linhas vazias e flags do pip (-r, -e, --index-url…).
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_PKG_NAME_RE = re.compile(r"^([A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)")
_SKIP_PREFIXES = ("-r ", "-e ", "--", "#", "http://", "https://")


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "_", name).lower()


def parse_requirements(file_path: Path) -> dict[str, str]:
    """
    Lê um requirements.txt e retorna as dependências declaradas.

    Args:
        file_path: Caminho para o requirements.txt.

    Returns:
        Dicionário {nome_normalizado: especificador_versão_raw}.

    Raises:
        FileNotFoundError: se o arquivo não existir.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"requirements.txt não encontrado: {file_path}")

    deps: dict[str, str] = {}
    lines = file_path.read_text(encoding="utf-8").splitlines()

    for raw_line in lines:
        line = raw_line.strip()

        # Ignora linhas vazias, comentários e flags do pip
        if not line or any(line.startswith(p) for p in _SKIP_PREFIXES):
            continue

        # Remove comentário inline
        line = line.split("#")[0].strip()

        m = _PKG_NAME_RE.match(line)
        if not m:
            continue

        pkg_name = _normalize(m.group(1))
        version_part = line[m.end():].strip()  # ex: ">=2.0,<3.0" ou ""
        deps[pkg_name] = version_part

    logger.info("requirements.txt: %d dependência(s) encontrada(s).", len(deps))
    return deps
