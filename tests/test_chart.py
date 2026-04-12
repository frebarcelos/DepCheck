"""Testes da construção de dados do gráfico de pizza."""

from __future__ import annotations

MOCK_RESULT = {
    "project_info": {"name": "chart-project", "analyzed_at": "2026-04-05T00:00:00"},
    "dependencies": {
        "declared": ["requests", "flask", "djangocms", "unused-lib", "boto3"],
        "imported": ["requests", "flask", "boto3"],
        "zombies": ["unused-lib"],
        "ghosts": ["boto3"],
        "outdated": {"requests": {"latest_version": "2.32.0", "days_outdated": 90}},
    },
    "statistics": {
        "total_declared": 5,
        "total_imported": 3,
        "total_zombies": 1,
        "total_ghosts": 1,
        "total_outdated": 1,
    },
}


def test_get_pie_chart_data_returns_labels_and_values():
    """Os dados do gráfico devem conter labels, values e colors."""
    from gui.report import get_pie_chart_data

    data = get_pie_chart_data(MOCK_RESULT)
    assert set(data.keys()) == {"labels", "values", "colors"}


def test_get_pie_chart_data_labels_are_strings():
    """Todos os labels devem ser strings."""
    from gui.report import get_pie_chart_data

    data = get_pie_chart_data(MOCK_RESULT)
    for label in data["labels"]:
        assert isinstance(label, str)


def test_get_pie_chart_data_values_are_non_negative():
    """Todos os valores devem ser >= 0."""
    from gui.report import get_pie_chart_data

    data = get_pie_chart_data(MOCK_RESULT)
    for value in data["values"]:
        assert value >= 0


def test_get_pie_chart_data_total_matches_declared_when_consistent():
    """Com estatísticas consistentes, a soma deve bater com total_declared."""
    from gui.report import get_pie_chart_data

    data = get_pie_chart_data(MOCK_RESULT)
    total = sum(data["values"])
    assert total == MOCK_RESULT["statistics"]["total_declared"]


def test_get_pie_chart_data_has_at_least_two_categories():
    """O gráfico deve ter pelo menos 2 categorias (saudáveis + problemáticos)."""
    from gui.report import get_pie_chart_data

    data = get_pie_chart_data(MOCK_RESULT)
    assert len(data["labels"]) == 4


def test_get_pie_chart_data_includes_healthy_category():
    """Deve existir uma categoria para dependências saudáveis."""
    from gui.report import get_pie_chart_data

    data = get_pie_chart_data(MOCK_RESULT)
    labels_lower = [label.lower() for label in data["labels"]]
    assert any("saud" in label for label in labels_lower)


def test_get_pie_chart_data_all_zero_when_empty():
    """Com resultado vazio, todos os valores devem ser 0."""
    from gui.report import get_pie_chart_data

    empty = {
        "statistics": {
            "total_declared": 0,
            "total_zombies": 0,
            "total_ghosts": 0,
            "total_outdated": 0,
        }
    }
    data = get_pie_chart_data(empty)
    assert all(v == 0 for v in data["values"])


def test_get_pie_chart_data_healthy_is_clamped_at_zero():
    """Quando inconsistências geram negativo, saudável deve ser 0."""
    from gui.report import get_pie_chart_data

    inconsistent = {
        "statistics": {
            "total_declared": 1,
            "total_zombies": 2,
            "total_ghosts": 2,
            "total_outdated": 2,
        }
    }

    data = get_pie_chart_data(inconsistent)
    assert data["values"][0] == 0
