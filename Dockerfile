# ── Imagem base ──────────────────────────────────────────────
FROM python:3.12-slim AS base

# Evita arquivos .pyc e buffers de saída
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ── Instala uv ───────────────────────────────────────────────
RUN pip install --no-cache-dir uv

# ── Copia manifesto de dependências ──────────────────────────
COPY pyproject.toml ./

# ── Instala dependências de produção ─────────────────────────
RUN uv pip install --system --no-cache .

# ── Copia o código-fonte ──────────────────────────────────────
COPY . .

# ── Cria diretório temporário ─────────────────────────────────
RUN mkdir -p /tmp/depcheck

# ── Expõe porta do Streamlit ─────────────────────────────────
EXPOSE 8501

# ── Healthcheck ──────────────────────────────────────────────
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# ── Entrypoint ───────────────────────────────────────────────
ENTRYPOINT ["python", "-m", "streamlit", "run", "gui/home.py", \
            "--server.port=8501", "--server.address=0.0.0.0"]
