"""
src/orchestrator.py  –  Dev 4 | Sprint 2 | Auditoria Dev 4 Sprint 4
Pipeline procedural central que orquestra todas as etapas da análise:
  1. Parsing de manifesto (pyproject.toml / requirements.txt)
  2. Extração de imports via AST
  3. Detecção de Zumbis, Fantasmas e Dependências Desatualizadas
  4. Enriquecimento com metadados de tamanho e idade (age_size_analyzer)
  5. Preenchimento do modelo padronizado de resultado
  6. Cálculo de estatísticas de sumarização

Paradigma: Procedimental — apenas funções, sem classes de domínio.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from core.results_model import get_empty_result_model
from src.analyzers.ghost_analyzer import find_ghost_dependencies
from src.analyzers.outdated_analyzer import check_outdated_dependencies
from src.analyzers.zombie_analyzer import find_zombie_dependencies
from src.code_parser import get_all_imports
from src.parsers.pyproject_parser import parse_pyproject
from src.parsers.requirements_parser import parse_requirements

logger = logging.getLogger(__name__)


def _run_parsers(project_path: Path) -> list[str]:
    """
    Executa os parsers de manifesto (pyproject.toml e requirements.txt)
    e retorna a lista consolidada de dependências declaradas.

    Args:
        project_path: Raiz do projeto extraído a ser analisado.

    Returns:
        Lista de strings de dependência no formato bruto
        (ex: ["requests>=2.28.0", "numpy>=1.24.0"]).
        Em caso de falha em qualquer parser, o erro é logado e ignorado.
    """
    deps: dict[str, str] = {}
    pyproject = project_path / "pyproject.toml"
    req = project_path / "requirements.txt"

    if pyproject.exists():
        try:
            p_deps = parse_pyproject(pyproject)
            for k, v in p_deps.items():
                deps[k] = f"{k}{v}"
        except Exception:  # noqa: BLE001
            logger.warning("Falha ao parsear pyproject.toml em '%s'.", project_path, exc_info=True)

    if req.exists():
        try:
            r_deps = parse_requirements(req)
            for k, v in r_deps.items():
                deps[k] = f"{k}{v}"
        except Exception:  # noqa: BLE001
            logger.warning("Falha ao parsear requirements.txt em '%s'.", project_path, exc_info=True)

    logger.info("_run_parsers: %d dependência(s) declarada(s) encontrada(s).", len(deps))
    return list(deps.values())


def _run_ast(project_path: Path) -> set[str]:
    """
    Executa a extração de imports via AST em todos os arquivos .py do projeto.

    Args:
        project_path: Raiz do projeto a ser varrido.

    Returns:
        Conjunto de nomes de módulo raiz encontrados (ex: {'requests', 'flask'}).
        Retorna conjunto vazio em caso de falha inesperada.
    """
    try:
        return get_all_imports(project_path)
    except Exception:  # noqa: BLE001
        logger.warning("Falha na extração AST em '%s'.", project_path, exc_info=True)
        return set()


def _analyze_zombies(declared: list[str], imported: set[str]) -> list[str]:
    """
    Delega a detecção de Zumbis ao zombie_analyzer.

    Args:
        declared: Lista de dependências declaradas no manifesto.
        imported: Conjunto de módulos importados via AST.

    Returns:
        Lista de nomes de pacote classificados como Zumbis.
    """
    return find_zombie_dependencies(declared, imported)


def _analyze_ghosts(declared: list[str], imported: set[str]) -> list[str]:
    """
    Delega a detecção de Fantasmas ao ghost_analyzer.

    Args:
        declared: Lista de dependências declaradas no manifesto.
        imported: Conjunto de módulos importados via AST.

    Returns:
        Lista de nomes de módulo classificados como Fantasmas.
    """
    return find_ghost_dependencies(declared, imported)


def _analyze_outdated(declared: list[str]) -> dict[str, dict[str, Any]]:
    """
    Delega a verificação de defasagem ao outdated_analyzer.

    Args:
        declared: Lista de dependências declaradas no manifesto.

    Returns:
        Dicionário de pacotes desatualizados com metadados de versão.
    """
    return check_outdated_dependencies(declared)


def _enrich_dependencies(declared: list[str]) -> dict[str, dict]:
    """
    Busca metadados enriquecidos (size_bytes, age_days) para cada dependência
    declarada usando o age_size_analyzer.

    Args:
        declared: Lista de deps brutas (ex: ["requests>=2.28.0"]).

    Returns:
        dict[str, {"size_bytes": int, "age_days": int | None}]
        Retorna dicionário vazio se o módulo ainda não estiver disponível
        ou se ocorrer qualquer falha durante a consulta.
    """
    try:
        from src.analyzers.age_size_analyzer import compute_enriched_metadata  # noqa: PLC0415
        return compute_enriched_metadata(declared)
    except Exception:  # noqa: BLE001
        logger.warning(
            "_enrich_dependencies: compute_enriched_metadata indisponível ou falhou.",
            exc_info=True,
        )
        return {}


def _fill_result_model(
    result: dict[str, Any],
    declared_deps: list[str],
    imported_modules: set[str],
    zombies: list[str],
    ghosts: list[str],
    outdated: dict[str, dict[str, Any]],
    enriched_declared: dict[str, dict] | None = None,
) -> None:
    """
    Preenche o modelo padronizado de resultado com os dados das análises.

    Modifica ``result`` in-place para evitar cópias desnecessárias do dicionário.

    Args:
        result: Dicionário de resultado (estrutura de ``get_empty_result_model``).
        declared_deps: Lista de dependências declaradas.
        imported_modules: Conjunto de módulos importados via AST.
        zombies: Lista de dependências classificadas como Zumbis.
        ghosts: Lista de módulos classificados como Fantasmas.
        outdated: Dicionário de pacotes desatualizados.
        enriched_declared: Metadados enriquecidos por pacote
            (size_bytes, age_days). Opcional; padrão: None → persiste como {}.
    """
    if enriched_declared is None:
        enriched_declared = {}

    result["dependencies"]["declared"] = declared_deps
    result["dependencies"]["imported"] = sorted(imported_modules)
    result["dependencies"]["zombies"] = zombies
    result["dependencies"]["ghosts"] = ghosts
    result["dependencies"]["outdated"] = outdated
    result["enriched_declared"] = enriched_declared

    stats = result["statistics"]
    stats["total_declared"] = len(declared_deps)
    stats["total_imported"] = len(imported_modules)
    stats["total_zombies"] = len(zombies)
    stats["total_ghosts"] = len(ghosts)
    stats["total_outdated"] = len(outdated)

    # ── Estatísticas de enriquecimento ───────────────────────────────────────
    size_values = [
        meta["size_bytes"]
        for meta in enriched_declared.values()
        if isinstance(meta.get("size_bytes"), int) and meta["size_bytes"] != -1
    ]
    age_values = [
        meta["age_days"]
        for meta in enriched_declared.values()
        if meta.get("age_days") is not None
    ]

    stats["total_size_bytes"] = sum(size_values)
    stats["avg_age_days"] = (
        round(sum(age_values) / len(age_values), 2) if age_values else None
    )


def run_analysis(recieved_project_path: str) -> dict[str, Any]:
    """
    Ponto de entrada do pipeline de análise de dependências.

    Executa proceduralmente todas as etapas de extração e análise:
    parsing → AST → analisadores → preenchimento do modelo → estatísticas.

    Args:
        recieved_project_path: Caminho (string) para a raiz do projeto extraído.
                               O nome do argumento preserva a grafia original
                               dos sprints anteriores para retrocompatibilidade.

    Returns:
        Dicionário de resultado padronizado conforme ``core/results_model.py``,
        contendo ``project_info``, ``dependencies`` e ``statistics``.
    """
    result: dict[str, Any] = get_empty_result_model()
    project_path = Path(recieved_project_path)

    result["project_info"]["analyzed_at"] = datetime.now().isoformat()
    logger.info("Iniciando análise em: '%s'", project_path)

    declared_deps = _run_parsers(project_path)
    imported_modules = _run_ast(project_path)
    zombies = _analyze_zombies(declared_deps, imported_modules)
    ghosts = _analyze_ghosts(declared_deps, imported_modules)
    outdated = _analyze_outdated(declared_deps)
    enriched_declared = _enrich_dependencies(declared_deps)

    _fill_result_model(
        result,
        declared_deps,
        imported_modules,
        zombies,
        ghosts,
        outdated,
        enriched_declared,
    )

    logger.info(
        "Análise concluída: %d declaradas | %d zumbis | %d fantasmas | %d desatualizadas "
        "| tamanho total: %d bytes | idade média: %s dias.",
        len(declared_deps),
        len(zombies),
        len(ghosts),
        len(outdated),
        result["statistics"].get("total_size_bytes", 0),
        result["statistics"].get("avg_age_days"),
    )
    return result
