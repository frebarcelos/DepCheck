# CLAUDE.md — Guia de Contexto para IA: DepCheck

> **Fonte de verdade para qualquer agente de IA que assume este projeto.**
> Leia este arquivo antes de qualquer ação de código.

---

## 1. O que é este projeto

**DepCheck** é um analisador de dependências Python com arquitetura modular e paradigma **estritamente procedural** (sem classes de domínio — apenas funções). A ferramenta:

1. Recebe um `.zip` de um projeto Python via upload na GUI (Streamlit).
2. Extrai, filtra e varre os arquivos `.py` com AST.
3. Cruza dependências declaradas (`pyproject.toml` / `requirements.txt`) com imports reais.
4. Classifica em três categorias: **Zumbis** (declarados mas não usados), **Fantasmas** (usados mas não declarados), **Desatualizados** (versão abaixo do PyPI latest).
5. Exibe relatório tabelar + gráficos na GUI e permite exportação CSV/JSON.

---

## 2. Estrutura do repositório

```
projeto-sprint-4/          ← CÓDIGO OFICIAL VIGENTE (sempre use este)
├── core/
│   ├── aliases.py         ← Mapeamento PIL→Pillow etc. (anti-falsos-positivos)
│   ├── constants.py       ← MAX_ZIP_SIZE_MB, MAX_ZIP_SIZE_BYTES, MAX_ZIP_RATIO
│   ├── paths.py           ← TEMP_DIR, get_upload_dir()
│   └── results_model.py   ← get_empty_result_model() — dicionário padrão de saída
├── gui/
│   ├── charts.py          ← render_bar_chart_outdated() (Altair/Plotly)
│   ├── home.py            ← Ponto de entrada Streamlit: upload → análise → relatório
│   └── report.py          ← render_zombie_table, render_ghost_table, render_kpi_cards,
│                             render_outdated_table, render_pie_chart + botões CSV/JSON
├── src/
│   ├── analyzers/
│   │   ├── ghost_analyzer.py     ← find_ghost_dependencies()
│   │   ├── outdated_analyzer.py  ← check_outdated_dependencies()
│   │   └── zombie_analyzer.py    ← find_zombie_dependencies()
│   ├── clients/
│   │   └── pypi_client.py        ← fetch_pypi_info(), fetch_latest_version(), lru_cache
│   ├── parsers/
│   │   ├── pyproject_parser.py   ← parse_pyproject()
│   │   └── requirements_parser.py← parse_requirements()
│   ├── reporters/
│   │   ├── csv_reporter.py       ← export_to_csv()
│   │   └── json_reporter.py      ← export_to_json()
│   ├── utils/
│   │   └── stdlib_filters.py     ← is_stdlib_module(), get_stdlib_module_names()
│   ├── code_parser.py            ← get_all_imports() via AST
│   ├── decompressor.py           ← validate_zip(), extract_zip(), cleanup_session()
│   ├── filter.py                 ← filter_extracted() — ignora tests/, docs/, .venv/ etc.
│   └── orchestrator.py           ← run_analysis() — pipeline central procedural
└── tests/                        ← Suite completa de testes
```

**Pastas `devN/` e `projeto-sprint-N/`** são artefatos históricos de desenvolvimento isolado por desenvolvedor — não modifique sem instrução explícita.

---

## 3. Como rodar

```bash
cd projeto-sprint-4/

# Subir GUI
docker compose up --build

# Acessar em: http://localhost:8501

# Rodar testes com cobertura (obrigatório ≥ 80%)
docker compose run --rm app pytest --cov=src --cov=core --cov-fail-under=80 tests/

# Lint e tipos
ruff check .
mypy .
```

---

## 4. Regras imutáveis do projeto

| Regra | Detalhe |
|---|---|
| **Paradigma procedural** | Proibido criar classes de domínio. Apenas funções. |
| **TDD obrigatório** | Escreva o teste antes da implementação. Teste deve falhar primeiro. |
| **Cobertura mínima 80%** | Bloqueio via `.pre-commit-config.yaml` no commit. |
| **Docker primeiro** | Nunca rode `pytest` solto — sempre via `docker compose run --rm app pytest ...` |
| **Sem modificar outros devs** | Durante sprint ativa, cada dev trabalha isolado em `devN/` |
| **Merge em `projeto-sprint-N/`** | Integração acontece apenas ao fechar a sprint |

---

## 5. Modelo de dados (`results_model.py`)

```python
{
    "project_info": {
        "name": "unknown",
        "analyzed_at": ""          # ISO 8601
    },
    "dependencies": {
        "declared": [],            # list[str] — ex: ["requests>=2.28.0"]
        "imported": [],            # list[str] — módulos AST
        "zombies": [],             # list[str] — declarados mas não importados
        "ghosts": [],              # list[str] — importados mas não declarados
        "outdated": {}             # dict[str, {"latest_version": str, "days_outdated": int}]
    },
    "statistics": {
        "total_declared": 0,
        "total_imported": 0,
        "total_zombies": 0,
        "total_ghosts": 0,
        "total_outdated": 0
    }
}
```

---

## 6. Estado atual vs. requisitos da descrição do problema

### 6.1 O que está implementado e funcionando

- Upload de ZIP com validações defensivas (extensão, tamanho, zip-bomb, path-traversal)
- Extração segura e limpeza automática de temp após análise
- Parsing de `pyproject.toml` e `requirements.txt`
- Extração de imports via AST (`code_parser.py`)
- Detecção de Zumbis, Fantasmas e Desatualizados
- GUI Streamlit com tabelas, KPI cards, gráfico de pizza (Plotly) e gráfico de barras
- Exportação CSV (zumbis) e JSON (relatório completo) via botões na GUI
- Filtragem automática de `tests/`, `docs/`, `.venv/` etc.
- Consulta PyPI com `lru_cache`
- Suite de testes: unitários + E2E + cobertura
- Type hints completos e docstrings Google Style

### 6.2 Status dos requisitos da descrição do problema

A `descricao.md` exige que o relatório inclua, **para cada categoria (total, zumbis, fantasmas)**:

| Campo exigido | Situação atual |
|---|---|
| Lista de dependências | ✅ Implementado |
| Quantidade | ✅ Implementado (KPI cards) |
| **Tamanho** (size do pacote) | ✅ Implementado — `fetch_package_size()` em `pypi_client.py`; `enriched_declared` no modelo; colunas Tamanho nas tabelas de Zumbis, Fantasmas, Todas as Deps e gráfico Top-10 |
| **Idade** (data atual − data de lançamento da versão usada) | ✅ Implementado — `fetch_release_date()` em `pypi_client.py`; `age_size_analyzer.py` calcula `age_days`; colunas Idade (dias) nas tabelas de Zumbis, Fantasmas e Todas as Deps |

Além disso:

| Regra de implementação | Situação |
|---|---|
| "A configuração do projeto (diretório raiz, exclusões) deve ser feita através de interface gráfica" | ✅ Implementado — `render_exclusion_config()` em `gui/home.py` com `st.multiselect` + campo customizado; `filter_extracted()` em `src/filter.py` aceita `extra_excluded_dirs` |

---

## 7. Estado atual — todos os requisitos implementados

Todos os requisitos da `descricao.md` estão implementados em `projeto-sprint-4/` (v0.4.1). Bugs de parsing de datas corrigidos em abril/2026.

### Arquitetura de enriquecimento (Sprint 4 final)

```
pypi_client.py
  fetch_package_size(name, version) → int (bytes, -1 se N/D)
  fetch_release_date(name, version) → str|None (ISO 8601)

age_size_analyzer.py
  compute_enriched_metadata(declared) → {"pkg": {"size_bytes": int, "age_days": int|None}}

orchestrator.py
  _enrich_dependencies(declared) → chama compute_enriched_metadata
  _fill_result_model() → popula result["enriched_declared"] + stats

gui/report.py
  render_zombie_table()      → colunas Tamanho + Idade (dias)
  render_ghost_table()       → colunas Tamanho + Idade (dias)
  render_all_deps_table()    → Pacote | Status | Tamanho | Idade
  render_kpi_cards()         → 8 cards: inclui Tamanho Total + Idade Média
  render_size_bar_chart()    → Top-10 pacotes mais pesados (via gui/charts.py)

gui/home.py
  render_exclusion_config()  → st.multiselect com dirs padrão + campo customizado
```

### Bugs corrigidos (2026-04-12)

- `outdated_analyzer.py`: parsing de datas com microsegundos; comparação de versão ausente (todo pacote era marcado como desatualizado ou nenhum era detectado); `days_outdated` agora reflete a versão declarada, não a latest.
- `age_size_analyzer.py`: mesmo bug de parsing de datas com microsegundos.
- `pypi_client.py`: timeout aumentado de 5s para 10s (Docker/Windows).
- `gui/report.py`: tabela de desatualizados agora exibe coluna "Versão Declarada".

---

## 8. Critérios de avaliação (plano de ensino)

A nota final é: `NF = Teoria×0.2 + Prática em Grupo×0.4 + Prática Individual×0.4`

**Para "TOk" (10) na Prática:**
- Código correto e funcional
- Abrangência compatível com o esforço esperado
- Domínio demonstrado sobre os artefatos
- Código no escopo do problema proposto

**Atenção:** Commits precisam estar no repositório até **23:59 do domingo anterior à aula de avaliação**.

---

## 9. Fluxo de Sprint (para continuidade futura)

1. Copiar `projeto-sprint-4/` → pasta `devN/` de cada desenvolvedor como base
2. Cada dev implementa **isolado** na sua pasta
3. Testes escritos **antes** da implementação (TDD)
4. Ao encerrar: merge em `projeto-sprint-5/` + `GUIA_MERGE_SPRINT_5.md` + `README_SPRINT_5.md` em cada `devN/`

---

## 11. Divisão de trabalho — Sprint 4 (semana final)

> **Contexto:** Última semana do Sprint 4. Os requisitos de *tamanho*, *idade para todas as categorias* e *configuração de exclusões via GUI* estão ausentes. Cada desenvolvedor trabalha isolado em sua pasta `devN/`, que já contém uma cópia completa do projeto baseada em `projeto-sprint-4/`. O trabalho equivale a um dia produtivo de um desenvolvedor pleno (design + implementação + testes + documentação).

### Novo campo no modelo de dados (contratos entre devs)

Todos os devs devem considerar que o `results_model.py` terá o seguinte novo campo após o merge:

```python
"enriched_declared": {}
# dict[str, {"size_bytes": int, "age_days": int | None}]
# Exemplo: {"requests": {"size_bytes": 102400, "age_days": 180}}
# size_bytes = -1 quando indisponível; age_days = None quando indisponível
```

E a nova função em `src/analyzers/age_size_analyzer.py` (Dev 3):

```python
def compute_enriched_metadata(declared: list[str]) -> dict[str, dict]:
    """Retorna {package_name: {"size_bytes": int, "age_days": int|None}} para cada dep declarada."""
```

### Dev 1 — Core / Modelo / Zombie table

**Pasta:** `dev1/`  
**Arquivos sob sua responsabilidade:**
- `core/results_model.py` → adicionar `"enriched_declared": {}` no modelo base
- `core/constants.py` → adicionar `SIZE_UNKNOWN = -1`, `DEFAULT_EXCLUDED_DIRS` como lista mutável
- `src/analyzers/zombie_analyzer.py` → adicionar helper `extract_package_name(dep: str) -> str` (extrai nome limpo da string de dep)
- `gui/report.py` → atualizar `render_zombie_table()` para mostrar colunas Tamanho (KB) e Idade (dias) quando disponíveis em `result["enriched_declared"]`; atualizar `build_zombie_csv_bytes()` para incluir esses campos
- `tests/test_zombie_enriched.py` → novo arquivo de testes cobrindo enriched zombie flow
- `dev1/README_SPRINT_4_FINAL.md` → README com as alterações da semana

### Dev 2 — Filter / Ghost table / Configuração GUI

**Pasta:** `dev2/`  
**Arquivos sob sua responsabilidade:**
- `src/filter.py` → adicionar `extra_excluded_dirs: list[str] | None = None` à assinatura de `filter_extracted()`, mantendo retrocompatibilidade
- `gui/home.py` → adicionar função `render_exclusion_config() -> list[str]` que renderiza `st.multiselect` para configurar diretórios ignorados (padrão: lista de `IGNORED_DIRS`); integrar ao `process_upload()`
- `gui/report.py` → atualizar `render_ghost_table()` para mostrar Tamanho e Idade de `enriched_declared`; atualizar `build_json_bytes()` para incluir `enriched_declared`
- `tests/test_filter_configurable.py` → novo arquivo de testes para exclusões configuráveis
- `dev2/README_SPRINT_4_FINAL.md` → README com as alterações da semana

### Dev 3 — PyPI client / Tamanho e Idade / Novo analyzer

**Pasta:** `dev3/`  
**Arquivos sob sua responsabilidade:**
- `src/clients/pypi_client.py` → adicionar `fetch_package_size(package_name, version=None) -> int` e `fetch_release_date(package_name, version=None) -> str | None`, ambas com `lru_cache`
- `src/analyzers/outdated_analyzer.py` → incluir `"size_bytes"` no dict de cada pacote desatualizado
- `src/analyzers/age_size_analyzer.py` → **NOVO arquivo** com `compute_enriched_metadata(declared: list[str]) -> dict[str, dict]`
- `tests/test_age_size_analyzer.py` → testes do novo analyzer com HTTP mockado
- `tests/test_pypi_client_enriched.py` → testes das novas funções do pypi_client
- `dev3/README_SPRINT_4_FINAL.md` → README com as alterações da semana

### Dev 4 — Orchestrator / Tabela geral / KPI expandido

**Pasta:** `dev4/`  
**Arquivos sob sua responsabilidade:**
- `src/orchestrator.py` → chamar `compute_enriched_metadata()` e popular `result["enriched_declared"]`; adicionar helper `_enrich_dependencies(declared: list[str]) -> dict`
- `gui/report.py` → adicionar `render_all_deps_table(result)` (tabela de TODAS as deps com colunas: Pacote, Status, Tamanho, Idade); atualizar `render_kpi_cards()` adicionando métricas de "Tamanho Total" e "Idade Média"
- `gui/home.py` → chamar `render_all_deps_table` em `_render_report()` antes das demais tabelas
- `tests/test_orchestrator_enriched.py` → testes do pipeline enriquecido com PyPI mockado
- `dev4/README_SPRINT_4_FINAL.md` → README com as alterações da semana

### Dev 5 — Reporters / Gráfico de tamanho / Release

**Pasta:** `dev5/`  
**Arquivos sob sua responsabilidade:**
- `src/reporters/csv_reporter.py` → reescrever `export_to_csv()` incluindo colunas Tamanho (KB) e Idade (dias) de `enriched_declared`
- `src/reporters/json_reporter.py` → garantir que `export_to_json()` inclua `enriched_declared` no output
- `gui/charts.py` → adicionar `render_size_bar_chart(result)` mostrando os top-10 pacotes mais pesados em KB; integrar chamada em `gui/home.py` dentro de `_render_report()`
- `pyproject.toml` → bump de versão `0.4.0` → `0.4.1`
- `tests/test_reporters_enriched.py` → testes de CSV/JSON com dados enriquecidos
- `dev5/README_SPRINT_4_FINAL.md` → README com as alterações da semana

### Merge final

Após todos os devs concluírem, o merge integra todas as contribuições em `projeto-sprint-4/`:
1. `core/` → versão de Dev 1
2. `src/filter.py` → versão de Dev 2
3. `src/clients/pypi_client.py` → versão de Dev 3
4. `src/analyzers/age_size_analyzer.py` → novo arquivo de Dev 3
5. `src/analyzers/outdated_analyzer.py` → versão de Dev 3
6. `src/orchestrator.py` → versão de Dev 4
7. `src/reporters/` → versão de Dev 5
8. `gui/charts.py` → versão de Dev 5 (inclui render_size_bar_chart)
9. `gui/home.py` → combinar Dev 2 (exclusions widget) + Dev 4 (render_all_deps_table call) + Dev 5 (render_size_bar_chart call)
10. `gui/report.py` → combinar Dev 1 (zombie) + Dev 2 (ghost) + Dev 4 (all_deps + kpi)
11. `tests/` → todos os novos arquivos de todos os devs
12. Escrever `GUIA_MERGE_SPRINT_4_FINAL.md` na raiz

---

## 10. Dependências principais

| Pacote | Uso |
|---|---|
| `streamlit` | GUI |
| `plotly` | Gráfico de pizza interativo |
| `altair` / `pandas` | Gráfico de barras + DataFrames |
| `requests` | Consulta PyPI |
| `tomllib` / `tomli` | Parse de `pyproject.toml` |
| `ruff` | Lint |
| `mypy` | Type checking |
| `pytest` + `pytest-cov` | Testes e cobertura |
| `pre-commit` | Hooks de commit |
