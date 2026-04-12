from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from src.clients.pypi_client import fetch_package_size, fetch_release_date, get_pypi_package_info


# Payload PyPI realista usado nos testes
_PYPI_PAYLOAD = {
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
        ],
        "2.27.0": [
            {
                "filename": "requests-2.27.0.tar.gz",
                "size": 108000,
                "upload_time": "2022-06-01T10:00:00",
            }
        ],
    },
}


def _make_mock_urlopen(payload: dict):
    """Cria um mock de urlopen que retorna o payload serializado."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = json.dumps(payload).encode("utf-8")
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_response)
    mock_ctx.__exit__ = MagicMock(return_value=False)
    mock_urlopen = MagicMock(return_value=mock_ctx)
    return mock_urlopen


# ---------------------------------------------------------------------------
# fetch_package_size
# ---------------------------------------------------------------------------

@patch("urllib.request.urlopen")
def test_fetch_package_size_returns_bytes(mock_urlopen):
    mock_urlopen.side_effect = _make_mock_urlopen(_PYPI_PAYLOAD)
    get_pypi_package_info.cache_clear()
    fetch_package_size.cache_clear()

    size = fetch_package_size("requests")
    # Versão latest (2.28.2) → wheel preferido → 62284
    assert size == 62284


@patch("urllib.request.urlopen")
def test_fetch_package_size_prefers_wheel_over_sdist(mock_urlopen):
    mock_urlopen.side_effect = _make_mock_urlopen(_PYPI_PAYLOAD)
    get_pypi_package_info.cache_clear()
    fetch_package_size.cache_clear()

    size = fetch_package_size("requests")
    # O sdist tem 109513; o wheel tem 62284 → deve preferir wheel
    assert size == 62284
    assert size != 109513


@patch("urllib.request.urlopen")
def test_fetch_package_size_sdist_only(mock_urlopen):
    """Quando não há wheel, usa o primeiro arquivo disponível (sdist)."""
    payload_sdist_only = {
        "info": {"version": "2.27.0"},
        "releases": {
            "2.27.0": [
                {
                    "filename": "requests-2.27.0.tar.gz",
                    "size": 108000,
                    "upload_time": "2022-06-01T10:00:00",
                }
            ]
        },
    }
    mock_urlopen.side_effect = _make_mock_urlopen(payload_sdist_only)
    get_pypi_package_info.cache_clear()
    fetch_package_size.cache_clear()

    size = fetch_package_size("requests")
    assert size == 108000


@patch("urllib.request.urlopen")
def test_fetch_package_size_http_error_returns_minus_one(mock_urlopen):
    mock_urlopen.side_effect = Exception("HTTP 404")
    get_pypi_package_info.cache_clear()
    fetch_package_size.cache_clear()

    size = fetch_package_size("nonexistent-package-xyz")
    assert size == -1


@patch("urllib.request.urlopen")
def test_fetch_package_size_specific_version(mock_urlopen):
    mock_urlopen.side_effect = _make_mock_urlopen(_PYPI_PAYLOAD)
    get_pypi_package_info.cache_clear()
    fetch_package_size.cache_clear()

    # Versão 2.27.0 só tem sdist com 108000 bytes
    size = fetch_package_size("requests", "2.27.0")
    assert size == 108000


@patch("urllib.request.urlopen")
def test_fetch_package_size_version_not_in_releases(mock_urlopen):
    mock_urlopen.side_effect = _make_mock_urlopen(_PYPI_PAYLOAD)
    get_pypi_package_info.cache_clear()
    fetch_package_size.cache_clear()

    size = fetch_package_size("requests", "99.0.0")
    assert size == -1


# ---------------------------------------------------------------------------
# fetch_release_date
# ---------------------------------------------------------------------------

@patch("urllib.request.urlopen")
def test_fetch_release_date_returns_iso_string(mock_urlopen):
    mock_urlopen.side_effect = _make_mock_urlopen(_PYPI_PAYLOAD)
    get_pypi_package_info.cache_clear()
    fetch_release_date.cache_clear()

    date = fetch_release_date("requests")
    assert date == "2023-01-12T15:30:00"


@patch("urllib.request.urlopen")
def test_fetch_release_date_specific_version(mock_urlopen):
    mock_urlopen.side_effect = _make_mock_urlopen(_PYPI_PAYLOAD)
    get_pypi_package_info.cache_clear()
    fetch_release_date.cache_clear()

    date = fetch_release_date("requests", "2.27.0")
    assert date == "2022-06-01T10:00:00"


@patch("urllib.request.urlopen")
def test_fetch_release_date_http_error_returns_none(mock_urlopen):
    mock_urlopen.side_effect = Exception("HTTP 500")
    get_pypi_package_info.cache_clear()
    fetch_release_date.cache_clear()

    date = fetch_release_date("broken-pkg")
    assert date is None


@patch("urllib.request.urlopen")
def test_fetch_release_date_version_not_found_returns_none(mock_urlopen):
    mock_urlopen.side_effect = _make_mock_urlopen(_PYPI_PAYLOAD)
    get_pypi_package_info.cache_clear()
    fetch_release_date.cache_clear()

    date = fetch_release_date("requests", "0.0.0")
    assert date is None


@patch("urllib.request.urlopen")
def test_fetch_release_date_missing_upload_time_returns_none(mock_urlopen):
    payload_no_time = {
        "info": {"version": "1.0.0"},
        "releases": {
            "1.0.0": [{"filename": "pkg-1.0.0.whl", "size": 1000}]  # sem upload_time
        },
    }
    mock_urlopen.side_effect = _make_mock_urlopen(payload_no_time)
    get_pypi_package_info.cache_clear()
    fetch_release_date.cache_clear()

    date = fetch_release_date("some-pkg")
    assert date is None
