"""
gui/report.py  –  DepCheck | Sprint 4
Módulo unificado de renderização: tabelas, KPIs, gráficos e exportações.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any
import streamlit as st
import pandas as pd
import plotly.graph_objects as go


from core.constants import SIZE_UNKNOWN

# ══════════════════════════════════════════════════════════════════════════════
# DEV 1 — Zombie Helpers + Render
# ══════════════════════════════════════════════════════════════════════════════


def _format_size(size_bytes: int | None) -> str:
    """Formata um tamanho em bytes como string legível para exibição.

    Retorna "N/D" quando o valor é SIZE_UNKNOWN (-1) ou None, "X KB" para valores
    menores que 1 MB, e "X MB" para valores maiores ou iguais a 1 MB.

    Args:
        size_bytes: Tamanho em bytes. Usar SIZE_UNKNOWN (-1) ou None quando indisponível.

    Returns:
        String formatada, ex: ``"N/D"``, ``"100 KB"``, ``"2 MB"``.
    """
    if size_bytes is None or size_bytes == SIZE_UNKNOWN:
        return "N/D"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes // 1024} KB"
    return f"{size_bytes // (1024 * 1024)} MB"


def get_zombie_rows(result: dict[str, Any]) -> list[dict[str, str]]:
    """Extrai e retorna as dependências zumbis como lista de dicionários para exibição.

    Quando ``result`` contém a chave ``"enriched_declared"``, cada linha é enriquecida
    com as colunas ``"tamanho"`` e ``"idade_dias"`` provenientes dos metadados PyPI.
    Caso contrário, as colunas não são incluídas (retrocompatibilidade total).

    Args:
        result: Dicionário de resultado completo conforme ``get_empty_result_model()``.

    Returns:
        Lista de dicionários prontos para renderização em tabela Streamlit.
        Sem enriquecimento: ``[{"pacote": "...", "status": "Zumbi"}, ...]``
        Com enriquecimento: adiciona ``"tamanho"`` e ``"idade_dias"`` a cada item.
    """
    deps = result.get("dependencies", {})
    zombies = deps.get("zombies", [])
    enriched: dict[str, Any] = result.get("enriched_declared", {})

    rows: list[dict[str, str]] = []
    for z in zombies:
        # Normaliza o nome para buscar no enriched_declared (chave em minúsculas)
        from src.analyzers.zombie_analyzer import extract_package_name
        key = extract_package_name(z)
        row: dict[str, str] = {"pacote": z, "status": "Zumbi"}
        if enriched:
            meta = enriched.get(key, {})
            size_bytes: int = meta.get("size_bytes", SIZE_UNKNOWN)
            age_days: int | None = meta.get("age_days", None)
            row["tamanho"] = _format_size(size_bytes)
            row["idade_dias"] = str(age_days) if age_days is not None else "N/D"
        rows.append(row)
    return rows


def build_zombie_csv_bytes(result: dict[str, Any]) -> bytes:
    """Serializa zumbis para bytes CSV com BOM UTF-8 (compatível com Excel).

    Quando ``result`` contém ``"enriched_declared"``, o CSV exportado inclui
    as colunas adicionais ``"tamanho"`` e ``"idade_dias"``.

    Args:
        result: Dicionário de resultado completo conforme ``get_empty_result_model()``.

    Returns:
        Bytes do CSV com BOM UTF-8 (``utf-8-sig``), delimitado por ponto-e-vírgula.
    """
    rows = get_zombie_rows(result)
    has_enriched = bool(result.get("enriched_declared"))
    fieldnames = ["pacote", "status"]
    if has_enriched:
        fieldnames += ["tamanho", "idade_dias"]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=";")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8-sig")


def render_csv_download(result: dict[str, Any]) -> None:
    """Renderiza o botão de download CSV dos dados de zumbis.

    Args:
        result: Dicionário de resultado completo conforme ``get_empty_result_model()``.
    """
    csv_bytes = build_zombie_csv_bytes(result)
    st.download_button(
        label="⬇️ Exportar Zumbis (.csv)",
        data=csv_bytes,
        file_name="zombies_report.csv",
        mime="text/csv",
        use_container_width=True,
        key="download_zombie_csv",
    )


def render_zombie_table(result: dict[str, Any]) -> None:
    """Renderiza a seção de Tabela de Dependências Zumbis.

    Exibe colunas básicas ``Pacote`` e ``Status`` sempre. Quando
    ``result["enriched_declared"]`` estiver preenchido, exibe também as
    colunas ``Tamanho`` e ``Idade (dias)`` com os metadados do PyPI.

    Args:
        result: Dicionário de resultado completo conforme ``get_empty_result_model()``.
    """
    rows = get_zombie_rows(result)
    count = len(rows)
    has_enriched = bool(result.get("enriched_declared"))

    st.markdown("### 🧟 Dependências Zumbis")
    st.caption(
        "Pacotes declarados nos arquivos de manifesto que **não possuem nenhum import** "
        "correspondente no código-fonte."
    )

    if count == 0:
        st.success("✅ Nenhuma dependência zumbi encontrada! Projeto limpo.")
        return

    st.error(f"⚠️ **{count}** dependência(s) zumbi detectada(s).")

    df = pd.DataFrame(rows)

    column_config: dict[str, Any] = {
        "pacote": st.column_config.TextColumn("📦 Pacote", width="large"),
        "status": st.column_config.TextColumn("🔖 Status", width="small"),
    }

    if has_enriched:
        column_config["tamanho"] = st.column_config.TextColumn("📦 Tamanho", width="small")
        column_config["idade_dias"] = st.column_config.TextColumn("📅 Idade (dias)", width="small")

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
    )
    render_csv_download(result)


# ══════════════════════════════════════════════════════════════════════════════
# DEV 2 — Ghost Helpers + Render
# ══════════════════════════════════════════════════════════════════════════════


def _format_age(age_days: int | float | None) -> str:
    """Formata a idade em dias para string legível.

    Args:
        age_days: Número de dias. None indica valor indisponível.

    Returns:
        String com o valor numérico ou "N/D" quando indisponível.
    """
    if age_days is None:
        return "N/D"
    return str(int(age_days))


def get_ghost_rows(result: dict[str, Any]) -> list[dict[str, str]]:
    """Extrai e retorna as dependências fantasmas como lista de dicionários
    prontos para exibição em tabela Streamlit.

    Quando ``result["enriched_declared"]`` está presente, inclui as colunas
    adicionais "tamanho" e "idade_dias" com dados de cada pacote.

    Args:
        result: Dicionário de resultado da análise retornado pelo orquestrador.

    Returns:
        Lista de dicionários com os campos do pacote fantasma, incluindo
        "tamanho" e "idade_dias" quando dados enriquecidos estiverem disponíveis.
    """
    deps = result.get("dependencies", {})
    ghosts = deps.get("ghosts", [])
    enriched: dict[str, Any] = result.get("enriched_declared", {})

    rows: list[dict[str, str]] = []
    for g in ghosts:
        row: dict[str, str] = {"pacote": g, "status": "Fantasma"}
        if enriched:
            pkg_data = enriched.get(g, {})
            row["tamanho"] = _format_size(pkg_data.get("size_bytes"))
            row["idade_dias"] = _format_age(pkg_data.get("age_days"))
        rows.append(row)
    return rows


def build_json_bytes(result: dict[str, Any]) -> bytes:
    """Serializa o dicionário de resultado completo para bytes JSON.

    Inclui o campo ``enriched_declared`` quando presente no dicionário de
    resultado, permitindo auditoria completa dos metadados enriquecidos.

    Args:
        result: Dicionário de resultado da análise retornado pelo orquestrador.

    Returns:
        Bytes UTF-8 do JSON formatado com indentação de 4 espaços.
    """
    return json.dumps(result, ensure_ascii=False, indent=4).encode("utf-8")


def render_json_download(result: dict[str, Any]) -> None:
    """Renderiza o botão de download JSON do relatório completo."""

    json_bytes = build_json_bytes(result)
    st.download_button(
        label="⬇️ Exportar Relatório Completo (.json)",
        data=json_bytes,
        file_name="depcheck_report.json",
        mime="application/json",
        use_container_width=True,
        key="download_full_json",
    )


def render_ghost_table(result: dict[str, Any]) -> None:
    """Renderiza a seção de Tabela de Dependências Fantasmas.

    Exibe colunas adicionais "Tamanho" e "Idade (dias)" quando
    ``result["enriched_declared"]`` estiver disponível no resultado.

    Args:
        result: Dicionário de resultado da análise retornado pelo orquestrador.
    """
    rows = get_ghost_rows(result)
    count = len(rows)
    has_enriched = bool(result.get("enriched_declared"))

    st.markdown("### 👻 Dependências Fantasmas")
    st.caption(
        "Módulos importados ativamente no código via AST que **não estão declarados** "
        "nos arquivos de manifesto do projeto."
    )

    if count == 0:
        st.success("✅ Nenhuma dependência fantasma encontrada! Manifesto completo.")
        render_json_download(result)
        return

    st.warning(f"⚠️ **{count}** dependência(s) fantasma detectada(s).")

    df = pd.DataFrame(rows)

    if has_enriched:
        df.columns = ["Pacote", "Status", "Tamanho", "Idade (dias)"]
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Pacote": st.column_config.TextColumn("📦 Pacote", width="large"),
                "Status": st.column_config.TextColumn("🔖 Status", width="small"),
                "Tamanho": st.column_config.TextColumn("💾 Tamanho", width="small"),
                "Idade (dias)": st.column_config.TextColumn("📅 Idade (dias)", width="small"),
            },
        )
    else:
        df.columns = ["Pacote", "Status"]
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Pacote": st.column_config.TextColumn("📦 Pacote", width="large"),
                "Status": st.column_config.TextColumn("🔖 Status", width="small"),
            },
        )

    render_json_download(result)


# ══════════════════════════════════════════════════════════════════════════════
# DEV 3 — KPI + Outdated Helpers + Renders
# ══════════════════════════════════════════════════════════════════════════════


def get_kpi_values(result: dict[str, Any]) -> dict[str, int]:
    """Extrai e consolida métricas de KPI do resultado da análise.

    Args:
        result: Modelo de resultado contendo estatísticas de dependências.

    Returns:
        Dicionário com valores de KPI como total declarado, importado, zumbis, fantasmas, desatualizados e saudáveis.
    """
    stats = result.get("statistics", {})
    total_declared = stats.get("total_declared", 0)
    total_zombies = stats.get("total_zombies", 0)
    total_ghosts = stats.get("total_ghosts", 0)
    total_outdated = stats.get("total_outdated", 0)
    total_healthy = max(0, total_declared - total_zombies - total_ghosts - total_outdated)
    return {
        "total_declared": total_declared,
        "total_imported": stats.get("total_imported", 0),
        "total_zombies": total_zombies,
        "total_ghosts": total_ghosts,
        "total_outdated": total_outdated,
        "total_healthy": total_healthy,
    }


def get_outdated_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Formata as dependências desatualizadas para exibição em tabela.

    Args:
        result: Modelo de resultado contendo dependências desatualizadas.

    Returns:
        Lista de dicionários com nome do pacote, versão mais recente e dias de defasagem,
        ordenada da maior para a menor defasagem.
    """
    outdated = result.get("dependencies", {}).get("outdated", {})
    rows = [
        {
            "pacote": name,
            "versao_mais_recente": info.get("latest_version", "—"),
            "dias_defasagem": info.get("days_outdated", 0),
        }
        for name, info in outdated.items()
    ]
    return sorted(rows, key=lambda r: r["dias_defasagem"], reverse=True)


def _format_size_bytes(total_bytes: int) -> str:
    """
    Formata um valor em bytes para exibição legível (KB ou MB).

    Args:
        total_bytes: Valor total em bytes.

    Returns:
        String formatada (ex: "12.4 MB", "320.0 KB").
    """
    if total_bytes <= 0:
        return "N/D"
    if total_bytes >= 1_048_576:
        return f"{total_bytes / 1_048_576:.1f} MB"
    return f"{total_bytes / 1_024:.1f} KB"


def _format_avg_age(avg_age_days: float | None) -> str:
    """
    Formata a idade média em dias para exibição legível.

    Args:
        avg_age_days: Idade média em dias, ou None se indisponível.

    Returns:
        String formatada (ex: "320 dias") ou "N/D".
    """
    if avg_age_days is None:
        return "N/D"
    return f"{int(avg_age_days)} dias"


def render_kpi_cards(result: dict[str, Any]) -> None:
    """Renderiza os 8 cartões de KPI no topo do painel (2 linhas × 4 colunas).

    Linha 1: Declaradas | Importadas (AST) | Saudáveis | Tamanho Total
    Linha 2: Zumbis | Fantasmas | Desatualizadas | Idade Média
    """

    kpis = get_kpi_values(result)
    stats = result.get("statistics", {})

    total_size_bytes: int = stats.get("total_size_bytes", 0)
    avg_age_days: float | None = stats.get("avg_age_days")

    st.markdown("### 📊 Resumo da Análise")
    col1, col2, col3, col4 = st.columns(4)
    col5, col6, col7, col8 = st.columns(4)

    with col1:
        st.metric("📦 Declaradas", kpis["total_declared"])
    with col2:
        st.metric("🔍 Importadas (AST)", kpis["total_imported"])
    with col3:
        st.metric(
            "✅ Saudáveis",
            kpis["total_healthy"],
            delta=f"+{kpis['total_healthy']}" if kpis["total_healthy"] > 0 else "0",
            delta_color="normal",
        )
    with col4:
        st.metric("📦 Tamanho Total", _format_size_bytes(total_size_bytes))
    with col5:
        st.metric(
            "🧟 Zumbis",
            kpis["total_zombies"],
            delta=f"-{kpis['total_zombies']}" if kpis["total_zombies"] > 0 else "0",
            delta_color="inverse",
        )
    with col6:
        st.metric(
            "👻 Fantasmas",
            kpis["total_ghosts"],
            delta=f"-{kpis['total_ghosts']}" if kpis["total_ghosts"] > 0 else "0",
            delta_color="inverse",
        )
    with col7:
        st.metric(
            "⏰ Desatualizadas",
            kpis["total_outdated"],
            delta=f"-{kpis['total_outdated']}" if kpis["total_outdated"] > 0 else "0",
            delta_color="inverse",
        )
    with col8:
        st.metric("📅 Idade Média", _format_avg_age(avg_age_days))
    st.divider()


def render_outdated_table(result: dict[str, Any]) -> None:
    """Renderiza a Tabela de Dependências Desatualizadas com colorização por criticidade."""

    rows = get_outdated_rows(result)
    count = len(rows)

    st.markdown("### ⏰ Dependências Desatualizadas")
    st.caption(
        "Pacotes com versões anteriores à release mais recente no **PyPI**. "
        "Ordenados por criticidade (mais antigos primeiro)."
    )

    if count == 0:
        st.success("✅ Todas as dependências estão na versão mais recente!")
        return

    st.info(f"ℹ️ **{count}** dependência(s) desatualizada(s) encontrada(s).")

    df = pd.DataFrame(rows)
    df.columns = ["Pacote", "Versão Mais Recente", "Dias Defasagem"]

    def highlight_critical(val: int) -> str:
        if val > 365:
            return "background-color: #fee2e2; color: #991b1b"
        if val > 180:
            return "background-color: #fef3c7; color: #92400e"
        return ""

    styler = df.style
    map_fn = getattr(styler, "map", None)
    if callable(map_fn):
        styled = map_fn(highlight_critical, subset=["Dias Defasagem"])
    else:
        applymap_fn = getattr(styler, "applymap")
        styled = applymap_fn(highlight_critical, subset=["Dias Defasagem"])
    st.dataframe(styled, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# DEV 4 — Pie Chart (Plotly) + Render + All Deps Table (Sprint 4)
# ══════════════════════════════════════════════════════════════════════════════

_PIE_COLORS = ["#22c55e", "#ef4444", "#a855f7", "#f59e0b"]


def get_pie_chart_data(result: dict[str, Any]) -> dict[str, Any]:
    """Computa proporções para o gráfico de pizza:
    Saudáveis | Zumbis | Fantasmas | Desatualizadas
    """
    stats = result.get("statistics", {})
    total_declared = stats.get("total_declared", 0)
    total_zombies = stats.get("total_zombies", 0)
    total_ghosts = stats.get("total_ghosts", 0)
    total_outdated = stats.get("total_outdated", 0)
    total_healthy = max(0, total_declared - total_zombies - total_ghosts - total_outdated)
    return {
        "labels": ["Saudáveis ✅", "Zumbis 🧟", "Fantasmas 👻", "Desatualizados ⏰"],
        "values": [total_healthy, total_zombies, total_ghosts, total_outdated],
        "colors": _PIE_COLORS,
    }


def render_pie_chart(result: dict[str, Any]) -> None:
    """Renderiza gráfico de pizza interativo (Plotly donut) com responsividade total."""

    data = get_pie_chart_data(result)
    labels = data["labels"]
    values = data["values"]
    colors = data["colors"]

    filtered = [(l, v, c) for l, v, c in zip(labels, values, colors) if v > 0]

    st.markdown("### 🥧 Proporção de Dependências")
    st.caption("Visão macro da saúde do projeto: saudáveis vs problemáticas.")

    if not filtered or sum(v for _, v, _ in filtered) == 0:
        st.info("ℹ️ Nenhum dado disponível para o gráfico.")
        return

    f_labels, f_values, f_colors = zip(*filtered)

    fig = go.Figure(
        data=[
            go.Pie(
                labels=list(f_labels),
                values=list(f_values),
                hole=0.4,
                marker=dict(colors=list(f_colors), line=dict(color="#1e293b", width=2)),
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b><br>Contagem: %{value}<br>Proporção: %{percent}<extra></extra>",
                pull=[0.05 if i > 0 else 0 for i in range(len(f_labels))],
            )
        ]
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0", family="Inter, sans-serif", size=13),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        margin=dict(t=20, b=20, l=20, r=20),
        height=380,
        annotations=[
            dict(
                text=f"<b>{sum(f_values)}</b><br>pacotes",
                x=0.5, y=0.5,
                font_size=16, font_color="#e2e8f0",
                showarrow=False,
            )
        ],
    )
    st.plotly_chart(fig, use_container_width=True)


# ── All Dependencies Table (Dev 4 | Sprint 4) ─────────────────────────────────

_STATUS_ORDER = {"Zumbi": 0, "Fantasma": 1, "Desatualizado": 2, "Saudável": 3}


def _get_dep_status(
    name: str,
    zombies: list[str],
    ghosts: list[str],
    outdated: dict[str, Any],
) -> str:
    """
    Determina o status de uma dependência com base nas listas de análise.

    Args:
        name: Nome normalizado do pacote.
        zombies: Lista de nomes zumbis.
        ghosts: Lista de nomes fantasmas.
        outdated: Dicionário de pacotes desatualizados.

    Returns:
        String de status: "Zumbi", "Fantasma", "Desatualizado" ou "Saudável".
    """
    if name in zombies:
        return "Zumbi"
    if name in ghosts:
        return "Fantasma"
    if name in outdated:
        return "Desatualizado"
    return "Saudável"


def _extract_pkg_name(raw_dep: str) -> str:
    """
    Extrai o nome do pacote de uma string de dependência bruta.

    Args:
        raw_dep: Dependência bruta (ex: "requests>=2.28.0").

    Returns:
        Nome normalizado do pacote em minúsculas (ex: "requests").
    """
    import re  # noqa: PLC0415
    match = re.match(r"^([A-Za-z0-9_.-]+)", raw_dep.strip())
    return match.group(1).lower() if match else raw_dep.strip().lower()


def get_all_deps_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Constrói as linhas da tabela de todas as dependências declaradas,
    combinando status, tamanho e idade dos metadados enriquecidos.

    Args:
        result: Dicionário de resultado padronizado da análise.

    Returns:
        Lista de dicionários com campos: pacote, status, tamanho, idade.
        Ordenada: problemáticas primeiro (Zumbi→Fantasma→Desatualizado→Saudável),
        depois alfabeticamente por nome.
    """
    deps = result.get("dependencies", {})
    declared: list[str] = deps.get("declared", [])
    zombies: list[str] = deps.get("zombies", [])
    ghosts: list[str] = deps.get("ghosts", [])
    outdated: dict[str, Any] = deps.get("outdated", {})
    enriched: dict[str, dict] = result.get("enriched_declared", {})

    rows: list[dict[str, Any]] = []
    for raw_dep in declared:
        pkg_name = _extract_pkg_name(raw_dep)
        status = _get_dep_status(pkg_name, zombies, ghosts, outdated)
        meta = enriched.get(pkg_name, {})

        size_bytes = meta.get("size_bytes", -1)
        if isinstance(size_bytes, int) and size_bytes != -1:
            tamanho = _format_size_bytes(size_bytes)
        else:
            tamanho = "N/D"

        age_days = meta.get("age_days")
        idade = f"{age_days} dias" if age_days is not None else "N/D"

        rows.append(
            {
                "pacote": pkg_name,
                "status": status,
                "tamanho": tamanho,
                "idade": idade,
                "_sort_status": _STATUS_ORDER.get(status, 99),
            }
        )

    rows.sort(key=lambda r: (r["_sort_status"], r["pacote"]))
    for row in rows:
        del row["_sort_status"]

    return rows


def render_all_deps_table(result: dict[str, Any]) -> None:
    """
    Renderiza tabela de TODAS as dependências declaradas com:
    - Pacote (nome)
    - Status (Saudável / Zumbi / Fantasma / Desatualizado)
    - Tamanho (KB ou MB, 'N/D' se -1)
    - Idade (dias, 'N/D' se None)
    Ordenada por status (problemáticas primeiro) depois por nome.

    Args:
        result: Dicionário de resultado padronizado da análise.
    """
    import streamlit as st
    import pandas as pd

    rows = get_all_deps_rows(result)
    count = len(rows)

    st.markdown("### 📋 Todas as Dependências Declaradas")
    st.caption(
        "Visão consolidada de todas as dependências declaradas no manifesto, "
        "com status, tamanho no PyPI e idade do pacote. "
        "Problemáticas aparecem primeiro."
    )

    if count == 0:
        st.info("ℹ️ Nenhuma dependência declarada encontrada no manifesto.")
        return

    df = pd.DataFrame(rows)
    df.columns = ["Pacote", "Status", "Tamanho", "Idade"]

    status_colors = {
        "Zumbi": "🧟",
        "Fantasma": "👻",
        "Desatualizado": "⏰",
        "Saudável": "✅",
    }
    df["Status"] = df["Status"].apply(lambda s: f"{status_colors.get(s, '')} {s}")

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Pacote": st.column_config.TextColumn("📦 Pacote", width="medium"),
            "Status": st.column_config.TextColumn("🔖 Status", width="medium"),
            "Tamanho": st.column_config.TextColumn("💾 Tamanho", width="small"),
            "Idade": st.column_config.TextColumn("📅 Idade", width="small"),
        },
    )
