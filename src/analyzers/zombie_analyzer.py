from __future__ import annotations

import re

from core.aliases import IMPORT_TO_PACKAGE


def extract_package_name(dep: str) -> str:
    """Extrai o nome limpo (normalizado) de uma string de dependência Python.

    Remove especificadores de versão (>=, ==, ~=, !=, <=, <, >) e extras
    opcionais entre colchetes (ex: ``[security]``), retornando o nome do
    pacote em minúsculas e com hífens convertidos para underscores conforme
    a convenção de normalização do PyPI.

    Args:
        dep: String de dependência no formato PEP 508, por exemplo
            ``"Django>=3.2"``, ``"requests[security]==2.28.0"``,
            ``"pillow"`` ou ``"my-package~=1.0"``.

    Returns:
        Nome do pacote em minúsculas sem especificadores de versão nem extras.
        Exemplos::

            extract_package_name("Django>=3.2")          # "django"
            extract_package_name("requests[security]")   # "requests"
            extract_package_name("my-package~=1.0")      # "my-package"
            extract_package_name("pillow")               # "pillow"
    """
    # Remove extras entre colchetes, ex: requests[security] -> requests
    dep = re.sub(r"\[.*?\]", "", dep)
    # Divide no primeiro especificador de versão (>=, ==, ~=, !=, <=, <, >)
    parts = re.split(r"[=><~!]", dep)
    return parts[0].strip().lower()


def find_zombie_dependencies(declared_deps: list[str], imported_modules: set[str]) -> list[str]:
    """Identifica dependências declaradas que não possuem nenhum import correspondente.

    Compara os pacotes declarados nos arquivos de manifesto (ex: ``pyproject.toml``,
    ``requirements.txt``) contra os módulos efetivamente importados no código-fonte
    (extraídos via AST). Pacotes declarados mas nunca importados são classificados
    como "zumbis".

    Args:
        declared_deps: Lista de strings de dependências declaradas, podendo conter
            especificadores de versão (ex: ``["Django>=3.2", "requests", "numpy"]``).
        imported_modules: Conjunto de nomes de módulos importados encontrados no
            código-fonte via análise AST.

    Returns:
        Lista das strings de dependência originais (sem modificação) que foram
        consideradas zumbis — preservando o formato original para exibição na GUI.
    """
    zombies = []

    # Resolve cada import para seu nome de pacote canônico.
    # IMPORT_TO_PACKAGE mapeia import→pacote (ex: "pil"→"pillow", "yaml"→"pyyaml"),
    # portanto normalizamos os imports, não os pacotes declarados.
    resolved_imports = {
        IMPORT_TO_PACKAGE.get(m.lower(), m.lower())
        for m in imported_modules
    }

    for dep in declared_deps:
        clean_dep = extract_package_name(dep)
        # Normaliza hífens/underscores para bater com os valores do IMPORT_TO_PACKAGE
        normalized_dep = re.sub(r"[-_.]+", "_", clean_dep)

        if normalized_dep not in resolved_imports:
            zombies.append(dep)

    return zombies
