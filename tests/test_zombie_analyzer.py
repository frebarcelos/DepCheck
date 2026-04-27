import pytest
from src.analyzers.zombie_analyzer import find_zombie_dependencies

def test_find_zombie_dependencies_healthy():
    declared = ["requests", "django>=3.2", "pillow"]
    imported = {"requests", "django", "PIL"}
    zombies = find_zombie_dependencies(declared, imported)
    assert not zombies

def test_find_zombie_dependencies_zombies_found():
    declared = ["requests", "numpy", "pandas==1.0"]
    imported = {"requests"}
    zombies = find_zombie_dependencies(declared, imported)
    assert "numpy" in zombies
    assert "pandas==1.0" in zombies

def test_case_insensitivity():
    declared = ["Flask", "PyYAML"]
    imported = {"flask", "yaml"}
    zombies = find_zombie_dependencies(declared, imported)
    assert not zombies
