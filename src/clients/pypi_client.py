from __future__ import annotations

import json
import urllib.request
from functools import lru_cache


@lru_cache(maxsize=128)
def get_pypi_package_info(package_name: str) -> dict | None:
    """Busca as informações do pacote no servidor PyPI usando urllib.

    Utiliza lru_cache para evitar chamadas de rede duplicadas para o mesmo
    pacote.

    Args:
        package_name: Nome do pacote a consultar no PyPI.

    Returns:
        Dicionário com os dados retornados pela API PyPI ou None em caso de
        falha.
    """
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DepCheck/0.4"})
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                return data
    except Exception as e:
        print(f"Erro ao buscar {package_name} no PyPI: {e}")
        return None
    return None


@lru_cache(maxsize=128)
def fetch_package_size(package_name: str, version: str | None = None) -> int:
    """Retorna o tamanho em bytes do pacote no PyPI.

    Usa a versão especificada; se None, usa a versão latest.
    Prefere wheel (.whl) sobre sdist (.tar.gz). Se múltiplos arquivos,
    retorna o tamanho do primeiro wheel encontrado ou do primeiro arquivo.

    Args:
        package_name: Nome do pacote no PyPI.
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
                return int(size)

    # Fallback to first file
    size = files[0].get("size")
    if size is not None:
        return int(size)

    return -1


@lru_cache(maxsize=128)
def fetch_release_date(package_name: str, version: str | None = None) -> str | None:
    """Retorna a data de upload de uma versão específica do pacote no PyPI.

    A data é retornada no formato ISO 8601 (ex: "2023-04-15T10:23:45").
    Usa a versão latest se version=None.
    Usa o campo "upload_time" de releases[version][0].

    Args:
        package_name: Nome do pacote no PyPI.
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

    return str(upload_time)
