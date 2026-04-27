"""
tests/test_gui_report_zombie.py  –  Dev 1 | Sprint 3 (TDD)
Testa a lógica de renderização da tabela de Zumbis e geração de CSV para download.
"""
from __future__ import annotations

import io
import csv
from unittest.mock import patch, MagicMock

import pytest

# ── Fixtures de resultado mockado ──────────────────────────────────────────────

MOCK_RESULT = {
    "project_info": {"name": "test-project", "analyzed_at": "2026-04-05T00:00:00"},
    "dependencies": {
        "declared": ["requests>=2.28.0", "pillow>=9.0.0", "unused-lib>=1.0.0"],
        "imported": ["requests", "PIL"],
        "zombies": ["unused-lib>=1.0.0"],
        "ghosts": [],
        "outdated": {},
    },
    "statistics": {
        "total_declared": 3,
        "total_imported": 2,
        "total_zombies": 1,
        "total_ghosts": 0,
        "total_outdated": 0,
    },
}


# ── Testes de lógica de tabela ─────────────────────────────────────────────────

def test_get_zombie_rows_returns_only_zombies():
    """Garante que a função retorna apenas as dependências identificadas como zumbis."""
    from gui.report import get_zombie_rows

    rows = get_zombie_rows(MOCK_RESULT)
    assert len(rows) == 1
    assert rows[0]["pacote"] == "unused-lib>=1.0.0"
    assert rows[0]["status"] == "Zumbi"


def test_get_zombie_rows_empty_when_no_zombies():
    """Retorna lista vazia se não houver zumbis no resultado."""
    from gui.report import get_zombie_rows

    clean_result = dict(MOCK_RESULT)
    clean_result["dependencies"] = dict(MOCK_RESULT["dependencies"])
    clean_result["dependencies"]["zombies"] = []

    rows = get_zombie_rows(clean_result)
    assert rows == []


def test_get_zombie_rows_handles_missing_key():
    """Não falha se a chave 'zombies' estiver ausente no dicionário."""
    from gui.report import get_zombie_rows

    incomplete = {"dependencies": {}}
    rows = get_zombie_rows(incomplete)
    assert rows == []


# ── Testes de geração de CSV ───────────────────────────────────────────────────

def test_build_csv_bytes_contains_header():
    """O CSV gerado deve ter cabeçalho com 'Pacote' e 'Status'."""
    from gui.report import build_zombie_csv_bytes

    raw = build_zombie_csv_bytes(MOCK_RESULT)
    text = raw.decode("utf-8")
    assert "pacote" in text
    assert "status" in text


def test_build_csv_bytes_contains_zombie_entry():
    """O CSV deve conter a linha do pacote zumbi."""
    from gui.report import build_zombie_csv_bytes

    raw = build_zombie_csv_bytes(MOCK_RESULT)
    text = raw.decode("utf-8")
    assert "unused-lib>=1.0.0" in text


def test_build_csv_bytes_empty_on_no_zombies():
    """CSV com apenas cabeçalho quando não há zumbis."""
    from gui.report import build_zombie_csv_bytes

    clean = dict(MOCK_RESULT)
    clean["dependencies"] = dict(MOCK_RESULT["dependencies"])
    clean["dependencies"]["zombies"] = []

    raw = build_zombie_csv_bytes(clean)
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
    rows = list(reader)
    assert rows == []
