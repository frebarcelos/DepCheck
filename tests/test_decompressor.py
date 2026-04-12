import pytest
from pathlib import Path
from src.decompressor import validate_zip, DecompressorError

def test_validate_zip_extension(tmp_path):
    invalid_file = tmp_path / "test.txt"
    invalid_file.write_text("dummy text content")
    
    with pytest.raises(DecompressorError, match="Formato inválido"):
        validate_zip(invalid_file)

def test_validate_zip_size(monkeypatch, tmp_path):
    valid_file = tmp_path / "test.zip"
    valid_file.write_text("dummy bytes base")
    
    # Mock file size to exceed max (assuming memory of 500MB max)
    def mock_stat(*args, **kwargs):
        class Stat:
            st_size = 9999 * 1024 * 1024 # 9.9GB
        return Stat()
        
    monkeypatch.setattr(Path, "stat", mock_stat)
    
    with pytest.raises(DecompressorError, match="Arquivo muito grande"):
        validate_zip(valid_file)

import zipfile
import uuid
from src.decompressor import extract_zip, cleanup_session

def test_extract_and_cleanup(tmp_path):
    # create a dummy zip
    dummy_zip = tmp_path / "dummy.zip"
    with zipfile.ZipFile(dummy_zip, "w") as zf:
        zf.writestr("test.py", "print('hello')")
        
    session_id = str(uuid.uuid4())
    dest_dir = extract_zip(dummy_zip, session_id)
    
    assert dest_dir.exists()
    assert (dest_dir / "test.py").exists()
    
    cleanup_session(session_id)
    assert not dest_dir.exists()

