"""
src/analyzers/ghost_analyzer.py  –  Dev 2 | Sprint 2 | Auditoria Dev 4 Sprint 4
Identifica dependências "Fantasmas": módulos ativamente importados no código
via AST que não estão declarados nos arquivos de manifesto do projeto.

Paradigma: Procedimental — apenas funções, sem classes de domínio.
"""
from __future__ import annotations

import re

from src.utils.stdlib_filters import filter_stdlib_imports


def _clean_declared_names(declared_deps: list[str]) -> set[str]:
    """
    Normaliza a lista de dependências declaradas para nomes de pacote limpos.

    Exemplo: "Django>=3.2" → "django", "Pillow[jpg]~=9.0" → "pillow".

    Args:
        declared_deps: Lista de strings brutas de dependência (ex: "requests>=2.28.0").

    Returns:
        Conjunto de nomes de pacote normalizados (lowercase, sem versão).
    """
    clean: set[str] = set()
    for dep in declared_deps:
        parts = re.split(r"[=><~\[]", dep)
        base = parts[0].strip().lower() if parts else dep.strip().lower()
        if base:
            clean.add(base)
    return clean


def find_ghost_dependencies(declared_deps: list[str], imported_modules: set[str]) -> list[str]:
    """
    Identifica dependências "Fantasmas": módulos importados no código-fonte
    (detectados via AST) que não estão declarados nas dependências do projeto.

    Módulos da Standard Library são removidos antes da comparação para
    evitar falsos positivos (ex: 'os', 'json', 'sys').

    Args:
        declared_deps: Lista de dependências declaradas (formato bruto, ex: "requests>=2.0").
        imported_modules: Conjunto de nomes de módulo raiz encontrados via AST.

    Returns:
        Lista de nomes de módulo classificados como fantasmas (importados mas não declarados).
    """
    filtered_imports = filter_stdlib_imports(imported_modules)
    clean_declared = _clean_declared_names(declared_deps)

    ghosts: list[str] = []
    for imp in filtered_imports:
        base_imp = imp.split(".")[0].lower()
        if base_imp not in clean_declared:
            ghosts.append(imp)

    return ghosts
