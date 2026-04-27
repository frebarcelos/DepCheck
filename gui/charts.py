"""
gui/charts.py  –  Dev 5 | Sprint 4
Módulo de visualização de gráficos para análise de dependências.

Dev 5 é responsável por:
  - get_bar_chart_data()      → prepara dados brutos para gráfico de barras de defasagem
  - render_bar_chart_outdated() → componente Streamlit com gráfico Plotly de barras (outdated)
  - get_size_chart_data()     → prepara dados top-10 pacotes por tamanho
  - render_size_bar_chart()   → componente Streamlit com gráfico Plotly de tamanho de pacotes
"""
from __future__ import annotations

from typing import Any


# ══════════════════════════════════════════════════════════════════════════════
# GRÁFICO DE DEFASAGEM (Sprint 3)
# ══════════════════════════════════════════════════════════════════════════════


def get_bar_chart_data(result: dict[str, Any]) -> dict[str, list]:
    """Prepara os dados brutos para o gráfico de barras horizontais de defasagem.

    Retorna dicionário com:
      - ``packages``: lista de nomes de pacotes (str)
      - ``days``: lista de dias de defasagem (int)

    Ordenado por dias de defasagem decrescente (mais crítico primeiro).

    Args:
        result: Dicionário padronizado retornado pelo orquestrador de análise.

    Returns:
        Dicionário com chaves ``packages`` e ``days``.
    """
    outdated: dict[str, Any] = result.get("dependencies", {}).get("outdated", {})

    if not outdated:
        return {"packages": [], "days": []}

    items = [
        (name, int(info.get("days_outdated", 0)))
        for name, info in outdated.items()
    ]
    items.sort(key=lambda x: x[1], reverse=True)

    packages = [item[0] for item in items]
    days = [item[1] for item in items]

    return {"packages": packages, "days": days}


def render_bar_chart_outdated(result: dict[str, Any]) -> None:
    """Renderiza o gráfico de barras horizontais de defasagem em dias.

    Exibe colorização gradiente por criticidade (verde → amarelo → vermelho).
    Exibe mensagem informativa se não houver dependências desatualizadas.

    Args:
        result: Dicionário padronizado retornado pelo orquestrador de análise.
    """
    import plotly.graph_objects as go
    import streamlit as st

    data = get_bar_chart_data(result)
    packages = data["packages"]
    days = data["days"]

    st.markdown("### Defasagem por Dependência (dias)")
    st.caption("Quanto mais à direita, mais tempo sem atualização. Valores em dias.")

    if not packages:
        st.info("Nenhuma dependência desatualizada detectada.")
        return

    def _color_for_days(d: int) -> str:
        if d > 365:
            return "#ef4444"  # vermelho
        if d > 180:
            return "#f97316"  # laranja
        if d > 90:
            return "#f59e0b"  # amarelo
        return "#22c55e"      # verde

    bar_colors = [_color_for_days(d) for d in days]

    fig = go.Figure(
        go.Bar(
            x=days,
            y=packages,
            orientation="h",
            marker=dict(
                color=bar_colors,
                line=dict(color="rgba(0,0,0,0.1)", width=1),
            ),
            text=[f"{d} dias" for d in days],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Defasagem: %{x} dias<extra></extra>",
        )
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,0.5)",
        font=dict(color="#e2e8f0", family="Inter, sans-serif", size=12),
        xaxis=dict(
            title="Dias de Defasagem",
            gridcolor="rgba(255,255,255,0.07)",
            zeroline=False,
        ),
        yaxis=dict(
            autorange="reversed",
            tickfont=dict(size=12),
        ),
        margin=dict(t=10, b=40, l=10, r=80),
        height=max(300, len(packages) * 45),
    )

    st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# GRÁFICO DE TAMANHO DE PACOTES (Sprint 4)
# ══════════════════════════════════════════════════════════════════════════════


def get_size_chart_data(result: dict[str, Any]) -> dict[str, list]:
    """Prepara dados para gráfico de barras horizontais de tamanho de pacotes.

    Filtra pacotes com ``size_bytes > 0`` e retorna os top-10 mais pesados
    convertidos para KB, ordenados por tamanho decrescente.

    Args:
        result: Dicionário padronizado retornado pelo orquestrador de análise.
                Espera a chave opcional ``enriched_declared`` com a estrutura:
                ``{nome_pacote: {"size_bytes": int, "age_days": int | None}}``.

    Returns:
        Dicionário com chaves:
          - ``packages``: lista de nomes de pacotes (str)
          - ``sizes_kb``: lista de tamanhos em KB (float)

        Listas vazias se não houver dados de tamanho disponíveis.
    """
    enriched: dict[str, Any] = result.get("enriched_declared", {})

    if not enriched:
        return {"packages": [], "sizes_kb": []}

    items: list[tuple[str, float]] = []
    for name, info in enriched.items():
        if not isinstance(info, dict):
            continue
        size_bytes: int = info.get("size_bytes", -1)
        if size_bytes is not None and size_bytes > 0:
            items.append((name, round(size_bytes / 1024, 2)))

    if not items:
        return {"packages": [], "sizes_kb": []}

    items.sort(key=lambda x: x[1], reverse=True)
    top_items = items[:10]

    packages = [item[0] for item in top_items]
    sizes_kb = [item[1] for item in top_items]

    return {"packages": packages, "sizes_kb": sizes_kb}


def render_size_bar_chart(result: dict[str, Any]) -> None:
    """Renderiza gráfico de barras horizontais dos top-10 pacotes mais pesados.

    Usa colorização gradiente por tamanho (azul claro → azul escuro) e estilo
    dark theme consistente com ``render_bar_chart_outdated()``.
    Exibe mensagem informativa se não houver dados de tamanho disponíveis.

    Args:
        result: Dicionário padronizado retornado pelo orquestrador de análise.
    """
    import plotly.graph_objects as go
    import streamlit as st

    data = get_size_chart_data(result)
    packages = data["packages"]
    sizes_kb = data["sizes_kb"]

    st.markdown("### Tamanho dos Pacotes (Top 10)")
    st.caption("Os 10 pacotes com maior tamanho instalado. Valores em KB.")

    if not packages:
        st.info("Informações de tamanho de pacotes não disponíveis para este projeto.")
        return

    max_size = max(sizes_kb) if sizes_kb else 1.0

    def _color_for_size(kb: float) -> str:
        ratio = kb / max_size if max_size > 0 else 0.0
        if ratio > 0.75:
            return "#6366f1"   # roxo intenso
        if ratio > 0.50:
            return "#818cf8"   # roxo médio
        if ratio > 0.25:
            return "#a5b4fc"   # roxo claro
        return "#c7d2fe"       # lavanda

    bar_colors = [_color_for_size(kb) for kb in sizes_kb]

    fig = go.Figure(
        go.Bar(
            x=sizes_kb,
            y=packages,
            orientation="h",
            marker=dict(
                color=bar_colors,
                line=dict(color="rgba(0,0,0,0.1)", width=1),
            ),
            text=[f"{kb} KB" for kb in sizes_kb],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Tamanho: %{x} KB<extra></extra>",
        )
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,0.5)",
        font=dict(color="#e2e8f0", family="Inter, sans-serif", size=12),
        xaxis=dict(
            title="Tamanho (KB)",
            gridcolor="rgba(255,255,255,0.07)",
            zeroline=False,
        ),
        yaxis=dict(
            autorange="reversed",
            tickfont=dict(size=12),
        ),
        margin=dict(t=10, b=40, l=10, r=80),
        height=max(300, len(packages) * 45),
    )

    st.plotly_chart(fig, use_container_width=True)
