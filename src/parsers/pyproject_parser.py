"""
src/parsers/pyproject_parser.py  –  Dev 3 | Sprint 1
Extrai as dependências declaradas em um arquivo pyproject.toml.
Suporta [project].dependencies e [tool.poetry.dependencies].
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import toml

logger = logging.getLogger(__name__)

# Regex para extrair apenas o nome do pacote, ignorando versão/extras
# Exemplos: "requests>=2.0", "Pillow[jpg]~=9.0", "numpy"
_PKG_NAME_RE = re.compile(r"^([A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)")


def _normalize(name: str) -> str:
    """Normaliza nome de pacote: lowercase e hífens → underscores."""
    return re.sub(r"[-_.]+", "_", name).lower()


def _extract_name(dep: str) -> str | None:
    """Extrai o nome do pacote de uma string de dependência."""
    m = _PKG_NAME_RE.match(dep.strip())
    return _normalize(m.group(1)) if m else None


def parse_pyproject(file_path: Path) -> dict[str, str]:
    """
    Lê um pyproject.toml e retorna as dependências declaradas.

    Args:
        file_path: Caminho para o pyproject.toml.

    Returns:
        Dicionário {nome_normalizado: versão_raw}.
        Versão raw é a string original (ex: ">=2.0") ou "" se não especificada.

    Raises:
        FileNotFoundError: se o arquivo não existir.
        ValueError: se o arquivo não puder ser interpretado.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"pyproject.toml não encontrado: {file_path}")

    try:
        data: dict = toml.loads(file_path.read_text(encoding="utf-8"))
    except toml.TomlDecodeError as exc:
        raise ValueError(f"Erro ao parse do TOML: {exc}") from exc

    deps: dict[str, str] = {}

    # PEP 621 (uv, pip, hatch, flit…)
    pep621: list[str] = data.get("project", {}).get("dependencies", [])
    for raw in pep621:
        name = _extract_name(raw)
        if name:
            deps[name] = raw.strip()

    # Poetry
    poetry_deps: dict = (
        data.get("tool", {}).get("poetry", {}).get("dependencies", {})
    )
    for pkg, ver in poetry_deps.items():
        if pkg.lower() == "python":
            continue
        name = _normalize(pkg)
        deps.setdefault(name, str(ver) if not isinstance(ver, dict) else "")

    logger.info("pyproject.toml: %d dependência(s) encontrada(s).", len(deps))
    return deps
