"""
tests/mocker.py  –  Dev 3 | Sprint 1
Gera dados mockados para testes usando a biblioteca Faker.
Provê dicionários com o mesmo formato de saída dos parsers e analisadores.
"""
from __future__ import annotations

import random
from typing import Any

from faker import Faker

_fake = Faker()

# Pacotes realistas para os mocks
_SAMPLE_PACKAGES = [
    "requests", "numpy", "pandas", "flask", "django", "fastapi",
    "sqlalchemy", "pydantic", "pytest", "click", "rich", "httpx",
    "boto3", "pillow", "celery", "redis", "aiohttp", "uvicorn",
    "cryptography", "paramiko", "faker", "toml", "python_dotenv",
    "streamlit", "plotly", "altair", "mypy", "ruff", "black",
]

_COMMON_IMPORTS = [
    "os", "sys", "json", "re", "math", "datetime", "pathlib",
    "logging", "typing", "collections", "itertools", "functools",
    "abc", "io", "time", "uuid", "hashlib", "base64",
]


def generate_mock_declared(n: int = 10) -> dict[str, str]:
    """
    Gera um dicionário simulando a saída dos parsers (dependências declaradas).

    Returns:
        {nome_pacote: versão_raw}, ex: {"requests": ">=2.28.0"}
    """
    packages = random.sample(_SAMPLE_PACKAGES, min(n, len(_SAMPLE_PACKAGES)))
    versions = [
        f">={random.randint(1, 3)}.{random.randint(0, 20)}.{random.randint(0, 5)}"
        for _ in packages
    ]
    return dict(zip(packages, versions))


def generate_mock_imports(
    declared: dict[str, str] | None = None,
    extra_zombies: int = 2,
    extra_ghosts: int = 2,
) -> set[str]:
    """
    Gera um conjunto simulando os imports encontrados no código-fonte.

    Args:
        declared: Dependências declaradas (para criar importações realistas).
        extra_zombies: Quantidade de deps declaradas que NÃO aparecem como import (zumbis).
        extra_ghosts: Quantidade de imports que NÃO estão declarados (fantasmas).

    Returns:
        Set de nomes de módulos importados.
    """
    declared_names = list((declared or {}).keys())

    # Zumbis: remove alguns imports das declaradas
    zombie_count = min(extra_zombies, len(declared_names))
    real_imports = set(declared_names[zombie_count:])

    # Stdlib: sempre presentes nos imports
    real_imports |= set(random.sample(_COMMON_IMPORTS, 5))

    # Fantasmas: importados mas não declarados
    existing_names = set(_SAMPLE_PACKAGES) | set(_COMMON_IMPORTS)
    ghost_pool = [p for p in _SAMPLE_PACKAGES if p not in real_imports]
    real_imports |= set(random.sample(ghost_pool, min(extra_ghosts, len(ghost_pool))))

    return real_imports


def generate_mock_analysis_result(n_packages: int = 12) -> dict[str, Any]:
    """
    Gera um dicionário completo simulando a saída do orquestrador.

    Returns:
        {
          "declared": {pkg: version},
          "imported": [pkg, ...],
          "zombies": [pkg, ...],
          "ghosts": [pkg, ...],
        }
    """
    declared = generate_mock_declared(n_packages)
    imported = generate_mock_imports(declared, extra_zombies=2, extra_ghosts=3)

    declared_set = set(declared.keys())
    imported_clean = {p for p in imported if p not in _COMMON_IMPORTS}

    zombies = list(declared_set - imported_clean)
    ghosts = list(imported_clean - declared_set)

    return {
        "declared": declared,
        "imported": sorted(imported),
        "zombies": zombies,
        "ghosts": ghosts,
    }
