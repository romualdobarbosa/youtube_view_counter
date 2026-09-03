FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Instala as dependências primeiro para aproveitar o cache de layers do Docker
# em rebuilds que só mudam código-fonte.
COPY requirements-docker.txt ./
RUN pip install -r requirements-docker.txt

COPY src/ ./src/
COPY copa2026/ ./copa2026/
COPY dbt/ ./dbt/

# data/ e logs/ são criados em runtime pelo próprio código (config.py / database.py)
# e devem ser montados como volume — nunca ficam embutidos na imagem.
#
# dbt/requirements.txt e copa2026/dbt/requirements.txt não entram em
# requirements-docker.txt de propósito: pinam versões de dbt-core diferentes e
# incompatíveis entre si (dbt-sqlite vs dbt-duckdb — ver os dois arquivos). Os
# serviços "dbt" e "copa-dbt" do docker-compose instalam cada um a sua na hora
# de rodar, em vez de tudo pré-instalado nesta imagem.

EXPOSE 8501

CMD ["streamlit", "run", "src/dashboard.py", "--server.address=0.0.0.0"]
