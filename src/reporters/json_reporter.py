from __future__ import annotations

import json
from datetime import datetime
from typing import Any

_EXPORT_VERSION = "0.4.1"


def export_to_json(result_model: dict[str, Any], output_path: str) -> None:
    """Exporta o resultado completo da análise para um arquivo JSON enriquecido.

    O arquivo gerado inclui:
      - ``exported_at``: timestamp ISO 8601 do momento da exportação.
      - ``version``: versão da aplicação que gerou o relatório.
      - Todo o conteúdo de ``result_model``, incluindo ``enriched_declared``
        quando presente.

    Args:
        result_model: Dicionário padronizado retornado pelo orquestrador de análise.
        output_path: Caminho absoluto ou relativo onde o arquivo JSON será gravado.
    """
    payload: dict[str, Any] = {
        "exported_at": datetime.now().isoformat(),
        "version": _EXPORT_VERSION,
        **result_model,
    }

    with open(output_path, mode="w", encoding="utf-8") as file:
        json.dump(payload, file, indent=4, ensure_ascii=False)