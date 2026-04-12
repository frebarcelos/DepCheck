"""
tests/test_gui_renders.py
Testa funções de renderização da GUI com Streamlit e Plotly mockados.
Garante que os caminhos de código de render_* são exercitados sem servidor real.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ── Fixture de resultado completo ──────────────────────────────────────────────

FULL_RESULT: dict[str, Any] = {
    "project_info": {"name": "test", "analyzed_at": "2026-04-12T00:00:00"},
    "dependencies": {
        "declared": ["requests>=2.28", "flask>=3.0", "unused-lib"],
        "imported": ["requests", "flask"],
        "zombies": ["unused-lib"],
        "ghosts": ["boto3"],
        "outdated": {
            "flask": {"latest_version": "3.1.0", "declared_version": "3.0", "days_outdated": 90, "size_bytes": 200000},
        },
    },
    "statistics": {
        "total_declared": 3,
        "total_imported": 2,
        "total_zombies": 1,
        "total_ghosts": 1,
        "total_outdated": 1,
        "total_size_bytes": 614400,
        "avg_age_days": 150.0,
    },
    "enriched_declared": {
        "requests": {"size_bytes": 102400, "age_days": 200},
        "flask": {"size_bytes": 200000, "age_days": 100},
        "unused_lib": {"size_bytes": 312000, "age_days": None},
    },
}

EMPTY_RESULT: dict[str, Any] = {
    "project_info": {"name": "empty", "analyzed_at": ""},
    "dependencies": {"declared": [], "imported": [], "zombies": [], "ghosts": [], "outdated": {}},
    "statistics": {
        "total_declared": 0, "total_imported": 0, "total_zombies": 0,
        "total_ghosts": 0, "total_outdated": 0, "total_size_bytes": 0, "avg_age_days": None,
    },
    "enriched_declared": {},
}


def _mock_st():
    """Retorna um MagicMock completo para streamlit."""
    st = MagicMock()

    def _columns(n, **kwargs):
        count = n if isinstance(n, int) else len(n)
        return [MagicMock() for _ in range(count)]

    st.columns.side_effect = _columns
    return st


# ── gui/charts.py — funções puras ──────────────────────────────────────────────

def test_get_bar_chart_data_with_outdated() -> None:
    from gui.charts import get_bar_chart_data
    data = get_bar_chart_data(FULL_RESULT)
    assert "flask" in data["packages"]
    assert 90 in data["days"]


def test_get_bar_chart_data_empty() -> None:
    from gui.charts import get_bar_chart_data
    data = get_bar_chart_data(EMPTY_RESULT)
    assert data == {"packages": [], "days": []}


def test_get_size_chart_data_with_enriched() -> None:
    from gui.charts import get_size_chart_data
    data = get_size_chart_data(FULL_RESULT)
    assert len(data["packages"]) > 0
    assert len(data["sizes_kb"]) == len(data["packages"])


def test_get_size_chart_data_empty() -> None:
    from gui.charts import get_size_chart_data
    data = get_size_chart_data(EMPTY_RESULT)
    assert data == {"packages": [], "sizes_kb": []}


# ── gui/charts.py — render com Plotly mockado ─────────────────────────────────

def test_render_bar_chart_outdated_with_data() -> None:
    from gui import charts
    st = _mock_st()
    go = MagicMock()
    with patch.dict("sys.modules", {"streamlit": st, "plotly.graph_objects": go}):
        charts.render_bar_chart_outdated(FULL_RESULT)
    st.markdown.assert_called()


def test_render_bar_chart_outdated_empty() -> None:
    from gui import charts
    st = _mock_st()
    with patch.dict("sys.modules", {"streamlit": st}):
        charts.render_bar_chart_outdated(EMPTY_RESULT)
    st.info.assert_called()


def test_render_size_bar_chart_with_data() -> None:
    from gui import charts
    st = _mock_st()
    go = MagicMock()
    with patch.dict("sys.modules", {"streamlit": st, "plotly.graph_objects": go}):
        charts.render_size_bar_chart(FULL_RESULT)
    st.markdown.assert_called()


def test_render_size_bar_chart_empty() -> None:
    from gui import charts
    st = _mock_st()
    with patch.dict("sys.modules", {"streamlit": st}):
        charts.render_size_bar_chart(EMPTY_RESULT)
    st.info.assert_called()


# ── gui/report.py — render_zombie_table ───────────────────────────────────────

def test_render_zombie_table_with_zombies() -> None:
    from gui import report
    st = _mock_st()
    pd = MagicMock()
    pd.DataFrame.return_value.style.map.return_value = MagicMock()
    with patch.dict("sys.modules", {"streamlit": st, "pandas": pd}):
        report.render_zombie_table(FULL_RESULT)
    st.markdown.assert_called()


def test_render_zombie_table_no_zombies() -> None:
    from gui import report
    st = _mock_st()
    pd = MagicMock()
    with patch.dict("sys.modules", {"streamlit": st, "pandas": pd}):
        report.render_zombie_table(EMPTY_RESULT)
    st.success.assert_called()


# ── gui/report.py — render_ghost_table ────────────────────────────────────────

def test_render_ghost_table_with_ghosts() -> None:
    from gui import report
    st = _mock_st()
    pd = MagicMock()
    pd.DataFrame.return_value.style.map.return_value = MagicMock()
    with patch.dict("sys.modules", {"streamlit": st, "pandas": pd}):
        report.render_ghost_table(FULL_RESULT)
    st.markdown.assert_called()


def test_render_ghost_table_no_ghosts() -> None:
    from gui import report
    st = _mock_st()
    pd = MagicMock()
    with patch.dict("sys.modules", {"streamlit": st, "pandas": pd}):
        report.render_ghost_table(EMPTY_RESULT)
    # Mesmo sem fantasmas, exibe JSON download button
    assert st.download_button.called or st.info.called or st.success.called


# ── gui/report.py — render_outdated_table ─────────────────────────────────────

def test_render_outdated_table_with_outdated() -> None:
    from gui import report
    st = _mock_st()
    pd = MagicMock()
    pd.DataFrame.return_value.style.map.return_value = MagicMock()
    with patch.dict("sys.modules", {"streamlit": st, "pandas": pd}):
        report.render_outdated_table(FULL_RESULT)
    st.markdown.assert_called()


def test_render_outdated_table_all_updated() -> None:
    from gui import report
    st = _mock_st()
    pd = MagicMock()
    with patch.dict("sys.modules", {"streamlit": st, "pandas": pd}):
        report.render_outdated_table(EMPTY_RESULT)
    st.success.assert_called()


def test_render_outdated_table_uses_map_not_applymap() -> None:
    """Garante que render_outdated_table usa Styler.map (pandas>=2.1), não applymap (removido)."""
    import pandas as real_pd
    from gui import report
    st = _mock_st()
    with patch.dict("sys.modules", {"streamlit": st}):
        # Não deve lançar AttributeError: 'Styler' object has no attribute 'applymap'
        report.render_outdated_table(FULL_RESULT)
    st.markdown.assert_called()


# ── gui/report.py — render_kpi_cards ──────────────────────────────────────────

def test_render_kpi_cards_does_not_raise() -> None:
    from gui import report
    st = _mock_st()
    with patch.dict("sys.modules", {"streamlit": st}):
        report.render_kpi_cards(FULL_RESULT)
    st.markdown.assert_called()


def test_render_kpi_cards_empty_result() -> None:
    from gui import report
    st = _mock_st()
    with patch.dict("sys.modules", {"streamlit": st}):
        report.render_kpi_cards(EMPTY_RESULT)


# ── gui/report.py — render_pie_chart ──────────────────────────────────────────

def test_render_pie_chart_does_not_raise() -> None:
    from gui import report
    st = _mock_st()
    go = MagicMock()
    with patch.dict("sys.modules", {"streamlit": st, "plotly.graph_objects": go}):
        report.render_pie_chart(FULL_RESULT)


# ── gui/report.py — render_all_deps_table ────────────────────────────────────

def test_render_all_deps_table_with_data() -> None:
    from gui import report
    st = _mock_st()
    pd = MagicMock()
    with patch.dict("sys.modules", {"streamlit": st, "pandas": pd}):
        report.render_all_deps_table(FULL_RESULT)
    st.markdown.assert_called()


def test_render_all_deps_table_empty() -> None:
    from gui import report
    st = _mock_st()
    pd = MagicMock()
    with patch.dict("sys.modules", {"streamlit": st, "pandas": pd}):
        report.render_all_deps_table(EMPTY_RESULT)
