"""
src/filter.py  –  Dev 2 | Sprint 1 / Sprint 4
Rotina para limpar arquivos inúteis após a extração de um ZIP.
Remove arquivos fora de SUPPORTED_EXTENSIONS e diretórios em IGNORED_DIRS.
Sprint 4: suporta lista adicional de diretórios a ignorar, configurável via GUI.
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from core.constants import IGNORED_DIRS, IGNORED_FILES, SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)


def filter_extracted(
    root_dir: Path,
    extra_excluded_dirs: list[str] | None = None,
) -> list[Path]:
    """
    Percorre root_dir recursivamente e remove:
      - Diretórios cujo nome está em IGNORED_DIRS ou em extra_excluded_dirs.
      - Arquivos que não possuem extensão em SUPPORTED_EXTENSIONS.
      - Arquivos cujo nome está em IGNORED_FILES.

    Args:
        root_dir: Raiz do diretório extraído.
        extra_excluded_dirs: Lista adicional de nomes de diretórios a ignorar,
            fornecida pela GUI do usuário. Quando None ou vazia, comporta-se
            exatamente como antes (retrocompatível).

    Returns:
        Lista dos arquivos .py mantidos após a limpeza.
    """
    if not root_dir.is_dir():
        raise ValueError(f"'{root_dir}' não é um diretório válido.")

    # Combina os diretórios ignorados padrão com os extras fornecidos pelo usuário
    effective_ignored: frozenset[str]
    if extra_excluded_dirs:
        effective_ignored = IGNORED_DIRS | frozenset(extra_excluded_dirs)
    else:
        effective_ignored = IGNORED_DIRS

    kept: list[Path] = []

    # Primeiro passo: remove diretórios ignorados (top-down)
    for item in sorted(root_dir.rglob("*"), key=lambda p: len(p.parts)):
        if item.exists() and item.is_dir() and item.name in effective_ignored:
            logger.debug("Removendo diretório ignorado: %s", item)
            shutil.rmtree(item)

    # Segundo passo: coleta arquivos .py relevantes
    # NÃO deleta outros tipos de arquivo — manifests como pyproject.toml e
    # requirements.txt precisam sobreviver para o parser do orquestrador.
    for item in root_dir.rglob("*"):
        if not item.is_file():
            continue
        if item.name in IGNORED_FILES:
            continue
        if item.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        kept.append(item)

    logger.info(
        "Filtro concluído em '%s': %d arquivo(s) .py mantido(s).", root_dir, len(kept)
    )
    return kept
