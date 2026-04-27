from __future__ import annotations

import csv
from typing import Any


def export_to_csv(result_model: dict[str, Any], output_path: str) -> None:
    """Gera CSV completo com colunas de status e dados enriquecidos de pacotes.

    Colunas geradas: Pacote | Status | Tamanho (KB) | Idade (dias) | Outdated (Dias).

    Usa result_model["enriched_declared"] para Tamanho e Idade quando disponível.
    Retrocompatível: funciona mesmo sem a chave enriched_declared.

    Args:
        result_model: Dicionário padronizado retornado pelo orquestrador de análise.
        output_path: Caminho absoluto ou relativo onde o arquivo CSV será gravado.
    """
    deps = result_model.get("dependencies", {})
    enriched: dict[str, dict[str, Any]] = result_model.get("enriched_declared", {})

    declared: set[str] = set(deps.get("declared", []))
    imported: set[str] = set(deps.get("imported", []))
    zombies: set[str] = set(deps.get("zombies", []))
    ghosts: set[str] = set(deps.get("ghosts", []))
    outdated: dict[str, Any] = deps.get("outdated", {})

    all_deps = declared.union(imported).union(zombies).union(ghosts)

    with open(output_path, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(["Pacote", "Status", "Tamanho (KB)", "Idade (dias)", "Outdated (Dias)"])

        for dep in sorted(all_deps):
            
            status_parts: list[str] = []
            if dep in zombies:
                status_parts.append("Zumbi")
            if dep in ghosts:
                status_parts.append("Fantasma")
            if dep in outdated:
                status_parts.append("Desatualizado")
            if not status_parts and dep in declared and dep in imported:
                status_parts.append("Saudável")

            status_str = ", ".join(status_parts)

            pkg_info = enriched.get(dep, {})
            size_bytes: int = pkg_info.get("size_bytes", -1) if pkg_info else -1
            if size_bytes is None or size_bytes < 0:
                size_kb: str | float = "N/D"
            else:
                size_kb = round(size_bytes / 1024, 2)

            age_days: Any = pkg_info.get("age_days") if pkg_info else None
            if age_days is None:
                age_str: str | int = "N/D"
            else:
                age_str = int(age_days)

            days_outdated: str | int = ""
            if dep in outdated:
                days_outdated = outdated[dep].get("days_outdated", "")

            writer.writerow([dep, status_str, size_kb, age_str, days_outdated])
