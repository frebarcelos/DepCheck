"""
tests/test_gui_report_ghost.py  –  Dev 2 | Sprint 3 (TDD)
Testa a lógica de renderização da tabela de Fantasmas e geração de JSON para download.
"""
from __future__ import annotations

import json

import pytest

# ── Fixture de resultado mockado ───────────────────────────────────────────────

MOCK_RESULT = {
    "project_info": {"name": "ghost-project", "analyzed_at": "2026-04-05T00:00:00"},
    "dependencies": {
        "declared": ["requests>=2.28.0"],
        "imported": ["requests", "boto3", "pandas"],
        "zombies": [],
        "ghosts": ["boto3", "pandas"],
        "outdated": {},
    },
    "statistics": {
        "total_declared": 1,
        "total_imported": 3,
        "total_zombies": 0,
        "total_ghosts": 2,
        "total_outdated": 0,
    },
}


# ── Testes de tabela de fantasmas ──────────────────────────────────────────────

def test_get_ghost_rows_returns_only_ghosts():
    """Retorna somente as dependências identificadas como fantasmas."""
    from gui.report import get_ghost_rows

    rows = get_ghost_rows(MOCK_RESULT)
    assert len(rows) == 2
    nomes = {r["pacote"] for r in rows}
    assert "boto3" in nomes
    assert "pandas" in nomes
    for r in rows:
        assert r["status"] == "Fantasma"


def test_get_ghost_rows_empty_when_no_ghosts():
    """Retorna lista vazia se não houver fantasmas."""
    from gui.report import get_ghost_rows

    clean = dict(MOCK_RESULT)
    clean["dependencies"] = dict(MOCK_RESULT["dependencies"])
    clean["dependencies"]["ghosts"] = []

    rows = get_ghost_rows(clean)
    assert rows == []


def test_get_ghost_rows_handles_missing_key():
    """Não falha se a chave 'ghosts' estiver ausente."""
    from gui.report import get_ghost_rows

    rows = get_ghost_rows({"dependencies": {}})
    assert rows == []


# ── Testes de geração de JSON ──────────────────────────────────────────────────

def test_build_json_bytes_is_valid_json():
    """O conteúdo gerado deve ser JSON parseável."""
    from gui.report import build_json_bytes

    raw = build_json_bytes(MOCK_RESULT)
    parsed = json.loads(raw.decode("utf-8"))
    assert isinstance(parsed, dict)


def test_build_json_bytes_contains_ghosts_key():
    """O JSON deve conter a chave 'ghosts' no bloco de dependências."""
    from gui.report import build_json_bytes

    raw = build_json_bytes(MOCK_RESULT)
    parsed = json.loads(raw.decode("utf-8"))
    assert "ghosts" in parsed["dependencies"]


def test_build_json_bytes_ghosts_values_match():
    """Os valores de fantasmas no JSON devem corresponder ao resultado original."""
    from gui.report import build_json_bytes

    raw = build_json_bytes(MOCK_RESULT)
    parsed = json.loads(raw.decode("utf-8"))
    assert set(parsed["dependencies"]["ghosts"]) == {"boto3", "pandas"}
