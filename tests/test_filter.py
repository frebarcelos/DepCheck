import pytest
from pathlib import Path
from src.filter import filter_extracted

def test_filter_extracted(tmp_path, monkeypatch):
    # Create valid file
    valid_py = tmp_path / "main.py"
    valid_py.write_text("print('hello')")
    
    # Create ignored file
    ignored_txt = tmp_path / "readme.txt"
    ignored_txt.write_text("hello")
    
    # Create ignored dir
    ignored_dir = tmp_path / ".git"
    ignored_dir.mkdir()
    ignored_dir_py = ignored_dir / "hidden.py"
    ignored_dir_py.write_text("hidden")
    
    kept = filter_extracted(tmp_path)

    assert len(kept) == 1
    assert kept[0].name == "main.py"
    # Arquivos não-.py são preservados no disco (manifests como pyproject.toml precisam sobreviver)
    assert ignored_txt.exists()
    # Diretórios ignorados (.git, tests/, etc.) ainda são removidos
    assert not ignored_dir.exists()
