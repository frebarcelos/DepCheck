"""
tests/test_zombie_enriched.py  –  Dev 1 | Sprint 4
Testa as funcionalidades enriquecidas de dependências zumbi:

  - extract_package_name(): parsing de strings de dependência PEP 508
  - get_zombie_rows(): com e sem enriched_declared no resultado
  - build_zombie_csv_bytes(): colunas enriquecidas presentes no CSV exportado
  - render_zombie_table(): renderização Streamlit mockada (sem Streamlit real)
"""
from __future__ import annotations

import csv
import io
from unittest.mock import MagicMock, patch

import pytest

# ── Fixtures ───────────────────────────────────────────────────────────────────

MOCK_RESULT_PLAIN = {
    "project_info": {"name": "test-project", "analyzed_at": "2026-04-10T00:00:00"},
    "dependencies": {
        "declared": ["requests>=2.28.0", "flask==2.3.0", "unused-lib>=1.0.0"],
        "imported": ["requests", "flask"],
        "zombies": ["unused-lib>=1.0.0"],
        "ghosts": [],
        "outdated": {},
    },
    "statistics": {
        "total_declared": 3,
        "total_imported": 2,
        "total_zombies": 1,
        "total_ghosts": 0,
        "total_outdated": 0,
    },
    "enriched_declared": {},
}

# Resultado com enriched_declared preenchido (contrato com Dev 3)
MOCK_RESULT_ENRICHED = {
    **MOCK_RESULT_PLAIN,
    "enriched_declared": {
        "requests": {"size_bytes": 102400, "age_days": 180},
        "flask": {"size_bytes": -1, "age_days": None},
        "unused-lib": {"size_bytes": 51200, "age_days": 30},
    },
}

# Resultado sem a chave enriched_declared (retrocompatibilidade)
MOCK_RESULT_NO_ENRICHED_KEY = {
    "project_info": {"name": "legacy-project", "analyzed_at": "2026-04-10T00:00:00"},
    "dependencies": {
        "declared": ["numpy"],
        "imported": [],
        "zombies": ["numpy"],
        "ghosts": [],
        "outdated": {},
    },
    "statistics": {
        "total_declared": 1,
        "total_imported": 0,
        "total_zombies": 1,
        "total_ghosts": 0,
        "total_outdated": 0,
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# Testes de extract_package_name()
# ══════════════════════════════════════════════════════════════════════════════


class TestExtractPackageName:
    """Testes unitários para extract_package_name() em vários formatos PEP 508."""

    def test_sem_versao(self) -> None:
        """Pacote sem especificador de versão retorna o nome em minúsculas."""
        from src.analyzers.zombie_analyzer import extract_package_name

        assert extract_package_name("requests") == "requests"

    def test_maior_ou_igual(self) -> None:
        """Especificador >= é removido corretamente."""
        from src.analyzers.zombie_analyzer import extract_package_name

        assert extract_package_name("Django>=3.2") == "django"

    def test_igual_igual(self) -> None:
        """Especificador == é removido corretamente."""
        from src.analyzers.zombie_analyzer import extract_package_name

        assert extract_package_name("flask==2.3.0") == "flask"

    def test_compativel(self) -> None:
        """Especificador ~= (compatible release) é removido corretamente."""
        from src.analyzers.zombie_analyzer import extract_package_name

        assert extract_package_name("numpy~=1.24") == "numpy"

    def test_diferente(self) -> None:
        """Especificador != é removido corretamente."""
        from src.analyzers.zombie_analyzer import extract_package_name

        assert extract_package_name("pillow!=9.0.0") == "pillow"

    def test_menor_ou_igual(self) -> None:
        """Especificador <= é removido corretamente."""
        from src.analyzers.zombie_analyzer import extract_package_name

        assert extract_package_name("urllib3<=1.26") == "urllib3"

    def test_menor_que(self) -> None:
        """Especificador < é removido corretamente."""
        from src.analyzers.zombie_analyzer import extract_package_name

        assert extract_package_name("boto3<2.0") == "boto3"

    def test_extras_colchetes(self) -> None:
        """Extras entre colchetes são removidos antes do nome do pacote."""
        from src.analyzers.zombie_analyzer import extract_package_name

        assert extract_package_name("requests[security]") == "requests"

    def test_extras_com_versao(self) -> None:
        """Extras e especificador de versão são removidos juntos."""
        from src.analyzers.zombie_analyzer import extract_package_name

        assert extract_package_name("requests[security]==2.28.0") == "requests"

    def test_maiusculas_normalizadas(self) -> None:
        """Nomes em maiúsculas são convertidos para minúsculas."""
        from src.analyzers.zombie_analyzer import extract_package_name

        assert extract_package_name("PyYAML>=6.0") == "pyyaml"

    def test_hifen_preservado(self) -> None:
        """Hífens no nome do pacote são preservados."""
        from src.analyzers.zombie_analyzer import extract_package_name

        assert extract_package_name("my-package>=1.0") == "my-package"

    def test_espacos_extras(self) -> None:
        """Espaços em volta do nome são removidos via strip."""
        from src.analyzers.zombie_analyzer import extract_package_name

        assert extract_package_name("  scipy >= 1.10  ") == "scipy"


# ══════════════════════════════════════════════════════════════════════════════
# Testes de get_zombie_rows()
# ══════════════════════════════════════════════════════════════════════════════


class TestGetZombieRows:
    """Testes para get_zombie_rows() com e sem enriched_declared."""

    def test_sem_enriched_retorna_colunas_basicas(self) -> None:
        """Sem enriched_declared, retorna apenas pacote e status."""
        from gui.report import get_zombie_rows

        rows = get_zombie_rows(MOCK_RESULT_PLAIN)
        assert len(rows) == 1
        assert rows[0]["pacote"] == "unused-lib>=1.0.0"
        assert rows[0]["status"] == "Zumbi"
        assert "tamanho" not in rows[0]
        assert "idade_dias" not in rows[0]

    def test_sem_chave_enriched_retrocompativel(self) -> None:
        """Resultado sem a chave enriched_declared não falha (retrocompatibilidade)."""
        from gui.report import get_zombie_rows

        rows = get_zombie_rows(MOCK_RESULT_NO_ENRICHED_KEY)
        assert len(rows) == 1
        assert rows[0]["pacote"] == "numpy"
        assert "tamanho" not in rows[0]

    def test_com_enriched_retorna_colunas_extras(self) -> None:
        """Com enriched_declared preenchido, retorna tamanho e idade_dias."""
        from gui.report import get_zombie_rows

        rows = get_zombie_rows(MOCK_RESULT_ENRICHED)
        assert len(rows) == 1
        row = rows[0]
        assert row["pacote"] == "unused-lib>=1.0.0"
        assert row["status"] == "Zumbi"
        assert "tamanho" in row
        assert "idade_dias" in row

    def test_com_enriched_tamanho_formatado_kb(self) -> None:
        """Tamanho de 51200 bytes deve ser formatado como '50 KB'."""
        from gui.report import get_zombie_rows

        rows = get_zombie_rows(MOCK_RESULT_ENRICHED)
        assert rows[0]["tamanho"] == "50 KB"

    def test_com_enriched_idade_dias_numerica(self) -> None:
        """Idade de 30 dias deve ser retornada como string '30'."""
        from gui.report import get_zombie_rows

        rows = get_zombie_rows(MOCK_RESULT_ENRICHED)
        assert rows[0]["idade_dias"] == "30"

    def test_com_enriched_size_unknown_exibe_nd(self) -> None:
        """Size_bytes == -1 (SIZE_UNKNOWN) deve ser exibido como 'N/D'."""
        from gui.report import get_zombie_rows

        result = {
            **MOCK_RESULT_PLAIN,
            "dependencies": {**MOCK_RESULT_PLAIN["dependencies"], "zombies": ["flask==2.3.0"]},
            "enriched_declared": {
                "flask": {"size_bytes": -1, "age_days": None},
            },
        }
        rows = get_zombie_rows(result)
        assert rows[0]["tamanho"] == "N/D"
        assert rows[0]["idade_dias"] == "N/D"

    def test_com_enriched_age_none_exibe_nd(self) -> None:
        """age_days == None deve ser exibido como 'N/D'."""
        from gui.report import get_zombie_rows

        result = {
            **MOCK_RESULT_PLAIN,
            "dependencies": {**MOCK_RESULT_PLAIN["dependencies"], "zombies": ["flask==2.3.0"]},
            "enriched_declared": {
                "flask": {"size_bytes": 10240, "age_days": None},
            },
        }
        rows = get_zombie_rows(result)
        assert rows[0]["idade_dias"] == "N/D"

    def test_pacote_sem_meta_no_enriched(self) -> None:
        """Zumbi sem entrada no enriched_declared exibe 'N/D' para ambas as colunas."""
        from gui.report import get_zombie_rows

        result = {
            **MOCK_RESULT_PLAIN,
            "dependencies": {**MOCK_RESULT_PLAIN["dependencies"], "zombies": ["obscuro-lib"]},
            "enriched_declared": {"requests": {"size_bytes": 1000, "age_days": 10}},
        }
        rows = get_zombie_rows(result)
        assert rows[0]["tamanho"] == "N/D"
        assert rows[0]["idade_dias"] == "N/D"

    def test_sem_zombies_retorna_lista_vazia(self) -> None:
        """Retorna lista vazia quando não há zumbis."""
        from gui.report import get_zombie_rows

        result = {**MOCK_RESULT_PLAIN}
        result["dependencies"] = {**MOCK_RESULT_PLAIN["dependencies"], "zombies": []}
        rows = get_zombie_rows(result)
        assert rows == []

    def test_tamanho_mb_formatado(self) -> None:
        """Tamanho >= 1 MB deve ser formatado como 'X MB'."""
        from gui.report import get_zombie_rows

        result = {
            **MOCK_RESULT_PLAIN,
            "dependencies": {**MOCK_RESULT_PLAIN["dependencies"], "zombies": ["biglib"]},
            "enriched_declared": {
                "biglib": {"size_bytes": 2 * 1024 * 1024, "age_days": 5},
            },
        }
        rows = get_zombie_rows(result)
        assert rows[0]["tamanho"] == "2 MB"


# ══════════════════════════════════════════════════════════════════════════════
# Testes de build_zombie_csv_bytes()
# ══════════════════════════════════════════════════════════════════════════════


class TestBuildZombieCsvBytes:
    """Testes para build_zombie_csv_bytes() com e sem dados enriquecidos."""

    def test_sem_enriched_cabecalho_basico(self) -> None:
        """CSV sem enriquecimento tem cabeçalho com 'pacote' e 'status'."""
        from gui.report import build_zombie_csv_bytes

        raw = build_zombie_csv_bytes(MOCK_RESULT_PLAIN)
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text), delimiter=";")
        assert reader.fieldnames is not None
        assert "Pacote" in reader.fieldnames
        assert "Status" in reader.fieldnames
        assert "Tamanho (KB)" not in reader.fieldnames
        assert "Idade (dias)" not in reader.fieldnames

    def test_sem_enriched_contem_pacote_zumbi(self) -> None:
        """CSV sem enriquecimento contém a entrada do pacote zumbi."""
        from gui.report import build_zombie_csv_bytes

        raw = build_zombie_csv_bytes(MOCK_RESULT_PLAIN)
        text = raw.decode("utf-8-sig")
        assert "unused-lib>=1.0.0" in text

    def test_com_enriched_cabecalho_inclui_colunas_extras(self) -> None:
        """CSV com enriquecimento inclui colunas 'tamanho' e 'idade_dias'."""
        from gui.report import build_zombie_csv_bytes

        raw = build_zombie_csv_bytes(MOCK_RESULT_ENRICHED)
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text), delimiter=";")
        assert reader.fieldnames is not None
        assert "Tamanho (KB)" in reader.fieldnames
        assert "Idade (dias)" in reader.fieldnames

    def test_com_enriched_valores_corretos_no_csv(self) -> None:
        """CSV com enriquecimento contém os valores de tamanho e idade corretos."""
        from gui.report import build_zombie_csv_bytes

        raw = build_zombie_csv_bytes(MOCK_RESULT_ENRICHED)
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text), delimiter=";")
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["Tamanho (KB)"] == "50 KB"
        assert rows[0]["Idade (dias)"] == "30"

    def test_sem_zombies_csv_apenas_cabecalho(self) -> None:
        """CSV com lista de zumbis vazia contém apenas o cabeçalho."""
        from gui.report import build_zombie_csv_bytes

        result = {**MOCK_RESULT_PLAIN}
        result["dependencies"] = {**MOCK_RESULT_PLAIN["dependencies"], "zombies": []}
        raw = build_zombie_csv_bytes(result)
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), delimiter=";")
        rows = list(reader)
        assert rows == []

    def test_encoding_utf8_bom(self) -> None:
        """Bytes do CSV devem começar com BOM UTF-8 para compatibilidade Excel."""
        from gui.report import build_zombie_csv_bytes

        raw = build_zombie_csv_bytes(MOCK_RESULT_PLAIN)
        assert raw[:3] == b"\xef\xbb\xbf"

    def test_delimiter_ponto_e_virgula(self) -> None:
        """CSV deve usar ponto-e-vírgula como delimitador."""
        from gui.report import build_zombie_csv_bytes

        raw = build_zombie_csv_bytes(MOCK_RESULT_PLAIN)
        text = raw.decode("utf-8-sig")
        assert ";" in text


# ══════════════════════════════════════════════════════════════════════════════
# Testes de render_zombie_table() com mock do Streamlit
# ══════════════════════════════════════════════════════════════════════════════


class TestRenderZombieTable:
    """Testes de render_zombie_table() com Streamlit completamente mockado."""

    def _make_st_mock(self) -> MagicMock:
        """Cria mock do módulo streamlit com os atributos necessários."""
        st = MagicMock()
        st.column_config = MagicMock()
        st.column_config.TextColumn = MagicMock(return_value=MagicMock())
        return st

    def test_sem_zombies_chama_success(self) -> None:
        """Quando não há zumbis, deve chamar st.success."""
        from gui import report

        st_mock = self._make_st_mock()
        result_vazio = {**MOCK_RESULT_PLAIN}
        result_vazio["dependencies"] = {**MOCK_RESULT_PLAIN["dependencies"], "zombies": []}

        with patch.dict("sys.modules", {"streamlit": st_mock, "pandas": MagicMock()}):
            report.render_zombie_table(result_vazio)

        st_mock.success.assert_called_once()

    def test_com_zombies_chama_error(self) -> None:
        """Quando há zumbis, deve chamar st.error com a contagem."""
        from gui import report

        st_mock = self._make_st_mock()

        with patch.dict("sys.modules", {"streamlit": st_mock, "pandas": MagicMock()}):
            report.render_zombie_table(MOCK_RESULT_PLAIN)

        st_mock.error.assert_called_once()
        call_args = st_mock.error.call_args[0][0]
        assert "1" in call_args

    def test_com_zombies_chama_dataframe(self) -> None:
        """Com zumbis presentes, deve renderizar st.dataframe."""
        from gui import report

        st_mock = self._make_st_mock()

        with patch.dict("sys.modules", {"streamlit": st_mock, "pandas": MagicMock()}):
            report.render_zombie_table(MOCK_RESULT_PLAIN)

        st_mock.dataframe.assert_called_once()

    def test_com_enriched_column_config_tem_tamanho(self) -> None:
        """Com enriched_declared, column_config deve incluir 'tamanho' e 'idade_dias'."""
        from gui import report

        st_mock = self._make_st_mock()

        with patch.dict("sys.modules", {"streamlit": st_mock, "pandas": MagicMock()}):
            report.render_zombie_table(MOCK_RESULT_ENRICHED)

        st_mock.dataframe.assert_called_once()
        _, kwargs = st_mock.dataframe.call_args
        column_config = kwargs.get("column_config", {})
        assert "tamanho" in column_config
        assert "idade_dias" in column_config

    def test_sem_enriched_column_config_nao_tem_tamanho(self) -> None:
        """Sem enriched_declared, column_config não deve incluir colunas extras."""
        from gui import report

        st_mock = self._make_st_mock()

        with patch.dict("sys.modules", {"streamlit": st_mock, "pandas": MagicMock()}):
            report.render_zombie_table(MOCK_RESULT_PLAIN)

        st_mock.dataframe.assert_called_once()
        _, kwargs = st_mock.dataframe.call_args
        column_config = kwargs.get("column_config", {})
        assert "tamanho" not in column_config
        assert "idade_dias" not in column_config

    def test_render_chama_markdown_e_caption(self) -> None:
        """render_zombie_table deve sempre chamar st.markdown e st.caption."""
        from gui import report

        st_mock = self._make_st_mock()

        with patch.dict("sys.modules", {"streamlit": st_mock, "pandas": MagicMock()}):
            report.render_zombie_table(MOCK_RESULT_PLAIN)

        st_mock.markdown.assert_called()
        st_mock.caption.assert_called()

    def test_render_com_result_sem_chave_enriched(self) -> None:
        """Resultado legado sem 'enriched_declared' não deve causar exceção."""
        from gui import report

        st_mock = self._make_st_mock()

        with patch.dict("sys.modules", {"streamlit": st_mock, "pandas": MagicMock()}):
            # Não deve lançar exceção
            report.render_zombie_table(MOCK_RESULT_NO_ENRICHED_KEY)

        st_mock.error.assert_called_once()
