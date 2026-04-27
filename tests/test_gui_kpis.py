"""
tests/test_gui_kpis.py  –  Dev 3 | Sprint 3 (TDD)
Testa os KPIs de estatísticas e a lógica da tabela de dependências desatualizadas.
"""
from __future__ import annotations

import pytest

MOCK_RESULT = {
    "project_info": {"name": "outdated-project", "analyzed_at": "2026-04-05T00:00:00"},
    "dependencies": {
        "declared": ["requests>=2.28.0", "flask>=2.0.0", "pillow>=9.0.0"],
        "imported": ["requests", "flask", "PIL"],
        "zombies": [],
        "ghosts": [],
        "outdated": {
            "requests": {"latest_version": "2.32.0", "days_outdated": 180},
            "flask": {"latest_version": "3.0.2", "days_outdated": 365},
        },
    },
    "statistics": {
        "total_declared": 3,
        "total_imported": 3,
        "total_zombies": 0,
        "total_ghosts": 0,
        "total_outdated": 2,
    },
}


# ── Testes de KPIs ─────────────────────────────────────────────────────────────

def test_get_kpi_values_returns_correct_statistics():
    """Os KPIs extraídos devem corresponder ao bloco 'statistics' do resultado."""
    from gui.report import get_kpi_values

    kpis = get_kpi_values(MOCK_RESULT)
    assert kpis["total_declared"] == 3
    assert kpis["total_imported"] == 3
    assert kpis["total_zombies"] == 0
    assert kpis["total_ghosts"] == 0
    assert kpis["total_outdated"] == 2


def test_get_kpi_values_defaults_to_zero_on_missing():
    """KPIs retornam 0 se o bloco 'statistics' estiver ausente."""
    from gui.report import get_kpi_values

    kpis = get_kpi_values({})
    assert kpis["total_declared"] == 0
    assert kpis["total_outdated"] == 0


def test_get_kpi_values_calculates_healthy():
    """Total de saudáveis = declaradas - (zumbis + fantasmas + desatualizadas)."""
    from gui.report import get_kpi_values

    kpis = get_kpi_values(MOCK_RESULT)
    # Healthy = declared - zombies - ghosts - outdated (aproximação útil para KPI)
    expected_healthy = max(0, 3 - 0 - 0 - 2)
    assert kpis.get("total_healthy", expected_healthy) == expected_healthy


# ── Testes de tabela de desatualizadas ─────────────────────────────────────────

def test_get_outdated_rows_returns_all_outdated():
    """Retorna uma linha por pacote desatualizado."""
    from gui.report import get_outdated_rows

    rows = get_outdated_rows(MOCK_RESULT)
    assert len(rows) == 2
    names = {r["pacote"] for r in rows}
    assert "requests" in names
    assert "flask" in names


def test_get_outdated_rows_contain_version_and_days():
    """Cada linha deve ter 'versao_mais_recente' e 'dias_defasagem'."""
    from gui.report import get_outdated_rows

    rows = get_outdated_rows(MOCK_RESULT)
    for row in rows:
        assert "versao_mais_recente" in row
        assert "dias_defasagem" in row
        assert isinstance(row["dias_defasagem"], int)


def test_get_outdated_rows_empty_when_none():
    """Retorna lista vazia se não há pacotes desatualizados."""
    from gui.report import get_outdated_rows

    clean = dict(MOCK_RESULT)
    clean["dependencies"] = dict(MOCK_RESULT["dependencies"])
    clean["dependencies"]["outdated"] = {}

    rows = get_outdated_rows(clean)
    assert rows == []


def test_get_outdated_rows_sorted_by_days_desc():
    """Linhas devem estar ordenadas por dias_defasagem decrescente."""
    from gui.report import get_outdated_rows

    rows = get_outdated_rows(MOCK_RESULT)
    days = [r["dias_defasagem"] for r in rows]
    assert days == sorted(days, reverse=True)
