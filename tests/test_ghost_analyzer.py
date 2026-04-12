import pytest
from src.analyzers.ghost_analyzer import find_ghost_dependencies

def test_find_ghost_dependencies():
    declared = ["requests", "django"]
    imported = {"requests", "django", "numpy", "json"} # json ignored by stdlib filter
    ghosts = find_ghost_dependencies(declared, imported)
    assert "numpy" in ghosts
    assert "requests" not in ghosts
    assert "json" not in ghosts
