from src.utils.stdlib_filters import filter_stdlib_imports

def test_filter_stdlib_imports():
    imports = {"os", "sys", "requests", "json", "pandas"}
    filtered = filter_stdlib_imports(imports)
    assert "os" not in filtered
    assert "sys" not in filtered
    assert "json" not in filtered
    assert "requests" in filtered
    assert "pandas" in filtered
