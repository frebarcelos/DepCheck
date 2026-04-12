"""
tests/test_reporters_enriched.py  –  Dev 5 | Sprint 4
Testes para exportadores CSV/JSON com dados enriquecidos (enriched_declared)
e para a função get_size_chart_data() do módulo gui/charts.py.
"""
from __future__ import annotations

import csv
import json

import pytest

from core.results_model import get_empty_result_model
from gui.charts import get_size_chart_data
from src.reporters.csv_reporter import export_to_csv
from src.reporters.json_reporter import export_to_json


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


def _build_model_with_enriched() -> dict:
    """Retorna result_model completo com enriched_declared preenchido."""
    model = get_empty_result_model()
    model["dependencies"]["declared"] = ["requests", "flask", "boto3"]
    model["dependencies"]["imported"] = ["requests", "flask"]
    model["dependencies"]["zombies"] = ["boto3"]
    model["dependencies"]["ghosts"] = []
    model["dependencies"]["outdated"] = {
        "requests": {"days_outdated": 45, "latest_version": "2.32.0"}
    }
    model["enriched_declared"] = {
        "requests": {"size_bytes": 102400, "age_days": 180},
        "flask": {"size_bytes": 204800, "age_days": 90},
        "boto3": {"size_bytes": -1, "age_days": None},
    }
    return model


def _build_model_without_enriched() -> dict:
    """Retorna result_model sem a chave enriched_declared (retrocompat)."""
    model = get_empty_result_model()
    model["dependencies"]["declared"] = ["numpy", "pandas"]
    model["dependencies"]["imported"] = ["numpy", "pandas"]
    model["dependencies"]["zombies"] = []
    model["dependencies"]["ghosts"] = []
    model["dependencies"]["outdated"] = {}
    return model


# ══════════════════════════════════════════════════════════════════════════════
# TESTES: export_to_csv() com enriched_declared
# ══════════════════════════════════════════════════════════════════════════════


def test_csv_with_enriched_has_correct_header(tmp_path):
    """Cabeçalho do CSV deve conter os 5 campos esperados."""
    model = _build_model_with_enriched()
    out_file = tmp_path / "report.csv"
    export_to_csv(model, str(out_file))

    with open(out_file, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)

    assert header == ["Pacote", "Status", "Tamanho (KB)", "Idade (dias)", "Outdated (Dias)"]


def test_csv_with_enriched_size_column_populated(tmp_path):
    """Coluna Tamanho (KB) deve ter valor numérico para pacotes com size_bytes > 0."""
    model = _build_model_with_enriched()
    out_file = tmp_path / "report.csv"
    export_to_csv(model, str(out_file))

    with open(out_file, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        rows = {row["Pacote"]: row for row in reader}

    # requests: 102400 bytes → 100.0 KB
    assert rows["requests"]["Tamanho (KB)"] == "100.0"
    # flask: 204800 bytes → 200.0 KB
    assert rows["flask"]["Tamanho (KB)"] == "200.0"


def test_csv_with_enriched_size_nd_when_negative(tmp_path):
    """Coluna Tamanho (KB) deve ser 'N/D' quando size_bytes == -1."""
    model = _build_model_with_enriched()
    out_file = tmp_path / "report.csv"
    export_to_csv(model, str(out_file))

    with open(out_file, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        rows = {row["Pacote"]: row for row in reader}

    assert rows["boto3"]["Tamanho (KB)"] == "N/D"


def test_csv_with_enriched_age_column_populated(tmp_path):
    """Coluna Idade (dias) deve ter valor inteiro para pacotes com age_days preenchido."""
    model = _build_model_with_enriched()
    out_file = tmp_path / "report.csv"
    export_to_csv(model, str(out_file))

    with open(out_file, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        rows = {row["Pacote"]: row for row in reader}

    assert rows["requests"]["Idade (dias)"] == "180"
    assert rows["flask"]["Idade (dias)"] == "90"


def test_csv_with_enriched_age_nd_when_none(tmp_path):
    """Coluna Idade (dias) deve ser 'N/D' quando age_days é None."""
    model = _build_model_with_enriched()
    out_file = tmp_path / "report.csv"
    export_to_csv(model, str(out_file))

    with open(out_file, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        rows = {row["Pacote"]: row for row in reader}

    assert rows["boto3"]["Idade (dias)"] == "N/D"


def test_csv_with_enriched_outdated_days_filled(tmp_path):
    """Coluna Outdated (Dias) deve ter valor numérico para pacotes desatualizados."""
    model = _build_model_with_enriched()
    out_file = tmp_path / "report.csv"
    export_to_csv(model, str(out_file))

    with open(out_file, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        rows = {row["Pacote"]: row for row in reader}

    assert rows["requests"]["Outdated (Dias)"] == "45"


# ══════════════════════════════════════════════════════════════════════════════
# TESTES: export_to_csv() sem enriched_declared (retrocompatibilidade)
# ══════════════════════════════════════════════════════════════════════════════


def test_csv_without_enriched_does_not_raise(tmp_path):
    """export_to_csv() deve funcionar sem erros quando enriched_declared está ausente."""
    model = _build_model_without_enriched()
    out_file = tmp_path / "report_no_enriched.csv"
    # Não deve lançar exceção
    export_to_csv(model, str(out_file))
    assert out_file.exists()


def test_csv_without_enriched_size_is_nd(tmp_path):
    """Sem enriched_declared, colunas Tamanho e Idade devem ser 'N/D'."""
    model = _build_model_without_enriched()
    out_file = tmp_path / "report_no_enriched.csv"
    export_to_csv(model, str(out_file))

    with open(out_file, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        rows = list(reader)

    assert len(rows) == 2  # numpy e pandas
    for row in rows:
        assert row["Tamanho (KB)"] == "N/D"
        assert row["Idade (dias)"] == "N/D"


def test_csv_without_enriched_has_five_columns(tmp_path):
    """Mesmo sem enriched_declared o CSV deve ter o cabeçalho de 5 colunas."""
    model = _build_model_without_enriched()
    out_file = tmp_path / "report_no_enriched.csv"
    export_to_csv(model, str(out_file))

    with open(out_file, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)

    assert len(header) == 5


# ══════════════════════════════════════════════════════════════════════════════
# TESTES: export_to_json() com metadados e enriched_declared
# ══════════════════════════════════════════════════════════════════════════════


def test_json_includes_enriched_declared(tmp_path):
    """Arquivo JSON exportado deve conter a chave enriched_declared."""
    model = _build_model_with_enriched()
    out_file = tmp_path / "report.json"
    export_to_json(model, str(out_file))

    with open(out_file, encoding="utf-8") as f:
        data = json.load(f)

    assert "enriched_declared" in data
    assert data["enriched_declared"]["requests"]["size_bytes"] == 102400
    assert data["enriched_declared"]["flask"]["age_days"] == 90


def test_json_includes_exported_at_metadata(tmp_path):
    """Arquivo JSON exportado deve conter a chave exported_at com timestamp ISO."""
    model = _build_model_with_enriched()
    out_file = tmp_path / "report.json"
    export_to_json(model, str(out_file))

    with open(out_file, encoding="utf-8") as f:
        data = json.load(f)

    assert "exported_at" in data
    # Valida que é um timestamp ISO (contém 'T' separando data e hora)
    assert "T" in data["exported_at"]


def test_json_includes_version_metadata(tmp_path):
    """Arquivo JSON exportado deve conter a chave version com valor '0.4.1'."""
    model = _build_model_with_enriched()
    out_file = tmp_path / "report.json"
    export_to_json(model, str(out_file))

    with open(out_file, encoding="utf-8") as f:
        data = json.load(f)

    assert "version" in data
    assert data["version"] == "0.4.1"


def test_json_preserves_dependencies(tmp_path):
    """Arquivo JSON exportado deve preservar as dependências originais do result_model."""
    model = _build_model_with_enriched()
    out_file = tmp_path / "report.json"
    export_to_json(model, str(out_file))

    with open(out_file, encoding="utf-8") as f:
        data = json.load(f)

    assert data["dependencies"]["zombies"] == ["boto3"]
    assert data["dependencies"]["declared"] == ["requests", "flask", "boto3"]


def test_json_without_enriched_still_has_metadata(tmp_path):
    """Mesmo sem enriched_declared, o JSON deve conter exported_at e version."""
    model = _build_model_without_enriched()
    out_file = tmp_path / "report_simple.json"
    export_to_json(model, str(out_file))

    with open(out_file, encoding="utf-8") as f:
        data = json.load(f)

    assert "exported_at" in data
    assert "version" in data
    # enriched_declared é sempre incluído no JSON (pode estar vazio)
    assert "enriched_declared" in data
    assert data["enriched_declared"] == {}


# ══════════════════════════════════════════════════════════════════════════════
# TESTES: get_size_chart_data()
# ══════════════════════════════════════════════════════════════════════════════


def _build_result_with_sizes() -> dict:
    """Retorna result dict com enriched_declared contendo dados de tamanho."""
    return {
        "enriched_declared": {
            "django": {"size_bytes": 5_000_000, "age_days": 10},
            "numpy": {"size_bytes": 3_000_000, "age_days": 20},
            "flask": {"size_bytes": 200_000, "age_days": 30},
            "requests": {"size_bytes": 100_000, "age_days": 180},
            "boto3": {"size_bytes": 800_000, "age_days": None},
            "pandas": {"size_bytes": 4_000_000, "age_days": 5},
            "scipy": {"size_bytes": 2_000_000, "age_days": 60},
            "sqlalchemy": {"size_bytes": 1_500_000, "age_days": 45},
            "celery": {"size_bytes": 600_000, "age_days": 90},
            "fastapi": {"size_bytes": 300_000, "age_days": 15},
            "uvicorn": {"size_bytes": 150_000, "age_days": 7},
            "pydantic": {"size_bytes": 900_000, "age_days": 3},
        }
    }


def test_get_size_chart_data_returns_top_10(tmp_path):
    """get_size_chart_data() deve retornar no máximo 10 pacotes."""
    result = _build_result_with_sizes()
    data = get_size_chart_data(result)

    assert len(data["packages"]) <= 10
    assert len(data["sizes_kb"]) <= 10
    assert len(data["packages"]) == len(data["sizes_kb"])


def test_get_size_chart_data_ordered_descending(tmp_path):
    """Os pacotes devem ser ordenados por tamanho decrescente."""
    result = _build_result_with_sizes()
    data = get_size_chart_data(result)

    sizes = data["sizes_kb"]
    assert sizes == sorted(sizes, reverse=True)


def test_get_size_chart_data_largest_package_first(tmp_path):
    """O maior pacote deve aparecer primeiro na lista."""
    result = _build_result_with_sizes()
    data = get_size_chart_data(result)

    # django tem 5_000_000 bytes = 4882.81 KB → deve ser o maior
    assert data["packages"][0] == "django"


def test_get_size_chart_data_excludes_negative_sizes(tmp_path):
    """Pacotes com size_bytes <= 0 não devem aparecer no gráfico."""
    result: dict = {
        "enriched_declared": {
            "pacote-ok": {"size_bytes": 50_000, "age_days": 10},
            "pacote-sem-tamanho": {"size_bytes": -1, "age_days": 5},
            "pacote-zero": {"size_bytes": 0, "age_days": 2},
        }
    }
    data = get_size_chart_data(result)

    assert "pacote-sem-tamanho" not in data["packages"]
    assert "pacote-zero" not in data["packages"]
    assert "pacote-ok" in data["packages"]


def test_get_size_chart_data_sizes_in_kb(tmp_path):
    """Os valores de sizes_kb devem estar em KB (bytes / 1024)."""
    result: dict = {
        "enriched_declared": {
            "mypkg": {"size_bytes": 10_240, "age_days": 1},
        }
    }
    data = get_size_chart_data(result)

    assert data["packages"] == ["mypkg"]
    assert data["sizes_kb"] == [10.0]  # 10_240 / 1024 = 10.0


def test_get_size_chart_data_empty_when_no_enriched(tmp_path):
    """Sem enriched_declared, get_size_chart_data() deve retornar listas vazias."""
    result = get_empty_result_model()
    data = get_size_chart_data(result)

    assert data == {"packages": [], "sizes_kb": []}


def test_get_size_chart_data_empty_when_all_negative(tmp_path):
    """Se todos size_bytes forem negativos, deve retornar listas vazias."""
    result: dict = {
        "enriched_declared": {
            "pkg-a": {"size_bytes": -1, "age_days": 10},
            "pkg-b": {"size_bytes": -1, "age_days": 5},
        }
    }
    data = get_size_chart_data(result)

    assert data == {"packages": [], "sizes_kb": []}
