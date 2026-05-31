# Instrucciones de uso — Asistente DRC VLSI

## 1. Requisitos previos

- Python 3.10+
- [uv](https://astral.sh/uv) instalado
- [Ollama](https://ollama.com) instalado con el modelo `phi4-mini`

## 2. Inicializar el entorno

```bash
# Crea el entorno virtual en .venv e instala todas las dependencias
uv sync

# Activar el entorno (opcional si usas `uv run`)
source .venv/bin/activate
```

## 3. Descargar el modelo LLM

```bash
ollama pull phi4-mini
```

## 4. Iniciar Ollama

```bash
ollama serve
```

Si aparece `address already in use`, Ollama ya está corriendo en `http://localhost:11434`.

## 5. Indexar el corpus

```bash
uv run python main.py --add corpus/raw/xh018-DR-v10_1_1.txt
uv run python main.py --add corpus/annotated/ejemplos_anotados_DEF.json
uv run python main.py --add corpus/annotated-xh018_drc_solutions_only_txt_codes.json
```

Verificar que los chunks quedaron indexados:

```bash
uv run python main.py --stats
```

## 6. Correr el asistente

```bash
uv run python main.py
```

## 7. Comandos disponibles

```bash
uv run python main.py                          # modo consulta interactiva
uv run python main.py --add <archivo>          # indexa un documento al corpus
uv run python main.py --remove <archivo>       # elimina todos los chunks de un archivo
uv run python main.py --delete <id_sha1>       # elimina un chunk por ID SHA-1
uv run python main.py --stats                  # muestra total de chunks indexados
uv run python main.py --model <ruta_o_nombre>  # override del modelo de embeddings
```

## 8. Re-indexar un documento actualizado

```bash
uv run python main.py --remove corpus/raw/xh018-DR-v10_1_1.txt
uv run python main.py --add corpus/raw/xh018-DR-v10_1_1.txt
```

## 9. Base vectorial persistente

ChromaDB guarda la base vectorial en `data/chroma_db/`.
No borres esa carpeta para reiniciar el corpus sin confirmación explícita del equipo, porque contiene la indexación persistente usada por el asistente.

Para actualizar documentos, usa `--remove` y luego `--add` sobre el archivo correspondiente.
