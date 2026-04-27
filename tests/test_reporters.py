"""
tests/test_reporters.py  –  Dev 5 | Sprint 4
Testes básicos de regressão para exportadores CSV e JSON.
Atualizado para refletir o novo cabeçalho de 5 colunas do CSV (Sprint 4).
"""
from __future__ import annotations

import csv
import json

from core.results_model import get_empty_result_model
from src.reporters.csv_reporter import export_to_csv
from src.reporters.json_reporter import export_to_json


def build_dummy_model():
    model = get_empty_result_model()
    model["dependencies"]["declared"] = ["requests", "pandas"]
    model["dependencies"]["imported"] = ["requests", "numpy"]
    model["dependencies"]["zombies"] = ["pandas"]
    model["dependencies"]["ghosts"] = ["numpy"]
    model["dependencies"]["outdated"] = {"requests": {"days_outdated": 5, "latest_version": "2.26.0"}}
    return model


def test_json_reporter(tmp_path):
    model = build_dummy_model()
    out_file = tmp_path / "report.json"
    export_to_json(model, str(out_file))

    with open(out_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["dependencies"]["zombies"] == ["pandas"]


def test_json_reporter_has_metadata(tmp_path):
    """Exportação JSON deve incluir metadados de versão e timestamp."""
    model = build_dummy_model()
    out_file = tmp_path / "report.json"
    export_to_json(model, str(out_file))

    with open(out_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "exported_at" in data
    assert "version" in data
    assert data["version"] == "0.4.1"


def test_csv_reporter(tmp_path):
    model = build_dummy_model()
    out_file = tmp_path / "report.csv"
    export_to_csv(model, str(out_file))

    with open(out_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=';')
        rows = list(reader)

    # Headers + 3 deps (pandas, numpy, requests)
    assert len(rows) == 4
    # Sprint 4: cabeçalho agora tem 5 colunas com campos enriquecidos
    assert rows[0] == ["Pacote", "Status", "Tamanho (KB)", "Idade (dias)", "Outdated (Dias)"]
