"""
tests/test_orchestrator_enriched.py  –  Dev 4 | Sprint 4
Testes de integração para o enriquecimento de metadados (size_bytes, age_days)
no pipeline do orquestrador.

Paradigma: Procedimental — apenas funções, sem classes de domínio.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_MOCK_ENRICHED: dict[str, dict] = {
    "requests": {"size_bytes": 102_400, "age_days": 180},
    "flask": {"size_bytes": 512_000, "age_days": 365},
    "numpy": {"size_bytes": -1, "age_days": None},
}

_MOCK_DECLARED = ["requests>=2.28.0", "flask>=3.0", "numpy>=1.24.0"]
_MOCK_IMPORTED: set[str] = {"requests", "flask", "numpy"}


def _make_patched_run_analysis(
    tmp_path: Path,
    enriched_data: dict[str, dict],
    raise_enrichment: bool = False,
) -> dict:
    """
    Executa ``run_analysis`` com todos os analisadores reais substituídos por mocks
    para isolar o comportamento do enriquecimento.

    Substitui ``_enrich_dependencies`` diretamente no módulo do orquestrador
    para não depender da existência do ``age_size_analyzer`` do Dev 3.

    Args:
        tmp_path: Diretório temporário usado como raiz do projeto.
        enriched_data: Dados que ``_enrich_dependencies`` deve retornar.
        raise_enrichment: Se True, ``_enrich_dependencies`` lança exceção.

    Returns:
        Dicionário de resultado retornado por ``run_analysis``.
    """
    from src.orchestrator import run_analysis

    def _mock_enrich(declared: list[str]) -> dict[str, dict]:  # noqa: ARG001
        # Simula o comportamento real de _enrich_dependencies:
        # captura exceções internas e retorna {} em vez de propagar.
        if raise_enrichment:
            return {}
        return enriched_data

    with (
        patch("src.orchestrator._run_parsers", return_value=_MOCK_DECLARED),
        patch("src.orchestrator._run_ast", return_value=_MOCK_IMPORTED),
        patch("src.orchestrator._analyze_zombies", return_value=["flask"]),
        patch("src.orchestrator._analyze_ghosts", return_value=[]),
        patch("src.orchestrator._analyze_outdated", return_value={}),
        patch("src.orchestrator._enrich_dependencies", side_effect=_mock_enrich),
    ):
        return run_analysis(str(tmp_path))


# ---------------------------------------------------------------------------
# Testes: run_analysis popula enriched_declared
# ---------------------------------------------------------------------------


def test_run_analysis_populates_enriched_declared(tmp_path: Path) -> None:
    """
    Garante que ``run_analysis`` chama ``_enrich_dependencies`` e persiste
    o resultado em ``result["enriched_declared"]``.
    """
    result = _make_patched_run_analysis(tmp_path, _MOCK_ENRICHED)

    assert "enriched_declared" in result
    assert result["enriched_declared"] == _MOCK_ENRICHED


# ---------------------------------------------------------------------------
# Testes: _fill_result_model persiste enriched_declared corretamente
# ---------------------------------------------------------------------------


def test_fill_result_model_persists_enriched_declared(tmp_path: Path) -> None:
    """
    Confirma que ``_fill_result_model`` grava ``enriched_declared`` no resultado
    exatamente como recebido, sem modificação.
    """
    from core.results_model import get_empty_result_model
    from src.orchestrator import _fill_result_model

    result = get_empty_result_model()
    enriched = {"requests": {"size_bytes": 50_000, "age_days": 90}}

    _fill_result_model(
        result,
        declared_deps=["requests>=2.0"],
        imported_modules={"requests"},
        zombies=[],
        ghosts=[],
        outdated={},
        enriched_declared=enriched,
    )

    assert result["enriched_declared"] == enriched


def test_fill_result_model_defaults_enriched_to_empty_dict(tmp_path: Path) -> None:
    """
    Verifica que ``_fill_result_model`` aceita ``enriched_declared=None`` e
    persiste um dicionário vazio (sem KeyError).
    """
    from core.results_model import get_empty_result_model
    from src.orchestrator import _fill_result_model

    result = get_empty_result_model()

    _fill_result_model(
        result,
        declared_deps=[],
        imported_modules=set(),
        zombies=[],
        ghosts=[],
        outdated={},
        enriched_declared=None,
    )

    assert result["enriched_declared"] == {}


# ---------------------------------------------------------------------------
# Testes: statistics["total_size_bytes"] é calculado corretamente
# ---------------------------------------------------------------------------


def test_statistics_total_size_bytes_excludes_minus_one(tmp_path: Path) -> None:
    """
    Confirma que ``total_size_bytes`` soma apenas entradas com size_bytes != -1,
    ignorando o sentinela -1 (dados indisponíveis).
    """
    result = _make_patched_run_analysis(tmp_path, _MOCK_ENRICHED)

    # requests: 102_400 + flask: 512_000 = 614_400; numpy: -1 deve ser ignorado
    assert result["statistics"]["total_size_bytes"] == 614_400


def test_statistics_total_size_bytes_zero_when_all_unavailable(tmp_path: Path) -> None:
    """
    Garante que ``total_size_bytes`` é 0 quando todos os size_bytes são -1.
    """
    all_unavailable = {
        "requests": {"size_bytes": -1, "age_days": None},
        "flask": {"size_bytes": -1, "age_days": None},
    }
    result = _make_patched_run_analysis(tmp_path, all_unavailable)

    assert result["statistics"]["total_size_bytes"] == 0


def test_statistics_total_size_bytes_zero_when_enriched_empty(tmp_path: Path) -> None:
    """
    Verifica que ``total_size_bytes`` é 0 quando não há dados enriquecidos.
    """
    result = _make_patched_run_analysis(tmp_path, {})

    assert result["statistics"]["total_size_bytes"] == 0


# ---------------------------------------------------------------------------
# Testes: statistics["avg_age_days"] é calculado corretamente
# ---------------------------------------------------------------------------


def test_statistics_avg_age_days_ignores_none(tmp_path: Path) -> None:
    """
    Confirma que ``avg_age_days`` é a média apenas dos age_days não-None.
    requests: 180 + flask: 365 → média = 272.5; numpy: None ignorado.
    """
    result = _make_patched_run_analysis(tmp_path, _MOCK_ENRICHED)

    expected = round((180 + 365) / 2, 2)
    assert result["statistics"]["avg_age_days"] == expected


def test_statistics_avg_age_days_none_when_all_none(tmp_path: Path) -> None:
    """
    Garante que ``avg_age_days`` é None quando todos os age_days são None.
    """
    all_none_age = {
        "requests": {"size_bytes": 1000, "age_days": None},
        "flask": {"size_bytes": 2000, "age_days": None},
    }
    result = _make_patched_run_analysis(tmp_path, all_none_age)

    assert result["statistics"]["avg_age_days"] is None


def test_statistics_avg_age_days_none_when_enriched_empty(tmp_path: Path) -> None:
    """
    Verifica que ``avg_age_days`` é None quando não há dados enriquecidos.
    """
    result = _make_patched_run_analysis(tmp_path, {})

    assert result["statistics"]["avg_age_days"] is None


# ---------------------------------------------------------------------------
# Testes: resiliência quando compute_enriched_metadata lança exceção
# ---------------------------------------------------------------------------


def test_run_analysis_does_not_break_when_enrichment_raises(tmp_path: Path) -> None:
    """
    Garante que o pipeline não quebra quando ``_enrich_dependencies`` retorna
    {} por falha interna (comportamento resiliente da função real):
    ``enriched_declared`` deve ser {} e o restante do resultado preenchido normalmente.
    """
    result = _make_patched_run_analysis(tmp_path, {}, raise_enrichment=True)

    # Pipeline não deve ter falhado — resultado possui campos esperados
    assert "enriched_declared" in result
    assert result["enriched_declared"] == {}
    assert "dependencies" in result
    assert "statistics" in result


def test_run_analysis_total_size_bytes_zero_when_enrichment_raises(tmp_path: Path) -> None:
    """
    Confirma que ``total_size_bytes`` é 0 quando o enriquecimento falha.
    """
    result = _make_patched_run_analysis(tmp_path, {}, raise_enrichment=True)

    assert result["statistics"]["total_size_bytes"] == 0


def test_run_analysis_avg_age_days_none_when_enrichment_raises(tmp_path: Path) -> None:
    """
    Confirma que ``avg_age_days`` é None quando o enriquecimento falha.
    """
    result = _make_patched_run_analysis(tmp_path, {}, raise_enrichment=True)

    assert result["statistics"]["avg_age_days"] is None


# ---------------------------------------------------------------------------
# Testes: _enrich_dependencies isolado
# ---------------------------------------------------------------------------


def test_enrich_dependencies_returns_dict_from_analyzer() -> None:
    """
    Testa ``_enrich_dependencies`` diretamente: confirma que repassa o retorno
    de ``compute_enriched_metadata`` sem modificação, usando um módulo stub
    injetado via sys.modules para simular a presença do age_size_analyzer.
    """
    import sys
    import types
    from src.orchestrator import _enrich_dependencies

    expected = {"requests": {"size_bytes": 200_000, "age_days": 100}}

    # Cria um módulo stub em memória para simular src.analyzers.age_size_analyzer
    stub_module = types.ModuleType("src.analyzers.age_size_analyzer")
    stub_module.compute_enriched_metadata = lambda declared: expected  # type: ignore[attr-defined]

    original = sys.modules.get("src.analyzers.age_size_analyzer")
    sys.modules["src.analyzers.age_size_analyzer"] = stub_module
    try:
        result = _enrich_dependencies(["requests>=2.0"])
    finally:
        if original is None:
            sys.modules.pop("src.analyzers.age_size_analyzer", None)
        else:
            sys.modules["src.analyzers.age_size_analyzer"] = original

    assert result == expected


def test_enrich_dependencies_returns_empty_dict_on_exception(monkeypatch) -> None:
    """
    Confirma que ``_enrich_dependencies`` retorna {} silenciosamente quando
    ``compute_enriched_metadata`` lança qualquer exceção (rede indisponível, etc.).
    """
    from src.orchestrator import _enrich_dependencies

    def _raise(*_args, **_kwargs):
        raise RuntimeError("PyPI indisponível")

    monkeypatch.setattr(
        "src.analyzers.age_size_analyzer.compute_enriched_metadata", _raise
    )

    result = _enrich_dependencies(["requests>=2.0"])
    assert result == {}
