"""
src/clients/pypi_client.py  –  Dev 3 | Sprint 2 | Auditoria Dev 4 Sprint 4 | Expansão Dev 3 Sprint 4
Cliente HTTP minimalista para o índice PyPI.
Usa apenas bibliotecas da Standard Library (urllib, json, functools)
e lru_cache para evitar chamadas de rede duplicadas.

Paradigma: Procedimental — apenas funções, sem classes de domínio.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)

# Endpoint base da API JSON do PyPI
_PYPI_BASE_URL: str = "https://pypi.org/pypi"
# Timeout padrão em segundos para chamadas ao PyPI
_REQUEST_TIMEOUT: int = 10
# Cabeçalho User-Agent para identificar o cliente ao PyPI
_USER_AGENT: str = "DepCheck/0.4 (github.com/projeto-paralelo-rp3)"


@lru_cache(maxsize=128)
def get_pypi_package_info(package_name: str) -> dict[str, Any] | None:
    """
    Consulta a API JSON do PyPI e retorna os metadados do pacote solicitado.

    Utiliza ``functools.lru_cache`` para armazenar em memória os resultados
    de consultas anteriores, evitando chamadas de rede duplicadas na mesma
    sessão de execução.

    Args:
        package_name: Nome do pacote a ser consultado (ex: "requests", "numpy").
                      Deve estar em lowercase para compatibilidade com o índice.

    Returns:
        Dicionário com os campos da API PyPI (``info``, ``releases``, ``urls``),
        ou ``None`` se o pacote não for encontrado ou houver falha na conexão.
    """
    url = f"{_PYPI_BASE_URL}/{package_name}/json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as response:
            if response.status == 200:
                raw: bytes = response.read()
                data: dict[str, Any] = json.loads(raw.decode("utf-8"))
                logger.debug("PyPI: dados recebidos para '%s'.", package_name)
                return data
    except urllib.error.HTTPError as exc:
        logger.debug("PyPI HTTP %d para '%s': %s", exc.code, package_name, exc.reason)
    except urllib.error.URLError as exc:
        logger.warning("PyPI URLError para '%s': %s", package_name, exc.reason)
    except Exception:  # noqa: BLE001
        logger.warning("Erro inesperado ao consultar PyPI para '%s'.", package_name, exc_info=True)

    return None


def fetch_latest_version(package_name: str) -> dict[str, Any]:
    """
    Retorna os metadados resumidos de versão para uso nos analisadores.

    Wrapper procedural sobre ``get_pypi_package_info`` que extrai apenas
    os campos relevantes para o outdated_analyzer. Retorna dicionário vazio
    se os dados não estiverem disponíveis.

    Args:
        package_name: Nome do pacote a ser consultado.

    Returns:
        Dicionário com as chaves ``latest_version`` e ``upload_time``,
        ou dicionário vazio se os dados forem inacessíveis.
    """
    info = get_pypi_package_info(package_name)
    if not info or "info" not in info:
        return {}

    latest_version: str = info["info"].get("version", "")
    releases: dict[str, list[dict[str, Any]]] = info.get("releases", {})
    files = releases.get(latest_version, [])
    upload_time: str = files[0].get("upload_time", "") if files else ""

    return {"latest_version": latest_version, "upload_time": upload_time}


@lru_cache(maxsize=128)
def fetch_package_size(package_name: str, version: str | None = None) -> int:
    """Retorna o tamanho em bytes do pacote no PyPI.

    Usa a versão especificada; se None, usa a versão latest.
    Prefere wheel (.whl) sobre sdist (.tar.gz). Se múltiplos arquivos,
    retorna o tamanho do primeiro wheel encontrado ou do primeiro arquivo.

    Args:
        package_name: Nome do pacote no PyPI (lowercase).
        version: Versão específica a consultar. Se None, usa a latest.

    Returns:
        Tamanho em bytes (int >= 0) ou -1 se indisponível.
    """
    info = get_pypi_package_info(package_name)
    if not info:
        return -1

    target_version: str | None = version
    if target_version is None:
        target_version = info.get("info", {}).get("version")
    if not target_version:
        return -1

    releases = info.get("releases", {})
    files = releases.get(target_version, [])
    if not files:
        return -1

    # Prefer wheel over sdist
    for file_info in files:
        filename = file_info.get("filename", "")
        if filename.endswith(".whl"):
            size = file_info.get("size")
            if size is not None:
                logger.debug("PyPI size (whl) para '%s' v%s: %d bytes", package_name, target_version, int(size))
                return int(size)

    # Fallback to first file
    size = files[0].get("size")
    if size is not None:
        logger.debug("PyPI size (sdist) para '%s' v%s: %d bytes", package_name, target_version, int(size))
        return int(size)

    return -1


@lru_cache(maxsize=128)
def fetch_release_date(package_name: str, version: str | None = None) -> str | None:
    """Retorna a data de upload de uma versão específica do pacote no PyPI.

    A data é retornada no formato ISO 8601 (ex: "2023-04-15T10:23:45").
    Usa a versão latest se version=None.
    Usa o campo "upload_time" de releases[version][0].

    Args:
        package_name: Nome do pacote no PyPI (lowercase).
        version: Versão específica a consultar. Se None, usa a latest.

    Returns:
        String com a data no formato ISO 8601 ou None se indisponível.
    """
    info = get_pypi_package_info(package_name)
    if not info:
        return None

    target_version: str | None = version
    if target_version is None:
        target_version = info.get("info", {}).get("version")
    if not target_version:
        return None

    releases = info.get("releases", {})
    files = releases.get(target_version, [])
    if not files:
        return None

    upload_time = files[0].get("upload_time")
    if not upload_time:
        return None

    logger.debug("PyPI release_date para '%s' v%s: %s", package_name, target_version, upload_time)
    return str(upload_time)
