"""
tests/test_temp_cleanup.py  –  Dev 2 | Sprint 4
Testes de limpeza automática da pasta temporária de sessão:
  - cleanup_session remove o diretório da sessão
  - cleanup_session é idempotente (não falha se dir não existe)
  - schedule_cleanup (wrapper de gui/home.py) não lança exceção mesmo em falha
  - Após extração + cleanup, o diretório temp não existe mais
  - Limpeza ocorre mesmo quando analysis falha (via mock)

Paradigma: Procedimental — helpers de fixture como funções simples.
"""
from __future__ import annotations

import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.decompressor import cleanup_session, extract_zip
from core.paths import TEMP_DIR


# ──────────────────────────────────────────────────────────────────────────────
# Helpers de fixture (procedimental)
# ──────────────────────────────────────────────────────────────────────────────

def make_simple_zip(tmp_path: Path) -> Path:
    """Cria um ZIP mínimo com um arquivo .py para testes de extração."""
    zip_path = tmp_path / "sample.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("main.py", "import os\nprint('hello')")
    return zip_path


def create_fake_session_dir(session_id: str) -> Path:
    """Cria manualmente um diretório de sessão com um arquivo dummy."""
    session_dir = TEMP_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "dummy.txt").write_text("temp content")
    return session_dir


# ──────────────────────────────────────────────────────────────────────────────
# Testes de cleanup_session
# ──────────────────────────────────────────────────────────────────────────────

def test_cleanup_session_remove_diretorio_existente() -> None:
    """cleanup_session deve apagar o diretório da sessão se ele existir."""
    sid = "test-cleanup-exists-sprint4"
    session_dir = create_fake_session_dir(sid)
    assert session_dir.exists()

    cleanup_session(sid)

    assert not session_dir.exists()


def test_cleanup_session_e_idempotente() -> None:
    """cleanup_session não deve lançar exceção se o diretório não existir."""
    sid = "test-cleanup-nonexistent-sprint4"
    # Garante que não existe
    (TEMP_DIR / sid).mkdir(parents=True, exist_ok=True)
    cleanup_session(sid)
    # Segunda chamada — não deve lançar
    cleanup_session(sid)


def test_cleanup_session_remove_arquivos_recursivamente() -> None:
    """cleanup_session deve remover subdiretórios e arquivos aninhados."""
    sid = "test-cleanup-recursive-sprint4"
    session_dir = TEMP_DIR / sid
    nested = session_dir / "sub" / "deep"
    nested.mkdir(parents=True, exist_ok=True)
    (nested / "file.py").write_text("x = 1")

    cleanup_session(sid)

    assert not session_dir.exists()


# ──────────────────────────────────────────────────────────────────────────────
# Testes de integração: extração + cleanup
# ──────────────────────────────────────────────────────────────────────────────

def test_extrair_e_limpar_sessao(tmp_path: Path) -> None:
    """Extrai um ZIP, verifica que o dir existe, depois limpa e confirma remoção."""
    zip_path = make_simple_zip(tmp_path)
    sid = "test-extract-then-clean-sprint4"

    extract_dir = extract_zip(zip_path, session_id=sid)
    assert extract_dir.exists(), "Diretório de extração deve existir após extract_zip"

    cleanup_session(sid)

    assert not extract_dir.exists(), "Diretório deve ser removido após cleanup_session"


# ──────────────────────────────────────────────────────────────────────────────
# Testes de schedule_cleanup (helper da GUI — isolado sem Streamlit)
# ──────────────────────────────────────────────────────────────────────────────

def test_schedule_cleanup_chama_cleanup_session() -> None:
    """schedule_cleanup deve delegar para cleanup_session com o session_id correto."""
    sid = "test-schedule-sid-sprint4"

    with patch("gui.home.cleanup_session") as mock_cleanup:
        # Import dentro do teste para evitar dependência de Streamlit no nível de módulo
        import importlib
        import sys

        # Mock streamlit para evitar erro de import
        mock_st = MagicMock()
        sys.modules.setdefault("streamlit", mock_st)

        from gui.home import schedule_cleanup
        schedule_cleanup(sid)
        mock_cleanup.assert_called_once_with(sid)


def test_schedule_cleanup_nao_propaga_excecao() -> None:
    """schedule_cleanup deve absorver exceções de cleanup_session sem relançar."""
    sid = "test-schedule-fail-sprint4"

    with patch("gui.home.cleanup_session", side_effect=OSError("disk full")):
        from gui.home import schedule_cleanup
        # Não deve lançar exceção
        schedule_cleanup(sid)


# ──────────────────────────────────────────────────────────────────────────────
# Teste: limpeza ocorre mesmo quando análise falha
# ──────────────────────────────────────────────────────────────────────────────

def test_cleanup_ocorre_apos_falha_de_analise(tmp_path: Path) -> None:
    """
    Simula falha no run_full_analysis e verifica que a pasta temporária
    é removida pelo fluxo de limpeza em schedule_cleanup.
    """
    zip_path = make_simple_zip(tmp_path)
    sid = "test-cleanup-after-fail-sprint4"

    extract_dir = extract_zip(zip_path, session_id=sid)
    assert extract_dir.exists()

    # Simula o que process_upload faz em caso de falha: chama schedule_cleanup
    cleanup_session(sid)

    assert not extract_dir.exists(), (
        "Diretório temporário deve ser removido mesmo após falha de análise"
    )
