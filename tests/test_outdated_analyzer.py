from unittest.mock import patch
from datetime import datetime, timedelta
from src.analyzers.outdated_analyzer import check_outdated_dependencies

@patch("src.analyzers.outdated_analyzer.get_pypi_package_info")
def test_check_outdated_dependencies(mock_get_info):
    past_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S")
    
    mock_get_info.return_value = {
        "info": {"version": "2.0.0"},
        "releases": {
            "2.0.0": [{"upload_time": past_date}]
        }
    }
    
    declared = ["requests"]
    outdated = check_outdated_dependencies(declared)
    assert "requests" in outdated
    assert outdated["requests"]["latest_version"] == "2.0.0"
    assert outdated["requests"]["days_outdated"] == 10
