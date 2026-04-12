"""
src/decompressor.py  –  Dev 1 | Sprint 4
Validação defensiva completa de arquivos ZIP:
  - Extensão obrigatória (.zip)
  - Limite de tamanho configurável (MAX_ZIP_SIZE_BYTES)
  - Detecção de zip-bomb via razão descomprimido/comprimido (MAX_ZIP_RATIO)
  - Proteção contra nomes com null-byte
  - Proteção contra path-traversal (zip-slip)
  - Extração segura em diretório isolado por sessão
  - Limpeza de sessão temporária

Paradigma: Procedimental — apenas funções, sem classes de domínio.
"""
from __future__ import annotations

import logging
import shutil
import uuid
import zipfile
from pathlib import Path

from core.constants import MAX_ZIP_RATIO, MAX_ZIP_SIZE_BYTES
from core.paths import TEMP_DIR, get_upload_dir

logger = logging.getLogger(__name__)


class DecompressorError(Exception):
    """Erros de validação ou extração do ZIP."""


# ──────────────────────────────────────────────────────────────────────────────
# Funções granulares de validação — Sprint 4 (Dev 1)
# ──────────────────────────────────────────────────────────────────────────────

def validate_extension(file_path: Path) -> None:
    """
    Verifica se o arquivo possui extensão '.zip'.

    Args:
        file_path: Caminho para o arquivo a ser validado.

    Raises:
        DecompressorError: se a extensão não for '.zip'.
    """
    if file_path.suffix.lower() != ".zip":
        raise DecompressorError(
            f"Formato inválido: esperado '.zip', recebido '{file_path.suffix}'. "
            "Envie apenas arquivos .zip."
        )


def validate_size(file_path: Path) -> None:
    """
    Verifica se o arquivo não excede MAX_ZIP_SIZE_BYTES.

    Args:
        file_path: Caminho para o arquivo a ser validado.

    Raises:
        DecompressorError: se o arquivo ultrapassar o limite configurado.
    """
    size = file_path.stat().st_size
    if size > MAX_ZIP_SIZE_BYTES:
        limit_mb = MAX_ZIP_SIZE_BYTES // (1024 * 1024)
        actual_mb = size / (1024 * 1024)
        raise DecompressorError(
            f"Arquivo muito grande: {actual_mb:.1f} MB (limite: {limit_mb} MB). "
            "Reduza o projeto ou exclua artefatos pesados antes de compactar."
        )


def validate_zip_bomb(file_path: Path) -> None:
    """
    Detecta potenciais zip-bombs verificando a razão entre o tamanho
    descomprimido total e o tamanho comprimido do arquivo.

    Se a razão superar MAX_ZIP_RATIO, o arquivo é rejeitado por segurança.

    Args:
        file_path: Caminho para o arquivo .zip já confirmado como ZIP real.

    Raises:
        DecompressorError: se a razão de expansão exceder o limite seguro.
    """
    compressed_size = file_path.stat().st_size
    if compressed_size == 0:
        return

    with zipfile.ZipFile(file_path, "r") as zf:
        uncompressed_size = sum(info.file_size for info in zf.infolist())

    ratio = uncompressed_size / compressed_size
    if ratio > MAX_ZIP_RATIO:
        raise DecompressorError(
            f"ZIP suspeito: razão de expansão {ratio:.1f}x excede o limite de "
            f"{MAX_ZIP_RATIO}x. Possível zip-bomb detectado. Envio bloqueado."
        )


def validate_filenames(file_path: Path) -> None:
    """
    Verifica nomes de arquivos internos ao ZIP em busca de:
      - Caracteres nulos (null-byte poisoning)
      - Sequências de path-traversal ('..') — verificação defensiva redundante

    Args:
        file_path: Caminho para o arquivo .zip.

    Raises:
        DecompressorError: se algum nome interno for considerado suspeito.
    """
    with zipfile.ZipFile(file_path, "r") as zf:
        for name in zf.namelist():
            if "\x00" in name:
                raise DecompressorError(
                    f"Nome de arquivo inválido (null byte): '{name}'. Extração bloqueada."
                )
            parts = name.replace("\\", "/").split("/")
            if ".." in parts:
                raise DecompressorError(
                    f"Path traversal detectado: '{name}'. Extração bloqueada."
                )


def validate_zip(file_path: Path) -> None:
    """
    Ponto central de validação — aciona todas as checagens em sequência:
    extensão → tamanho → integridade do ZIP → zip-bomb → nomes internos.

    Args:
        file_path: Caminho completo para o arquivo .zip.

    Raises:
        DecompressorError: na primeira falha de validação encontrada.
    """
    validate_extension(file_path)
    validate_size(file_path)

    if not zipfile.is_zipfile(file_path):
        raise DecompressorError("O arquivo ZIP está corrompido ou não é um ZIP válido.")

    validate_zip_bomb(file_path)
    validate_filenames(file_path)


# ──────────────────────────────────────────────────────────────────────────────
# Funções de Extração e Limpeza
# ──────────────────────────────────────────────────────────────────────────────

def extract_zip(file_path: Path, session_id: str | None = None) -> Path:
    """
    Extrai o ZIP em diretório isolado em TEMP_DIR após todas as validações.

    Args:
        file_path: Caminho para o arquivo .zip.
        session_id: ID único da sessão (gerado automaticamente se None).

    Returns:
        Path do diretório onde os arquivos foram extraídos.

    Raises:
        DecompressorError: em qualquer falha de validação ou extração.
    """
    validate_zip(file_path)

    sid = session_id or str(uuid.uuid4())
    dest_dir = get_upload_dir(sid)

    with zipfile.ZipFile(file_path, "r") as zf:
        resolved_dest = dest_dir.resolve()
        for member in zf.namelist():
            target = (dest_dir / member).resolve()
            if not str(target).startswith(str(resolved_dest)):
                raise DecompressorError(
                    f"Caminho suspeito detectado no ZIP: '{member}'. Extração abortada."
                )
        zf.extractall(dest_dir)
        logger.info("ZIP extraído em: %s (%d arquivos)", dest_dir, len(zf.namelist()))

    return dest_dir


def cleanup_session(session_id: str) -> None:
    """
    Remove o diretório temporário de uma sessão após o uso.

    Args:
        session_id: Identificador da sessão a ser limpa.
    """
    session_dir = TEMP_DIR / session_id
    if session_dir.exists():
        shutil.rmtree(session_dir)
        logger.info("Sessão limpa: %s", session_id)
