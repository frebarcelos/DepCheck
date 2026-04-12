"""
tests/test_orchestrator.py
Testes do pipeline procedural central (src/orchestrator.py).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from src import orchestrator
from src.orchestrator import _find_manifest, _run_parsers, run_analysis


# ── _find_manifest ─────────────────────────────────────────────────────────────

def test_find_manifest_at_root(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    result = _find_manifest(tmp_path, "pyproject.toml")
    assert result == tmp_path / "pyproject.toml"


def test_find_manifest_in_subfolder(tmp_path: Path) -> None:
    sub = tmp_path / "myproject"
    sub.mkdir()
    (sub / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    result = _find_manifest(tmp_path, "pyproject.toml")
    assert result == sub / "pyproject.toml"


def test_find_manifest_returns_none_when_absent(tmp_path: Path) -> None:
    result = _find_manifest(tmp_path, "pyproject.toml")
    assert result is None


def test_find_manifest_prefers_root_over_subfolder(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='root'\n", encoding="utf-8")
    sub = tmp_path / "inner"
    sub.mkdir()
    (sub / "pyproject.toml").write_text("[project]\nname='inner'\n", encoding="utf-8")
    result = _find_manifest(tmp_path, "pyproject.toml")
    assert result == tmp_path / "pyproject.toml"


# ── _run_parsers ───────────────────────────────────────────────────────────────

def test_run_parsers_reads_pyproject(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

    monkeypatch.setattr("src.orchestrator.parse_pyproject", lambda _: {"requests": "requests>=2.0"})

    deps = _run_parsers(tmp_path)
    assert "requests>=2.0" in deps


def test_run_parsers_reads_requirements(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "requirements.txt").write_text("flask>=3.0\n", encoding="utf-8")

    monkeypatch.setattr("src.orchestrator.parse_requirements", lambda _: {"flask": ">=3.0"})

    deps = _run_parsers(tmp_path)
    assert "flask>=3.0" in deps


def test_run_parsers_merges_both_manifests(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("uvicorn\n", encoding="utf-8")

    monkeypatch.setattr("src.orchestrator.parse_pyproject", lambda _: {"requests": "requests>=2.28"})
    monkeypatch.setattr("src.orchestrator.parse_requirements", lambda _: {"uvicorn": "==0.30.0"})

    deps = _run_parsers(tmp_path)
    assert "requests>=2.28" in deps
    assert "uvicorn==0.30.0" in deps


def test_run_parsers_returns_empty_when_no_manifest(tmp_path: Path) -> None:
    deps = _run_parsers(tmp_path)
    assert deps == []


def test_run_parsers_handles_nested_zip_structure(tmp_path: Path, monkeypatch) -> None:
    sub = tmp_path / "myproject"
    sub.mkdir()
    (sub / "pyproject.toml").write_text("[project]\n", encoding="utf-8")

    monkeypatch.setattr("src.orchestrator.parse_pyproject", lambda _: {"numpy": "numpy>=1.24"})

    deps = _run_parsers(tmp_path)
    assert "numpy>=1.24" in deps


def test_run_parsers_survives_parser_exception(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")

    def _raise(_path):
        raise RuntimeError("parser error")

    monkeypatch.setattr("src.orchestrator.parse_pyproject", _raise)
    deps = _run_parsers(tmp_path)
    assert deps == []


# ── run_analysis (integração com mocks) ────────────────────────────────────────

def test_run_analysis_fills_result_model(monkeypatch) -> None:
    monkeypatch.setattr(orchestrator, "_run_parsers", lambda _p: ["requests>=2.0", "flask>=3.0"])
    monkeypatch.setattr(orchestrator, "_run_ast", lambda _p: {"requests", "os"})
    monkeypatch.setattr(orchestrator, "_analyze_zombies", lambda d, i: ["flask>=3.0"])
    monkeypatch.setattr(orchestrator, "_analyze_ghosts", lambda d, i: ["os"])
    monkeypatch.setattr(orchestrator, "_analyze_outdated", lambda d: {"requests": {"latest_version": "2.32.0", "days_outdated": 120}})
    monkeypatch.setattr(orchestrator, "_enrich_dependencies", lambda d: {})

    result = run_analysis(".")

    assert result["dependencies"]["declared"] == ["requests>=2.0", "flask>=3.0"]
    assert "requests" in result["dependencies"]["outdated"]
    assert result["statistics"]["total_declared"] == 2
    assert result["statistics"]["total_zombies"] == 1
    assert result["statistics"]["total_ghosts"] == 1
    assert result["statistics"]["total_outdated"] == 1


def test_run_analysis_with_enrichment(monkeypatch) -> None:
    monkeypatch.setattr(orchestrator, "_run_parsers", lambda _p: ["requests>=2.0"])
    monkeypatch.setattr(orchestrator, "_run_ast", lambda _p: {"requests"})
    monkeypatch.setattr(orchestrator, "_analyze_zombies", lambda d, i: [])
    monkeypatch.setattr(orchestrator, "_analyze_ghosts", lambda d, i: [])
    monkeypatch.setattr(orchestrator, "_analyze_outdated", lambda d: {})
    monkeypatch.setattr(orchestrator, "_enrich_dependencies", lambda d: {
        "requests": {"size_bytes": 102400, "age_days": 180}
    })

    result = run_analysis(".")

    assert result["enriched_declared"]["requests"]["size_bytes"] == 102400
    assert result["enriched_declared"]["requests"]["age_days"] == 180
    assert result["statistics"]["total_size_bytes"] == 102400
    assert result["statistics"]["avg_age_days"] == 180.0


def test_run_analysis_handles_ast_failure(monkeypatch) -> None:
    monkeypatch.setattr(orchestrator, "_run_parsers", lambda _p: ["requests>=2.0"])
    monkeypatch.setattr(orchestrator, "_run_ast", lambda _p: set())
    monkeypatch.setattr(orchestrator, "_analyze_zombies", lambda d, i: [])
    monkeypatch.setattr(orchestrator, "_analyze_ghosts", lambda d, i: [])
    monkeypatch.setattr(orchestrator, "_analyze_outdated", lambda d: {})
    monkeypatch.setattr(orchestrator, "_enrich_dependencies", lambda d: {})

    result = run_analysis(".")
    assert result["dependencies"]["imported"] == []
    assert result["statistics"]["total_imported"] == 0


def test_run_analysis_result_has_all_required_keys(monkeypatch) -> None:
    for fn in ("_run_parsers", "_run_ast", "_analyze_zombies", "_analyze_ghosts",
               "_analyze_outdated", "_enrich_dependencies"):
        monkeypatch.setattr(orchestrator, fn, lambda *_: {} if "enrich" in fn or "outdated" in fn else ([] if "parsers" in fn or "zombies" in fn or "ghosts" in fn else set()))

    result = run_analysis(".")
    assert "project_info" in result
    assert "dependencies" in result
    assert "statistics" in result
    assert "enriched_declared" in result
    assert "analyzed_at" in result["project_info"]
