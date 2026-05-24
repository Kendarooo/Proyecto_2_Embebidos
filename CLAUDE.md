# CLAUDE.md — Asistente DRC VLSI

## Descripción del proyecto
Sistema RAG (Retrieval-Augmented Generation) local para asistir a estudiantes del curso VLSI del TEC con errores DRC al diseñar celdas estándar en Cadence Virtuoso con el PDK XFAB XH018. Corre completamente en una Jetson Nano 4GB, sin internet ni API externa.

## Equipo
- Alex — Directora del proyecto
- Kendall — Líder técnico (branch: kendall_dev)
- JP — Investigador

## Stack
- **Hardware:** Jetson Nano 4GB
- **SO:** Linux via Yocto Project
- **LLM:** phi4-mini via Ollama (host local: http://localhost:11434)
- **Embeddings:** all-MiniLM-L6-v2 (sentence-transformers, ~80MB)
- **Vector store:** ChromaDB (persistente en disco)
- **Interfaz:** Terminal CLI
- **Lenguaje:** Python 3

## Estructura del proyecto
```
Proyecto_2_Embebidos/
├── rag/
│   ├── chunker.py          # Módulo 1 — carga y troceado de documentos
│   ├── embeddings.py       # Módulo 2 — modelo de embeddings
│   ├── vector_store.py     # Módulo 3 — ChromaDB
│   ├── pipeline.py         # Módulo 4 — orquestador RAG
│   └── corpus_admin.py     # Módulo 5 — gestión del corpus
├── corpus/
│   ├── raw/                # Documentos fuente (PDFs, TXTs del PDK)
│   └── annotated/          # Ejemplos anotados en JSON
├── data/
│   └── chroma_db/          # Base de datos vectorial persistente (NO versionar)
├── docs/                   # Documentación del proyecto (PDF propuesta)
├── logs/                   # Logs de consultas (NO versionar)
├── instructions.md         # Instrucciones de uso y despliegue
├── pyproject.toml          # Dependencias del proyecto
├── README.md
└── main.py                 # Punto de entrada CLI
```

## Dominio delimitado
- **PDK:** XFAB XH018 (180nm)
- **Celdas:** NOT, AND, NOR
- **Capas:** Metal1–Metal5, Poly, Ndiff, Pdiff, Contact (CT), Via1–Via4
- **Tipos de error:** Spacing, Width, Enclosure, Extension/Overlap, Via/Contact rules
- **Fuera de scope:** Antenna rules, LVS, Density global, Well rules, Notch

## Módulos y funciones esperadas

### Módulo 1 — chunker.py
```python
load_document(file_path: str) -> str          # soporta .pdf, .txt, .md, .json
chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]
```

### Módulo 2 — embeddings.py
```python
load_embedding_model(model_name: str) -> SentenceTransformer
generate_embedding(text: str, model: SentenceTransformer) -> list[float]
```

### Módulo 3 — vector_store.py
```python
init_vector_store(path: str) -> Collection
index_chunks(chunks: list[str], embeddings: list[list[float]], collection: Collection, source: str = "") -> None
search_relevant_chunks(query_embedding: list[float], collection: Collection, n: int = 3) -> list[str]
delete_by_source(source: str, collection: Collection) -> int   # retorna chunks eliminados
```

### Módulo 4 — pipeline.py
```python
build_prompt(context_chunks: list[str], user_query: str) -> str
query_llm(prompt: str, host: str) -> str
process_query(user_query: str, collection: Collection, embedder: SentenceTransformer, llm_host: str) -> str
```

### Módulo 5 — corpus_admin.py
```python
add_document(file_path: str, collection: Collection, embedder: SentenceTransformer, chunk_size: int = 512, overlap: int = 64) -> None
update_example(example_id: str, new_content: str, collection: Collection, embedder: SentenceTransformer) -> None
remove_document(file_path: str, collection: Collection) -> None   # elimina todos los chunks de un archivo por source
delete_example(example_id: str, collection: Collection) -> None   # elimina un chunk por ID SHA-1
```

## CLI — main.py
```
python main.py                          # modo consulta interactiva
python main.py --add <archivo>          # indexa un documento al corpus
python main.py --remove <archivo>       # elimina todos los chunks de un archivo
python main.py --delete <id_sha1>       # elimina un chunk por ID
python main.py --stats                  # muestra total de chunks indexados
python main.py --model <ruta_o_nombre>  # override del modelo de embeddings
```

## Restricciones críticas
- Máximo 4GB RAM total en Jetson Nano — evitar cargar modelos grandes en memoria simultáneamente
- Modelo LLM máximo 4B parámetros Q4
- Sin internet en ninguna etapa de ejecución
- Ollama corre como servicio local en `http://localhost:11434`
- ChromaDB persiste en `data/chroma_db/` — nunca borrar sin confirmación del equipo

## Formato del corpus anotado (JSON)
```json
{
  "error_raw": "METAL1_S: SPACE < 0.28, actual = 0.13um",
  "celda": "NOT",
  "capa": "Metal1",
  "tipo": "Spacing",
  "explicacion": "...",
  "correccion": "...",
  "error_comun": "..."
}
```

## Entregas
- 2026-05-25: Bitácoras + repositorio GitHub completo
- 2026-06-01: Demostración final presencial en Jetson Nano

## Convenciones de código
- Python 3, sin dependencias fuera del stack definido
- Sin comentarios obvios; solo comentarios para invariantes no evidentes
- Logs de consultas en `logs/` con timestamp y query
- El pipeline no debe lanzar excepciones al usuario — manejar errores con mensajes claros en CLI
