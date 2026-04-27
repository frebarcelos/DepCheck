from __future__ import annotations

from core.results_model import get_empty_result_model


def test_get_empty_result_model_has_expected_top_level_keys() -> None:
    """Checa as chaves principais esperadas no modelo de resultado."""
    model = get_empty_result_model()

    assert set(model.keys()) == {"project_info", "dependencies", "statistics", "enriched_declared"}


def test_get_empty_result_model_has_expected_defaults() -> None:
    """Valida valores default do modelo vazio."""
    model = get_empty_result_model()

    assert model["project_info"] == {"name": "unknown", "analyzed_at": ""}
    assert model["dependencies"] == {
        "declared": [],
        "imported": [],
        "zombies": [],
        "ghosts": [],
        "outdated": {},
    }
    assert model["statistics"] == {
        "total_declared": 0,
        "total_imported": 0,
        "total_zombies": 0,
        "total_ghosts": 0,
        "total_outdated": 0,
    }
    assert model["enriched_declared"] == {}


def test_get_empty_result_model_returns_independent_instances() -> None:
    """Garante que duas chamadas retornam estruturas independentes."""
    model_a = get_empty_result_model()
    model_b = get_empty_result_model()

    model_a["dependencies"]["declared"].append("requests>=2.0")
    model_a["dependencies"]["outdated"]["requests"] = {
        "latest_version": "2.32.0",
        "days_outdated": 90,
    }

    assert model_b["dependencies"]["declared"] == []
    assert model_b["dependencies"]["outdated"] == {}
