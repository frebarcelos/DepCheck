"""
src/code_parser.py  –  Dev 4 | Sprint 1
Varre arquivos .py usando a lib AST do Python para extrair
apenas as linhas de import reais (import X / from X import Y).
Retorna um conjunto normalizado de nomes de módulos de nível raiz.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path

from core.constants import IGNORED_DIRS, IGNORED_FILES, SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)


def _extract_imports_from_file(file_path: Path) -> set[str]:
    """
    Parseia um arquivo .py e retorna os imports de nível raiz
    """
    results = set()
    code = file_path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        logger.warning("SyntaxError em '%s': %s — arquivo ignorado.", file_path, exc)
        return set()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Erro ao ler '%s': %s — arquivo ignorado.", file_path, exc)
        return set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                results.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and (node.module and node.level == 0):
            results.add(node.module.split(".")[0])
    return results


def parse_imports(root_dir: Path) -> dict[str, set[str]]:
    """
    recebe um diretorio e utiliza chamada a funcao _extract_from_file em todos
    os arquivos .py ignorando arquivos e diretorios definidos previamente em core/constants.py
    """

    if not root_dir.is_dir():
        raise ValueError(f"'{root_dir}' não é um diretório válido.")

    results = {}
    for file in root_dir.rglob("*.py"):
        if file.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        if any(part in IGNORED_DIRS for part in file.parts):
            continue
        if file.name in IGNORED_FILES:
            continue
        imports = _extract_imports_from_file(file)
        if imports:
            results[str(file.relative_to(root_dir))] = imports
            logger.debug("%s → %d import(s)", file.relative_to(root_dir), len(imports))
    total_imports = {mod for mods in results.values() for mod in mods}
    logger.info(
        "code_parser: %d arquivo(s) | %d import(s) únicos encontrados.",
        len(results),
        len(total_imports),
    )
    return results


def get_all_imports(root_dir: Path) -> set[str]:
    """
    retorna todos os imports do projeto sem separar por arquivo
    """
    results = set()
    results_parse = parse_imports(root_dir)
    for valor in results_parse.values():
        results |= valor
    return results


if __name__ == "__main__":
    print("=============================================")
    print("Resultados:")
    print(get_all_imports(Path(".")))
