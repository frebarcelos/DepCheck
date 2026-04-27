"""
gui/home.py  –  Sprint 4 | MERGE FINAL (semana final Sprint 4)
Contribuições integradas:
  Dev 2 → render_exclusion_config() + exclusões configuráveis na GUI
          + schedule_cleanup() + limpeza automática de temp
  Dev 4 → render_all_deps_table() chamada em _render_report()
  Dev 5 → render_size_bar_chart() + layout 3 colunas de gráficos + v0.4.1
"""

from __future__ import annotations

import logging
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

import streamlit as st

# Garante que o root do projeto está no PYTHONPATH ao rodar via streamlit
ROOT = Path(__file__).parent.parent.resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.constants import MAX_ZIP_SIZE_MB  # noqa: E402
from src.decompressor import DecompressorError, cleanup_session, extract_zip  # noqa: E402
from src.filter import filter_extracted  # noqa: E402
from src.orchestrator import run_analysis  # noqa: E402

# Lista padrão de diretórios excluídos exibida na GUI.
# Espelha IGNORED_DIRS de constants.py; definida inline para independência de versão.
DEFAULT_EXCLUDED_DIRS: list[str] = [
    "tests",
    "test",
    "docs",
    "doc",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".git",
    "build",
    "dist",
]

logger = logging.getLogger(__name__)

def run_full_analysis(project_path: str) -> dict:
    """
    Executa a análise completa de dependências em um caminho de projeto.
    Retorna o dicionário de resultados padronizado do orquestrador.
    Função pura — sem efeitos Streamlit — para facilitar testes unitários.
    """
    return run_analysis(project_path)


def schedule_cleanup(session_id: str) -> None:
    """
    Agenda (executa imediatamente) a limpeza do diretório temporário
    de uma sessão. Chamada após a renderização do relatório ou em caso
    de falha para garantir que nenhum arquivo temporário persista.

    Args:
        session_id: Identificador único da sessão a ser descartada.
    """
    try:
        cleanup_session(session_id)
        logger.info("Limpeza de sessão concluída: %s", session_id)
    except Exception:  # noqa: BLE001
        logger.warning("Falha ao limpar sessão: %s", session_id, exc_info=True)

def setup_page() -> None:
    """Configura página e injeta CSS customizado."""
    st.set_page_config(
        page_title="DepCheck — Analisador de Dependências",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        .main { background-color: #0f172a; }
        .stButton>button {
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.6rem 1.5rem;
            font-weight: 600;
            transition: opacity 0.2s;
        }
        .stButton>button:hover { opacity: 0.85; }
        
        /* Força a borda e fundo customizado na section principal do Dropzone */
        section[aria-label="Selecione o arquivo ZIP"] {
            border: 2px dashed #6366f1 !important;
            border-radius: 12px !important;
            padding: 3rem 2rem !important;
            background-color: rgba(99,102,241,0.05) !important;
            position: relative !important;
            margin-bottom: 1.5rem !important;
        }
        section[aria-label="Selecione o arquivo ZIP"] * {
            background-color: transparent !important;
        }
        
        /* Estiliza e centraliza o ícone de nuvem original no meio da caixa */
        section[aria-label="Selecione o arquivo ZIP"] svg {
            display: block !important;
            position: absolute !important;
            left: 50% !important;
            top: 50% !important;
            transform: translate(-50%, -50%) !important;
            width: 72px !important;
            height: 72px !important;
            opacity: 0.4 !important;
            pointer-events: none !important;
        }

        /* Posiciona o botão nativo à direita */
        section[aria-label="Selecione o arquivo ZIP"] button {
            position: absolute !important;
            right: 2rem !important;
            bottom: 2rem !important;
        }

        /* Esconde os spans originais de instrução ("Drag and drop...", "Limit 50MB...") */
        section[aria-label="Selecione o arquivo ZIP"] > div > div > span {
            display: none !important;
        }

        /* Injeta nosso texto customizado no lugar */
        section[aria-label="Selecione o arquivo ZIP"] > div:first-of-type {
            width: 100% !important;
            height: 100% !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: flex-start !important;
            justify-content: center !important;
            gap: 0px !important;
        }
        section[aria-label="Selecione o arquivo ZIP"] > div:first-of-type::before {
            content: "📦 Arraste ou selecione o .zip do seu projeto";
            font-size: 16px;
            font-weight: 600;
            color: #e2e8f0;
            display: block;
        }
        section[aria-label="Selecione o arquivo ZIP"] > div:first-of-type::after {
            content: "Tamanho máximo: 50 MB";
            font-size: 14px;
            color: #888;
            display: block;
        }
        [data-testid="metric-container"] {
            background: rgba(99,102,241,0.08);
            border: 1px solid rgba(99,102,241,0.2);
            border-radius: 10px;
            padding: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    """Renderiza o cabeçalho da aplicação."""
    st.markdown("## 🔍 DepCheck")
    st.markdown(
        "**Análise inteligente de dependências Python.**  \n"
        "Faça upload do `.zip` do seu projeto e descubra zumbis, "
        "fantasmas e pacotes desatualizados."
    )
    st.divider()

def render_exclusion_config() -> list[str]:
    """
    Renderiza widget Streamlit para configurar diretórios a ignorar durante
    a análise. Permite selecionar diretórios pré-definidos e adicionar
    entradas customizadas via campo de texto.

    Returns:
        Lista de nomes de diretórios que o usuário selecionou para excluir.
    """
    with st.expander("⚙️ Configurar diretórios a ignorar", expanded=False):
        selected: list[str] = st.multiselect(
            label="Diretórios excluídos da análise",
            options=DEFAULT_EXCLUDED_DIRS,
            default=DEFAULT_EXCLUDED_DIRS,
            help=(
                "Diretórios selecionados serão removidos antes da análise. "
                "Desmarque para incluir um diretório na varredura."
            ),
            key="excluded_dirs_multiselect",
        )

        st.markdown("**Adicionar diretório customizado:**")
        col_input, col_btn = st.columns([4, 1])
        with col_input:
            custom_dir = st.text_input(
                label="Nome do diretório",
                placeholder="ex: scripts",
                label_visibility="collapsed",
                key="custom_dir_input",
            )
        with col_btn:
            add_clicked = st.button("Adicionar", key="add_custom_dir_btn")

        if "custom_excluded_dirs" not in st.session_state:
            st.session_state["custom_excluded_dirs"] = []

        if add_clicked and custom_dir.strip():
            clean = custom_dir.strip()
            if clean not in st.session_state["custom_excluded_dirs"]:
                st.session_state["custom_excluded_dirs"].append(clean)
                st.success(f"Diretório '{clean}' adicionado.")

        custom_list: list[str] = st.session_state.get("custom_excluded_dirs", [])
        if custom_list:
            st.caption(f"Customizados: {', '.join(custom_list)}")

        return list(set(selected) | set(custom_list))


def render_upload_section() -> tuple[Any, list[str]]:
    """
    Renderiza a configuração de exclusões e a área de upload do ZIP.

    Returns:
        Tupla (arquivo_uploaded, lista_de_dirs_excluidos).
    """
    excluded_dirs = render_exclusion_config()

    uploaded_file = st.file_uploader(
        label="Selecione o arquivo ZIP",
        label_visibility="collapsed",
        key="zip_uploader",
    )
    return uploaded_file, excluded_dirs

def _render_report(result: dict, extract_dir: Path) -> None:
    """
    Renderiza o relatório completo após análise bem-sucedida.

    Ordem de renderização:
    1. KPI cards (8 métricas — Dev 4)
    2. Tabela geral de todas as deps (Dev 4)
    3. Gráficos em 3 colunas: pizza | defasagem | tamanho (Dev 4 + Dev 5)
    4. Tabela zumbis + CSV (Dev 1)
    5. Tabela fantasmas + JSON (Dev 2)
    6. Tabela desatualizadas (Dev 3)
    """
    from gui.charts import render_bar_chart_outdated, render_size_bar_chart
    from gui.report import (
        render_all_deps_table,
        render_ghost_table,
        render_kpi_cards,
        render_outdated_table,
        render_pie_chart,
        render_zombie_table,
    )

    # ── KPI Cards (Dev 4: 8 métricas) ─────────────────────────────────────────
    render_kpi_cards(result)

    # ── Tabela geral de todas as dependências (Dev 4) ──────────────────────────
    render_all_deps_table(result)
    st.divider()

    # ── Gráficos em 3 colunas (Dev 4 pizza | Dev 5 defasagem | Dev 5 tamanho) ──
    col_left, col_mid, col_right = st.columns([1, 1, 1])
    with col_left:
        render_pie_chart(result)
    with col_mid:
        render_bar_chart_outdated(result)
    with col_right:
        render_size_bar_chart(result)

    st.divider()

    # ── Tabelas de análise ─────────────────────────────────────────────────────
    render_zombie_table(result)   # Dev 1 + botão CSV enriquecido
    st.divider()
    render_ghost_table(result)    # Dev 2 + botão JSON
    st.divider()
    render_outdated_table(result) # Dev 3

def process_upload(uploaded_file: Any, excluded_dirs: list[str] | None = None) -> None:
    """
    Processa o arquivo ZIP com spinners contextuais em cada etapa.
    Garante limpeza automática da pasta temporária ao final, com ou sem erros.

    Args:
        uploaded_file: Objeto de arquivo proveniente do st.file_uploader.
        excluded_dirs: Lista de nomes de diretórios a excluir durante a filtragem,
            além dos padrões definidos em IGNORED_DIRS. Quando None, apenas os
            padrões são usados (retrocompatível).
    """
    if uploaded_file is None:
        return

    if not uploaded_file.name.lower().endswith('.zip'):
        st.error("🚨 **Formato inválido!** Por favor, envie apenas arquivos com a extensão **.zip**.")
        return

    file_size_mb = uploaded_file.size / (1024 * 1024)
    st.info(f"📄 **{uploaded_file.name}** — {file_size_mb:.2f} MB recebido.")

    col1, col2 = st.columns([1, 3])
    with col1:
        analyze_btn = st.button("🚀 Analisar", use_container_width=True)

    if not analyze_btn:
        return

    session_id = str(uuid.uuid4())

    # ── Etapa 1: Extração ─────────────────────────────────────────────────────
    with st.spinner("📦 Extraindo arquivos do ZIP com segurança..."):
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp.write(uploaded_file.getbuffer())
            tmp_path = Path(tmp.name)

        try:
            extract_dir = extract_zip(tmp_path, session_id=session_id)
        except DecompressorError as exc:
            st.error(f"❌ Erro na extração: {exc}")
            tmp_path.unlink(missing_ok=True)
            schedule_cleanup(session_id)
            return
        except Exception as exc:  # noqa: BLE001
            st.error(f"❌ Erro inesperado na extração: {exc}")
            logger.exception("Erro inesperado na extração do ZIP.")
            tmp_path.unlink(missing_ok=True)
            schedule_cleanup(session_id)
            return
        finally:
            tmp_path.unlink(missing_ok=True)

    # ── Etapa 2: Filtro (Dev 2: exclusões configuráveis) ──────────────────────
    with st.spinner("🔎 Filtrando arquivos relevantes..."):
        py_files = filter_extracted(extract_dir, extra_excluded_dirs=excluded_dirs)

    st.success(f"✅ Extração concluída! **{len(py_files)} arquivo(s) .py** encontrado(s).")

    with st.expander("📁 Arquivos analisados", expanded=False):
        for f in sorted(py_files):
            st.code(str(f.relative_to(extract_dir)))

    # ── Etapa 3: Análise completa (Orquestrador + enriquecimento PyPI) ────────
    with st.spinner("🧠 Executando análise de dependências e consultando PyPI..."):
        try:
            result = run_full_analysis(str(extract_dir))
        except Exception as exc:  # noqa: BLE001
            st.error(f"❌ Erro durante a análise: {exc}")
            logger.exception("Erro durante run_full_analysis.")
            schedule_cleanup(session_id)
            return

    st.divider()

    # Persiste na sessão
    st.session_state["extract_dir"] = str(extract_dir)
    st.session_state["session_id"] = session_id
    st.session_state["py_files"] = [str(f) for f in py_files]
    st.session_state["analysis_result"] = result

    # Renderiza relatório completo
    _render_report(result, extract_dir)

    # ── Limpeza automática (Dev 2) ─────────────────────────────────────────────
    schedule_cleanup(session_id)


def render_footer() -> None:
    """Renderiza o rodapé da página."""
    st.divider()
    st.markdown(
        "<small>🔬 DepCheck v0.4.1 — Sprint 4 Final | Gerenciador de dependências</small>",
        unsafe_allow_html=True,
    )


def main() -> None:
    """Função principal que orquestra os componentes da Home."""
    setup_page()
    render_header()

    uploaded_file, excluded_dirs = render_upload_section()
    process_upload(uploaded_file, excluded_dirs=excluded_dirs)

    render_footer()


if __name__ == "__main__":
    main()
