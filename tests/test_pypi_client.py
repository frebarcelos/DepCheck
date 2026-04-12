from unittest.mock import patch, MagicMock
from src.clients.pypi_client import get_pypi_package_info

@patch("urllib.request.urlopen")
def test_get_pypi_package_info_success(mock_urlopen):
    # Mocking response
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"info": {"version": "1.0.0"}}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    # Clear cache since it's lru_cache
    get_pypi_package_info.cache_clear()
    
    data = get_pypi_package_info("dummy_package")
    assert data is not None
    assert data["info"]["version"] == "1.0.0"

@patch("urllib.request.urlopen")
def test_get_pypi_package_info_error(mock_urlopen):
    mock_urlopen.side_effect = Exception("Network Error")
    
    get_pypi_package_info.cache_clear()
    data = get_pypi_package_info("error_package")
    assert data is None
