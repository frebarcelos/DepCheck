"""
core/constants.py
Constantes globais do projeto, carregadas do arquivo .env via python-dotenv.
Todas as constantes devem ser importadas diretamente deste módulo.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Carrega variáveis do .env na raiz do projeto
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# ── Ambiente ──────────────────────────────────────────────────────────────────
APP_ENV: str = os.getenv("APP_ENV", "development")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# ── Upload ────────────────────────────────────────────────────────────────────
MAX_ZIP_SIZE_MB: int = int(os.getenv("MAX_ZIP_SIZE_MB", "50"))
MAX_ZIP_SIZE_BYTES: int = MAX_ZIP_SIZE_MB * 1024 * 1024
# Razão máxima descomprimido/comprimido para detecção de zip-bomb
MAX_ZIP_RATIO: int = int(os.getenv("MAX_ZIP_RATIO", "100"))

# ── Extensões / Diretórios varridos ───────────────────────────────────────────
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".py"})
IGNORED_DIRS: frozenset[str] = frozenset(
    {"tests", "test", "docs", "doc", ".venv", "venv", "env", "__pycache__", ".git", "build", "dist"}
)
IGNORED_FILES: frozenset[str] = frozenset({"setup.py", "conftest.py"})

# ── Formatos de arquivo de dependências suportados ────────────────────────────
REQUIREMENTS_FILES: frozenset[str] = frozenset({"requirements.txt", "requirements-dev.txt"})
PYPROJECT_FILE: str = "pyproject.toml"

# ── Metadados enriquecidos / PyPI ──────────────────────────────────────────────
# Sentinel usado quando o tamanho de um pacote no PyPI não está disponível.
SIZE_UNKNOWN: int = -1

# Diretórios excluídos por padrão durante a varredura — exibidos na GUI como opções.
DEFAULT_EXCLUDED_DIRS: list[str] = [
    "tests",
    "test",
    "docs",
    "doc",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".git",
    "build",
    "dist",
]
