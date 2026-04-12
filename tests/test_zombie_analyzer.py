"""
tests/test_zombie_analyzer.py
Testes unitários para src/analyzers/zombie_analyzer.py.
Cobre: happy path, cenários negativos, aliases, edge-cases.
"""
from src.analyzers.zombie_analyzer import extract_package_name, find_zombie_dependencies


# ── extract_package_name ────────────────────────────────────────────────────

def test_extract_plain_name() -> None:
    assert extract_package_name("requests") == "requests"

def test_extract_with_gte_operator() -> None:
    assert extract_package_name("requests>=2.28.0") == "requests"

def test_extract_with_eq_operator() -> None:
    assert extract_package_name("pandas==1.0") == "pandas"

def test_extract_with_tilde_operator() -> None:
    assert extract_package_name("flask~=3.0") == "flask"

def test_extract_with_extras() -> None:
    assert extract_package_name("requests[security]>=2.0") == "requests"

def test_extract_preserves_hyphens() -> None:
    assert extract_package_name("my-package>=1.0") == "my-package"

def test_extract_uppercase_lowercased() -> None:
    assert extract_package_name("Django>=3.2") == "django"


# ── find_zombie_dependencies — happy paths ──────────────────────────────────

def test_no_zombies_when_all_imported() -> None:
    declared = ["requests", "flask>=3.0", "numpy"]
    imported = {"requests", "flask", "numpy"}
    assert find_zombie_dependencies(declared, imported) == []

def test_detects_single_zombie() -> None:
    declared = ["requests", "unused-lib"]
    imported = {"requests"}
    zombies = find_zombie_dependencies(declared, imported)
    assert "unused-lib" in zombies
    assert "requests" not in zombies

def test_detects_multiple_zombies() -> None:
    declared = ["requests", "numpy", "pandas==1.0"]
    imported = {"requests"}
    zombies = find_zombie_dependencies(declared, imported)
    assert "numpy" in zombies
    assert "pandas==1.0" in zombies
    assert len(zombies) == 2

def test_all_declared_are_zombies() -> None:
    declared = ["unused-a", "unused-b"]
    imported = {"os", "sys"}
    zombies = find_zombie_dependencies(declared, imported)
    assert len(zombies) == 2

def test_case_insensitivity_declared() -> None:
    declared = ["Flask", "PyYAML"]
    imported = {"flask", "yaml"}
    assert find_zombie_dependencies(declared, imported) == []

def test_case_insensitivity_imported() -> None:
    declared = ["requests"]
    imported = {"Requests"}
    assert find_zombie_dependencies(declared, imported) == []


# ── find_zombie_dependencies — aliases (PIL → pillow, yaml → pyyaml) ───────

def test_pillow_alias_pil() -> None:
    """Pillow declarado + PIL importado → não é zumbi."""
    declared = ["pillow"]
    imported = {"PIL"}
    assert find_zombie_dependencies(declared, imported) == []

def test_yaml_alias_pyyaml() -> None:
    """pyyaml declarado + yaml importado → não é zumbi."""
    declared = ["pyyaml"]
    imported = {"yaml"}
    assert find_zombie_dependencies(declared, imported) == []

def test_sklearn_alias_scikit_learn() -> None:
    declared = ["scikit_learn"]
    imported = {"sklearn"}
    assert find_zombie_dependencies(declared, imported) == []


# ── find_zombie_dependencies — edge cases ───────────────────────────────────

def test_empty_declared_returns_empty() -> None:
    assert find_zombie_dependencies([], {"requests"}) == []

def test_empty_imported_all_are_zombies() -> None:
    declared = ["requests", "flask"]
    zombies = find_zombie_dependencies(declared, set())
    assert set(zombies) == {"requests", "flask"}

def test_both_empty_returns_empty() -> None:
    assert find_zombie_dependencies([], set()) == []

def test_preserves_original_dep_string() -> None:
    """Zumbi deve ser retornado com a string original, sem normalização."""
    declared = ["NumPy>=1.24.0"]
    imported = set()
    zombies = find_zombie_dependencies(declared, imported)
    assert "NumPy>=1.24.0" in zombies

def test_stdlib_module_still_marks_dep_as_zombie() -> None:
    """Se 'os' é importado mas 'os-lib' é declarado, 'os-lib' é zumbi."""
    declared = ["os-lib"]
    imported = {"os"}
    zombies = find_zombie_dependencies(declared, imported)
    assert "os-lib" in zombies

def test_dep_with_version_range_detected() -> None:
    declared = ["requests>=2.0,<3.0"]
    imported = set()
    zombies = find_zombie_dependencies(declared, imported)
    assert len(zombies) == 1

def test_return_type_is_list() -> None:
    result = find_zombie_dependencies(["x"], set())
    assert isinstance(result, list)
