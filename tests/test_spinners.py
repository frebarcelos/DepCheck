"""
tests/test_spinners.py  –  Dev 5 | Sprint 3 (TDD)
Testa a lógica de construção dos dados para o gráfico de barras de defasagem
e valida que os spinners são acionados corretamente via mocks.
"""
from __future__ import annotations

import pytest

MOCK_RESULT = {
    "project_info": {"name": "spinner-project", "analyzed_at": "2026-04-05T00:00:00"},
    "dependencies": {
        "declared": ["requests>=2.28.0", "flask>=2.0.0", "numpy>=1.24.0"],
        "imported": ["requests", "flask", "numpy"],
        "zombies": [],
        "ghosts": [],
        "outdated": {
            "requests": {"latest_version": "2.32.0", "days_outdated": 180},
            "flask": {"latest_version": "3.0.2", "days_outdated": 365},
            "numpy": {"latest_version": "1.26.4", "days_outdated": 90},
        },
    },
    "statistics": {
        "total_declared": 3,
        "total_imported": 3,
        "total_zombies": 0,
        "total_ghosts": 0,
        "total_outdated": 3,
    },
}


# ── Testes de dados para gráfico de barras ─────────────────────────────────────

def test_get_bar_chart_data_returns_packages_and_days():
    """Os dados devem conter listas de pacotes e dias de defasagem."""
    from gui.charts import get_bar_chart_data

    data = get_bar_chart_data(MOCK_RESULT)
    assert "packages" in data
    assert "days" in data


def test_get_bar_chart_data_lengths_match():
    """O número de pacotes deve ser igual ao número de valores de dias."""
    from gui.charts import get_bar_chart_data

    data = get_bar_chart_data(MOCK_RESULT)
    assert len(data["packages"]) == len(data["days"])


def test_get_bar_chart_data_sorted_descending():
    """Os dados devem estar ordenados por dias decrescente."""
    from gui.charts import get_bar_chart_data

    data = get_bar_chart_data(MOCK_RESULT)
    days = data["days"]
    assert days == sorted(days, reverse=True)


def test_get_bar_chart_data_all_days_positive():
    """Todos os valores de dias devem ser inteiros >= 0."""
    from gui.charts import get_bar_chart_data

    data = get_bar_chart_data(MOCK_RESULT)
    for d in data["days"]:
        assert isinstance(d, int)
        assert d >= 0


def test_get_bar_chart_data_empty_on_no_outdated():
    """Retorna listas vazias se não há pacotes desatualizados."""
    from gui.charts import get_bar_chart_data

    clean = dict(MOCK_RESULT)
    clean["dependencies"] = dict(MOCK_RESULT["dependencies"])
    clean["dependencies"]["outdated"] = {}

    data = get_bar_chart_data(clean)
    assert data["packages"] == []
    assert data["days"] == []


def test_get_bar_chart_data_contains_top_package():
    """O pacote mais defasado deve estar na primeira posição."""
    from gui.charts import get_bar_chart_data

    data = get_bar_chart_data(MOCK_RESULT)
    # Flask tem 365 dias → deve ser o primeiro
    assert data["packages"][0] == "flask"
    assert data["days"][0] == 365


# ── Testes de fluxo de análise (spinner implícito via orquestrador) ────────────

def test_run_full_analysis_returns_dict(tmp_path):
    """
    Garante que run_full_analysis retorna um dicionário com as chaves esperadas,
    usando um projeto temporário vazio como entrada.
    """
    from gui.home import run_full_analysis

    result = run_full_analysis(str(tmp_path))
    assert isinstance(result, dict)
    assert "dependencies" in result
    assert "statistics" in result
