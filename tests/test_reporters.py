import json
import csv
from core.results_model import get_empty_result_model
from src.reporters.json_reporter import export_to_json
from src.reporters.csv_reporter import export_to_csv

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

def test_csv_reporter(tmp_path):
    model = build_dummy_model()
    out_file = tmp_path / "report.csv"
    export_to_csv(model, str(out_file))

    with open(out_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=';')
        rows = list(reader)

    # Headers + deps (pandas, numpy, requests)
    assert rows[0] == ["Pacote", "Status", "Tamanho (KB)", "Idade (dias)", "Outdated (Dias)"]
    assert len(rows) >= 2  # cabeçalho + ao menos 1 dep
