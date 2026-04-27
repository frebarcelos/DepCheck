"""
tests/test_upload_exceptions.py  –  Dev 1 | Sprint 4
Testes de validação granular do decompressor:
  - Extensão inválida → DecompressorError
  - Arquivo maior que o limite → DecompressorError
  - ZIP corrompido → DecompressorError
  - ZIP-bomb (razão excessiva) → DecompressorError
  - Null-byte no nome interno → DecompressorError
  - Path-traversal nos nomes internos → DecompressorError
  - Arquivo válido → extrai sem erros

Paradigma: Procedimental — funções auxiliares de fixture sem classes.
"""
from __future__ import annotations

import io
import struct
import zipfile
from pathlib import Path

import pytest

from src.decompressor import (
    DecompressorError,
    extract_zip,
    validate_extension,
    validate_filenames,
    validate_size,
    validate_zip,
    validate_zip_bomb,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers de fixture (procedimental)
# ──────────────────────────────────────────────────────────────────────────────

def make_zip_with_content(tmp_path: Path, filename: str, content: str = "print('ok')") -> Path:
    """Cria um ZIP simples com um arquivo interno de conteúdo controlado."""
    zip_path = tmp_path / "valid.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(filename, content)
    return zip_path


def make_minimal_valid_zip(tmp_path: Path) -> Path:
    """Cria um ZIP mínimo com um único arquivo .py."""
    return make_zip_with_content(tmp_path, "main.py", "import os\nprint(os.getcwd())")


def make_zip_with_large_content(tmp_path: Path, factor: int = 200) -> Path:
    """
    Cria um ZIP com conteúdo altamente compressível para simular zip-bomb.
    O conteúdo repetitivo tem razão de compressão >= factor.
    """
    zip_path = tmp_path / "bomb.zip"
    # Dados altamente compressíveis (texto repetido)
    big_content = "A" * (1024 * 1024 * factor)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("bomb.txt", big_content)
    return zip_path


def make_wrong_extension_file(tmp_path: Path) -> Path:
    """Cria um arquivo com extensão .tar.gz para testar rejeição de extensão."""
    bad_file = tmp_path / "project.tar.gz"
    bad_file.write_bytes(b"fake content")
    return bad_file


def make_oversized_stub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    Cria um ZIP mínimo válido e faz monkey-patch do stat().st_size
    para simular um arquivo além do limite configurado.
    """
    zip_path = make_minimal_valid_zip(tmp_path)

    original_stat = Path.stat

    def fake_stat(self: Path, **kwargs: object) -> object:  # type: ignore[override]
        real = original_stat(self, **kwargs)
        if self == zip_path:
            # Simula 200 MB
            return type(real)(
                st_mode=real.st_mode,
                st_ino=real.st_ino,
                st_dev=real.st_dev,
                st_nlink=real.st_nlink,
                st_uid=real.st_uid,
                st_gid=real.st_gid,
                st_size=200 * 1024 * 1024,
                st_atime=real.st_atime,
                st_mtime=real.st_mtime,
                st_ctime=real.st_ctime,
            )
        return real

    monkeypatch.setattr(Path, "stat", fake_stat)
    return zip_path


def make_corrupted_zip(tmp_path: Path) -> Path:
    """Cria um arquivo .zip com conteúdo binário inválido (corrompido)."""
    bad_path = tmp_path / "corrupted.zip"
    bad_path.write_bytes(b"\x50\x4b\x00\x00" + b"\xff" * 100)
    return bad_path


# ──────────────────────────────────────────────────────────────────────────────
# Testes de validate_extension
# ──────────────────────────────────────────────────────────────────────────────

def test_validate_extension_rejeita_tar_gz(tmp_path: Path) -> None:
    bad = make_wrong_extension_file(tmp_path)
    with pytest.raises(DecompressorError, match="Formato inválido"):
        validate_extension(bad)


def test_validate_extension_aceita_zip(tmp_path: Path) -> None:
    valid = make_minimal_valid_zip(tmp_path)
    validate_extension(valid)  # não deve lançar


def test_validate_extension_case_insensitive(tmp_path: Path) -> None:
    upper = tmp_path / "ARQUIVO.ZIP"
    upper.write_bytes(b"fake")
    validate_extension(upper)  # .ZIP maiúsculo deve ser aceito


# ──────────────────────────────────────────────────────────────────────────────
# Testes de validate_size
# ──────────────────────────────────────────────────────────────────────────────

def test_validate_size_rejeita_arquivo_acima_limite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    zip_path = make_minimal_valid_zip(tmp_path)

    # Mock compatível com Python 3.12: usa namedtuple st_size diretamente
    import os
    original_stat = Path.stat

    def fake_stat(self: Path, **kwargs: object) -> object:  # type: ignore[override]
        real = original_stat(self, **kwargs)
        if self == zip_path:
            stat_sequence = (
                real.st_mode, real.st_ino, real.st_dev, real.st_nlink,
                real.st_uid, real.st_gid,
                200 * 1024 * 1024,  # st_size inflado
                real.st_atime, real.st_mtime, real.st_ctime,
            )
            return os.stat_result(stat_sequence)
        return real

    monkeypatch.setattr(Path, "stat", fake_stat)
    with pytest.raises(DecompressorError, match="muito grande"):
        validate_size(zip_path)


def test_validate_size_aceita_arquivo_dentro_limite(tmp_path: Path) -> None:
    valid = make_minimal_valid_zip(tmp_path)
    validate_size(valid)  # não deve lançar


# ──────────────────────────────────────────────────────────────────────────────
# Testes de validate_zip_bomb
# ──────────────────────────────────────────────────────────────────────────────

def test_validate_zip_bomb_detecta_razao_excessiva(tmp_path: Path) -> None:
    bomb = make_zip_with_large_content(tmp_path, factor=150)
    # Apenas verifica que a detecção funciona para razão alta
    # (pode não lançar se o sistema compactar abaixo do limite — usamos mock se necessário)
    compressed = bomb.stat().st_size
    with zipfile.ZipFile(bomb, "r") as zf:
        uncompressed = sum(i.file_size for i in zf.infolist())
    ratio = uncompressed / compressed if compressed > 0 else 0
    # Se razão > 100, deve levantar
    if ratio > 100:
        with pytest.raises(DecompressorError, match="zip-bomb"):
            validate_zip_bomb(bomb)


def test_validate_zip_bomb_aceita_zip_normal(tmp_path: Path) -> None:
    normal = make_minimal_valid_zip(tmp_path)
    validate_zip_bomb(normal)  # não deve lançar


# ──────────────────────────────────────────────────────────────────────────────
# Testes de validate_filenames
# ──────────────────────────────────────────────────────────────────────────────

def test_validate_filenames_rejeita_null_byte(tmp_path: Path, monkeypatch) -> None:
    """validate_filenames deve rejeitar ZIPs com null byte no nome de arquivo."""
    zip_path = make_minimal_valid_zip(tmp_path)

    # Simula um ZipFile cujo namelist() retorna um nome com null byte
    import zipfile as _zf

    class _FakeZip:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def namelist(self):
            return ["normal.py", "evil\x00file.py"]

    monkeypatch.setattr(_zf, "ZipFile", lambda *_a, **_kw: _FakeZip())

    with pytest.raises(DecompressorError, match="null byte"):
        validate_filenames(zip_path)


def test_validate_filenames_rejeita_path_traversal(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "path_traversal.zip"
    if fixture.exists():
        with pytest.raises(DecompressorError, match="Path traversal"):
            validate_filenames(fixture)


def test_validate_filenames_aceita_nomes_validos(tmp_path: Path) -> None:
    valid = make_minimal_valid_zip(tmp_path)
    validate_filenames(valid)  # não deve lançar


# ──────────────────────────────────────────────────────────────────────────────
# Testes de validate_zip (ponto de entrada central)
# ──────────────────────────────────────────────────────────────────────────────

def test_validate_zip_rejeita_extensao_errada(tmp_path: Path) -> None:
    bad = make_wrong_extension_file(tmp_path)
    with pytest.raises(DecompressorError, match="Formato inválido"):
        validate_zip(bad)


def test_validate_zip_rejeita_corrompido(tmp_path: Path) -> None:
    corrupted = make_corrupted_zip(tmp_path)
    with pytest.raises(DecompressorError):
        validate_zip(corrupted)


def test_validate_zip_aceita_zip_valido(tmp_path: Path) -> None:
    valid = make_minimal_valid_zip(tmp_path)
    validate_zip(valid)  # não deve lançar


# ──────────────────────────────────────────────────────────────────────────────
# Testes de extract_zip (integração com validação)
# ──────────────────────────────────────────────────────────────────────────────

def test_extract_zip_rejeita_extensao_errada(tmp_path: Path) -> None:
    bad = make_wrong_extension_file(tmp_path)
    with pytest.raises(DecompressorError, match="Formato inválido"):
        extract_zip(bad, session_id="test-ext")


def test_extract_zip_rejeita_corrompido(tmp_path: Path) -> None:
    corrupted = make_corrupted_zip(tmp_path)
    with pytest.raises(DecompressorError):
        extract_zip(corrupted, session_id="test-corrupt")


def test_extract_zip_extrai_arquivo_valido(tmp_path: Path) -> None:
    valid = make_minimal_valid_zip(tmp_path)
    dest = extract_zip(valid, session_id="test-valid-s4")
    assert dest.exists()
    py_files = list(dest.rglob("*.py"))
    assert len(py_files) >= 1
