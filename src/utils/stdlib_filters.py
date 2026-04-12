"""
src/utils/stdlib_filters.py  –  Dev 2 | Sprint 2 | Auditoria Dev 4 Sprint 4
Utilitário para remover módulos da Standard Library CPython da lista de
imports detectados via AST, evitando falsos positivos no Ghost Analyzer.

Paradigma: Procedimental — apenas funções, sem classes de domínio.
"""
from __future__ import annotations

import sys


def get_stdlib_module_names() -> frozenset[str]:
    """
    Retorna o conjunto de nomes de módulos da Standard Library CPython.

    Em Python >= 3.10, usa ``sys.stdlib_module_names`` (fonte oficial).
    Em versões anteriores, retorna um conjunto vazio (comportamento degradado).

    Returns:
        FrozenSet de nomes de módulos da stdlib (ex: 'os', 'sys', 'json').
    """
    if hasattr(sys, "stdlib_module_names"):
        return frozenset(sys.stdlib_module_names)
    return frozenset()


def filter_stdlib_imports(imports: set[str]) -> set[str]:
    """
    Remove módulos da Standard Library CPython de um conjunto de imports detectados.

    Compara o módulo raiz de cada import (parte antes do primeiro ponto) contra
    a lista de módulos da stdlib. Isso garante que subimports como 'os.path'
    sejam corretamente identificados como stdlib.

    Args:
        imports: Conjunto de nomes de módulo raiz detectados via AST
                 (ex: {'requests', 'os', 'json', 'flask'}).

    Returns:
        Subconjunto de ``imports`` sem os módulos da Standard Library.
        Ex: {'requests', 'flask'} (removendo 'os', 'json').
    """
    stdlib = get_stdlib_module_names()
    return {imp for imp in imports if imp.split(".")[0] not in stdlib}
