# AGENTS.md - Contexto para Codex

## Resumen del proyecto
Este repositorio implementa un asistente RAG local para ayudar a estudiantes de VLSI del TEC a interpretar y corregir errores DRC de Cadence Virtuoso/Pegasus usando el PDK XFAB XH018 de 180 nm.

El sistema debe operar offline en una NVIDIA Jetson Nano 4GB. No debe depender de APIs externas ni de internet durante la ejecucion en laboratorio.

## Stack actual
- Python 3.10+
- CLI en `main.py`
- Embeddings: `sentence-transformers`, modelo por defecto `all-MiniLM-L6-v2`
- Vector store: ChromaDB persistente en `data/chroma_db/`
- LLM local: Ollama en `http://localhost:11434`
- Modelo Ollama activo en codigo: `phi4-mini` en `rag/pipeline.py`
- Lectura de corpus: `.txt`, `.md`, `.pdf`, `.json`
- Dependencias declaradas en `pyproject.toml`; `uv.lock` se versiona

## Dominio del asistente
- PDK: XFAB XH018 (180nm)
- Contexto: errores DRC en Cadence Virtuoso/Pegasus
- Celdas objetivo: NOT, AND, NOR
- Capas frecuentes: Metal1-Metal5, Poly, Ndiff, Pdiff, Contact/CT, Via1-Via4
- Tipos de regla: spacing, width, enclosure, extension/overlap, area minima y via/contact
- Consultas fuera de dominio deben responder con mensaje claro de fuera de alcance

## Estructura relevante
- `main.py`: punto de entrada CLI y modos de consulta/admin.
- `rag/chunker.py`: carga documentos y genera chunks; JSON anotado se convierte a texto legible.
- `rag/embeddings.py`: carga el modelo de embeddings en CPU y genera vectores normalizados.
- `rag/vector_store.py`: inicializa ChromaDB, indexa chunks, busca por embedding y por keyword.
- `rag/pipeline.py`: orquesta el flujo RAG, arma prompt, consulta Ollama y limpia respuestas fuera de alcance.
- `rag/corpus_admin.py`: agrega, elimina y actualiza chunks/documentos del corpus.
- `corpus/raw/`: documentos fuente del PDK.
- `corpus/annotated/`: ejemplos/reglas anotadas en JSON.
- `docs/`: documentos de propuesta/diseño.
- `logs/`: logs locales de consultas; no versionar.
- `data/chroma_db/`: base vectorial local; no versionar ni borrar sin confirmacion.

## Comandos utiles
Usar `uv` cuando sea posible:

```bash
uv sync
uv run python main.py --stats
uv run python main.py --add corpus/raw/xh018-DR-v10_1_1.txt
uv run python main.py --add corpus/annotated/nand2_drc_errors.json
uv run python main.py
```

Comandos equivalentes si el entorno ya esta activado:

```bash
python main.py --stats
python main.py --add <archivo>
python main.py --remove <archivo>
python main.py --delete <id_sha1>
python main.py --model <ruta_o_nombre_modelo_embeddings>
```

## Flujo RAG esperado
1. El usuario ingresa un error DRC o una pregunta.
2. `process_query` detecta saludos/ayuda/gracias sin llamar al LLM.
3. Para consultas DRC, se genera embedding con `generate_embedding`.
4. Se recuperan chunks semanticos desde ChromaDB.
5. Si la consulta incluye codigos de regla con numeros, tambien se hace busqueda exacta por keyword.
6. `build_prompt` combina sistema, contexto y pregunta.
7. `query_llm` llama a Ollama con `stream=False`.
8. Si aparece el marcador `[FUERA_DE_ALCANCE]`, se devuelve una respuesta controlada.

## Reglas de trabajo importantes
- Mantener el proyecto local/offline; evitar introducir servicios cloud o dependencias innecesarias.
- Cuidar memoria: el objetivo es Jetson Nano 4GB, asi que evitar modelos grandes o cargas duplicadas.
- No borrar `data/chroma_db/` sin confirmacion explicita del usuario.
- No modificar ni truncar `logs/queries.log` salvo que el usuario lo pida.
- Mantener respuestas del asistente en espanol claro y directo.
- Preferir cambios pequenos y compatibles con la arquitectura actual.
- Si se cambia el modelo Ollama, actualizar tambien `instructions.md`, `README.md` y este archivo para evitar inconsistencias.

## Notas detectadas al revisar
- `README.md` menciona `gemma3:4b`, pero el codigo y `instructions.md` usan `phi4-mini`. Tomar `rag/pipeline.py` como fuente actual de verdad mientras no se decida lo contrario.
- No se encontraron tests automatizados en la revision inicial.
- Hay archivos generados/locales esperados: `data/chroma_db/chroma.sqlite3` y `logs/queries.log`.
- El repo tiene cambios locales existentes; no asumir que fueron hechos por Codex ni revertirlos.

