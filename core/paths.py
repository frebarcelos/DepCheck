"""
core/paths.py
Caminhos absolutos e diretórios base do projeto.
Centraliza todo acesso ao sistema de arquivos; demais módulos importam daqui.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# ── Raiz do projeto ───────────────────────────────────────────────────────────
ROOT_DIR: Path = Path(__file__).parent.parent.resolve()

# ── Diretórios internos ───────────────────────────────────────────────────────
CORE_DIR: Path = ROOT_DIR / "core"
SRC_DIR: Path = ROOT_DIR / "src"
GUI_DIR: Path = ROOT_DIR / "gui"
TESTS_DIR: Path = ROOT_DIR / "tests"

# ── Diretório temporário (overridável por .env) ───────────────────────────────
_temp_env: str = os.getenv("TEMP_DIR", "")
TEMP_DIR: Path = Path(_temp_env).resolve() if _temp_env else Path("/tmp/depcheck")

# Garante que o diretório temporário existe ao importar o módulo
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_upload_dir(session_id: str) -> Path:
    """Retorna (e cria) um subdiretório isolado por sessão dentro de TEMP_DIR."""
    upload_dir = TEMP_DIR / session_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir
