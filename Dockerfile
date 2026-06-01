FROM python:3.10-slim
WORKDIR /opt/drc-assistant

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc g++ git curl \
    && rm -rf /var/lib/apt/lists/*

ARG GIT_REPO=https://github.com/<usuario>/<repo>.git
ARG GIT_BRANCH=main
RUN git clone --depth 1 --branch ${GIT_BRANCH} ${GIT_REPO} .

# Copiar torch pre-descargado
COPY torch-2.12.0-cp310-cp310-manylinux_2_28_aarch64.whl /tmp/

# Instalar torch desde archivo local
RUN pip install --no-cache-dir /tmp/torch-2.12.0-cp310-cp310-manylinux_2_28_aarch64.whl

# Instalar resto de dependencias
RUN pip install --no-cache-dir \
        --timeout 300 \
        --retries 5 \
        sentence-transformers==3.4.1 \
        chromadb==0.6.3 \
        "pypdf>=4.0.0" \
        requests==2.32.3

RUN python3 << 'EOF'
from sentence_transformers import SentenceTransformer
SentenceTransformer('all-MiniLM-L6-v2')
print('Modelo descargado correctamente')
EOF

RUN sed -i 's/MODEL_NAME = "qwen3:4b"/MODEL_NAME = "phi4-mini"/' rag/pipeline.py
RUN mkdir -p data/chroma_db logs
ENTRYPOINT ["python3", "main.py"]
