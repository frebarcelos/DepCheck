from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

from src.analyzers.age_size_analyzer import (
    _compute_age_from_date,
    _extract_version_from_dep,
    compute_enriched_metadata,
    format_size_human,
)


# ---------------------------------------------------------------------------
# _extract_version_from_dep
# ---------------------------------------------------------------------------

def test_extract_version_pinned_equal():
    assert _extract_version_from_dep("requests==2.28.0") == "2.28.0"


def test_extract_version_gte_returns_none():
    assert _extract_version_from_dep("requests>=2.0") is None


def test_extract_version_compatible_returns_none():
    assert _extract_version_from_dep("requests~=2.28") is None


def test_extract_version_no_specifier_returns_none():
    assert _extract_version_from_dep("numpy") is None


def test_extract_version_lte_returns_none():
    assert _extract_version_from_dep("flask<=2.3.0") is None


def test_extract_version_complex_specifier():
    # Apenas == deve ser extraído; outros operadores são ignorados
    assert _extract_version_from_dep("django>=3.2,<4.0") is None


def test_extract_version_pinned_with_extra_spaces():
    assert _extract_version_from_dep("  scipy == 1.9.0  ") == "1.9.0"


# ---------------------------------------------------------------------------
# _compute_age_from_date
# ---------------------------------------------------------------------------

def test_compute_age_valid_date():
    past = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
    result = _compute_age_from_date(past)
    assert result is not None
    assert 29 <= result <= 31  # tolera 1 dia de diferença por horário


def test_compute_age_today():
    today = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    result = _compute_age_from_date(today)
    assert result is not None
    assert result == 0


def test_compute_age_none_input():
    assert _compute_age_from_date(None) is None


def test_compute_age_invalid_string():
    assert _compute_age_from_date("not-a-date") is None


def test_compute_age_empty_string():
    assert _compute_age_from_date("") is None


def test_compute_age_wrong_format():
    # Formato com timezone não suportado → None
    assert _compute_age_from_date("2023-04-15T10:23:45+00:00") is None


# ---------------------------------------------------------------------------
# format_size_human
# ---------------------------------------------------------------------------

def test_format_size_unavailable():
    assert format_size_human(-1) == "N/D"


def test_format_size_bytes():
    assert format_size_human(500) == "500 B"


def test_format_size_zero_bytes():
    assert format_size_human(0) == "0 B"


def test_format_size_kilobytes():
    result = format_size_human(102400)
    assert "KB" in result
    assert "100" in result


def test_format_size_megabytes():
    result = format_size_human(2 * 1024 * 1024)
    assert "MB" in result
    assert "2.0" in result


def test_format_size_exact_1kb():
    assert format_size_human(1024) == "1.0 KB"


def test_format_size_exact_1mb():
    assert format_size_human(1024 ** 2) == "1.0 MB"


# ---------------------------------------------------------------------------
# compute_enriched_metadata
# ---------------------------------------------------------------------------

_MOCK_PYPI_RESPONSE = {
    "info": {"version": "2.28.2"},
    "releases": {
        "2.28.2": [
            {
                "filename": "requests-2.28.2-py3-none-any.whl",
                "size": 62284,
                "upload_time": "2023-01-12T15:30:00",
            },
            {
                "filename": "requests-2.28.2.tar.gz",
                "size": 109513,
                "upload_time": "2023-01-12T15:30:00",
            },
        ]
    },
}


@patch("src.clients.pypi_client.get_pypi_package_info")
def test_compute_enriched_metadata_normal(mock_info):
    mock_info.return_value = _MOCK_PYPI_RESPONSE
    # Reset lru_cache so the mock is used
    from src.clients.pypi_client import fetch_package_size, fetch_release_date
    fetch_package_size.cache_clear()
    fetch_release_date.cache_clear()

    result = compute_enriched_metadata(["requests"])

    assert "requests" in result
    entry = result["requests"]
    assert entry["size_bytes"] == 62284  # wheel preferred
    assert entry["age_days"] is not None
    assert entry["age_days"] >= 0


@patch("src.clients.pypi_client.get_pypi_package_info")
def test_compute_enriched_metadata_pypi_none(mock_info):
    mock_info.return_value = None
    from src.clients.pypi_client import fetch_package_size, fetch_release_date
    fetch_package_size.cache_clear()
    fetch_release_date.cache_clear()

    result = compute_enriched_metadata(["unknown-pkg"])

    assert "unknown-pkg" in result
    entry = result["unknown-pkg"]
    assert entry["size_bytes"] == -1
    assert entry["age_days"] is None


@patch("src.clients.pypi_client.get_pypi_package_info")
def test_compute_enriched_metadata_pinned_version(mock_info):
    mock_info.return_value = _MOCK_PYPI_RESPONSE
    from src.clients.pypi_client import fetch_package_size, fetch_release_date
    fetch_package_size.cache_clear()
    fetch_release_date.cache_clear()

    result = compute_enriched_metadata(["requests==2.28.2"])

    assert "requests" in result
    # pinned version → consulta files da versão 2.28.2
    assert result["requests"]["size_bytes"] == 62284


@patch("src.clients.pypi_client.get_pypi_package_info")
def test_compute_enriched_metadata_multiple_deps(mock_info):
    mock_info.return_value = _MOCK_PYPI_RESPONSE
    from src.clients.pypi_client import fetch_package_size, fetch_release_date
    fetch_package_size.cache_clear()
    fetch_release_date.cache_clear()

    result = compute_enriched_metadata(["requests>=2.0", "numpy", "flask==2.3.0"])

    for pkg in ("requests", "numpy", "flask"):
        assert pkg in result
        assert "size_bytes" in result[pkg]
        assert "age_days" in result[pkg]


@patch("src.clients.pypi_client.get_pypi_package_info")
def test_compute_enriched_metadata_empty_list(mock_info):
    mock_info.return_value = _MOCK_PYPI_RESPONSE
    from src.clients.pypi_client import fetch_package_size, fetch_release_date
    fetch_package_size.cache_clear()
    fetch_release_date.cache_clear()

    result = compute_enriched_metadata([])
    assert result == {}
