from __future__ import annotations

from typing import Any


def get_empty_result_model() -> dict[str, Any]:
    """Estrutura base padronizada do resultado de uma análise completa do projeto.

    Esse é o dicionário que será consumido pela GUI e pelos Exportadores (JSON/CSV).

    Returns:
        dict[str, Any]: Modelo de resultado vazio com todos os campos inicializados.
    """
    return {
        "project_info": {
            "name": "unknown",
            "analyzed_at": "",
        },
        "dependencies": {
            "declared": [],      # Dependências achadas nos arquivos de config
            "imported": [],      # Módulos importados rastreados pelo AST
            "zombies": [],       # Declarado > Não Importado
            "ghosts": [],        # Importado > Não Declarado
            "outdated": {},      # Map de pacote -> {latest_version: str, days_outdated: int}
        },
        "statistics": {
            "total_declared": 0,
            "total_imported": 0,
            "total_zombies": 0,
            "total_ghosts": 0,
            "total_outdated": 0,
        },
        # Metadados enriquecidos de cada dependência declarada, buscados no PyPI.
        # Formato: {"requests": {"size_bytes": 102400, "age_days": 180}, ...}
        # "size_bytes" pode ser SIZE_UNKNOWN (-1) quando indisponível no PyPI.
        # "age_days" pode ser None quando a data de publicação não está disponível.
        "enriched_declared": {},
    }
