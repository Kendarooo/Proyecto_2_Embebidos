import json
import os


def load_document(file_path: str) -> str:
    """
    Supports .txt, .md and .json files.
    JSON annotated examples are serialized to a readable text block
    so they can be chunked and embedded like any other document.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No se encontró el archivo: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext in (".txt", ".md"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    if ext == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return _json_to_text(data)

    raise ValueError(f"Formato no soportado: '{ext}'. Use .txt, .md o .json")


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """
    Sliding-window chunker por caracteres.
    chunk_size: tamaño de cada chunk en caracteres
    overlap: cantidad de caracteres que se repiten entre chunks consecutivos
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size debe ser mayor que 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap debe estar en [0, chunk_size)")

    text = text.strip()
    if not text:
        return []

    chunks = []
    step = chunk_size - overlap
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += step

    return chunks


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _json_to_text(data) -> str:
    """
    Convierte un ejemplo anotado DRC (dict) o lista de ejemplos (list[dict])
    a texto plano estructurado para embedding.
    """
    if isinstance(data, list):
        return "\n\n".join(_example_to_text(item) for item in data if isinstance(item, dict))

    if isinstance(data, dict):
        return _example_to_text(data)

    raise ValueError("El JSON debe ser un objeto o una lista de objetos")


def _example_to_text(example: dict) -> str:
    fields = [
        ("Error DRC", example.get("error_raw", "")),
        ("Celda", example.get("celda", "")),
        ("Capa", example.get("capa", "")),
        ("Tipo", example.get("tipo", "")),
        ("Explicación", example.get("explicacion", "")),
        ("Corrección", example.get("correccion", "")),
        ("Error común", example.get("error_comun", "")),
    ]
    return "\n".join(f"{label}: {value}" for label, value in fields if value)
