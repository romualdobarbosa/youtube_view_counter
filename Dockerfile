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

# data/ e logs/ são criados em runtime pelo próprio código (config.py / database.py)
# e devem ser montados como volume — nunca ficam embutidos na imagem.

EXPOSE 8501

CMD ["streamlit", "run", "src/dashboard.py", "--server.address=0.0.0.0"]
