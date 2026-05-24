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

## 5. Indexar el corpus

```bash
python main.py --add corpus/raw/xh018-DR-v10_1_1.txt
```

Verificar que los chunks quedaron indexados:

```bash
python main.py --stats
```

## 6. Correr el asistente

```bash
python main.py
```

## 7. Comandos disponibles

```bash
python main.py                          # modo consulta interactiva
python main.py --add <archivo>          # indexa un documento al corpus
python main.py --remove <archivo>       # elimina todos los chunks de un archivo
python main.py --delete <id_sha1>       # elimina un chunk por ID SHA-1
python main.py --stats                  # muestra total de chunks indexados
python main.py --model <ruta_o_nombre>  # override del modelo de embeddings
```

## 8. Re-indexar un documento actualizado

```bash
python main.py --remove corpus/raw/xh018-DR-v10_1_1.txt
python main.py --add corpus/raw/xh018-DR-v10_1_1.txt
```

## 9. Resetear el corpus completo

```bash
rm -rf data/chroma_db/
python main.py --add corpus/raw/xh018-DR-v10_1_1.txt
```
