import pytest
from pathlib import Path
from src.parsers.requirements_parser import parse_requirements
from src.parsers.pyproject_parser import parse_pyproject
from src.code_parser import get_all_imports

def test_requirements_parser(tmp_path):
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("requests==2.25.1\ndjango>=3.0\npytest")
    deps = parse_requirements(req_file)
    assert "requests" in deps
    assert "django" in deps
    assert "pytest" in deps
    
def test_pyproject_parser(tmp_path):
    toml_file = tmp_path / "pyproject.toml"
    toml_file.write_text("[tool.poetry.dependencies]\nrequests = '*'\n")
    deps = parse_pyproject(toml_file)
    assert "requests" in deps
    
def test_code_parser(tmp_path):
    py_file = tmp_path / "main.py"
    py_file.write_text("import os\nfrom datetime import datetime\nimport requests")
    imports = get_all_imports(tmp_path)
    assert "requests" in imports
    assert "os" in imports
