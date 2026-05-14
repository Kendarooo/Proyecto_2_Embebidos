#!/usr/bin/env python3
import argparse
import datetime
import os
import sys

from rag.embeddings import load_embedding_model
from rag.vector_store import init_vector_store
from rag.pipeline import process_query
from rag.corpus_admin import add_document, delete_example

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "data", "chroma_db")
LOG_PATH = os.path.join(os.path.dirname(__file__), "logs", "queries.log")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
OLLAMA_HOST = "http://localhost:11434"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log_query(query: str, answer: str) -> None:
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}]\nQ: {query}\nA: {answer}\n{'-' * 60}\n")


def _print_banner() -> None:
    print("=" * 60)
    print("  Asistente DRC — PDK XFAB XH018 (180nm)")
    print("  Celdas: NOT, AND, NOR")
    print("  Escribe 'salir' para terminar.")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Modos
# ---------------------------------------------------------------------------

def modo_consulta(embedder, collection) -> None:
    _print_banner()
    while True:
        try:
            query = input("\nConsulta DRC> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSaliendo.")
            break

        if not query:
            continue
        if query.lower() in ("salir", "exit", "quit"):
            print("Hasta luego.")
            break

        print("\nProcesando...\n")
        answer = process_query(query, collection, embedder, OLLAMA_HOST)
        print(answer)
        _log_query(query, answer)


def modo_admin(args, embedder, collection) -> None:
    if args.add:
        add_document(args.add, collection, embedder)

    elif args.delete:
        try:
            delete_example(args.delete, collection)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

    elif args.stats:
        total = collection.count()
        print(f"Chunks indexados en ChromaDB: {total}")

    else:
        print("Modo admin: use --add <archivo>, --delete <id> o --stats.")


# ---------------------------------------------------------------------------
# Entrada principal
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Asistente DRC para errores de diseño VLSI (XFAB XH018)."
    )
    parser.add_argument(
        "--add",
        metavar="ARCHIVO",
        help="Agrega un documento al corpus (modo admin).",
    )
    parser.add_argument(
        "--delete",
        metavar="ID",
        help="Elimina un chunk del corpus por su ID SHA-1 (modo admin).",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Muestra estadísticas del corpus (modo admin).",
    )
    parser.add_argument(
        "--model",
        default=EMBEDDING_MODEL,
        metavar="MODELO",
        help=f"Modelo de embeddings a usar (default: {EMBEDDING_MODEL}).",
    )
    args = parser.parse_args()

    print("Cargando modelo de embeddings...")
    try:
        embedder = load_embedding_model(args.model)
    except Exception as e:
        print(f"Error al cargar el modelo de embeddings: {e}")
        sys.exit(1)

    print("Conectando a ChromaDB...")
    try:
        collection = init_vector_store(CHROMA_PATH)
    except Exception as e:
        print(f"Error al inicializar ChromaDB: {e}")
        sys.exit(1)

    if args.add or args.delete or args.stats:
        modo_admin(args, embedder, collection)
    else:
        modo_consulta(embedder, collection)


if __name__ == "__main__":
    main()
