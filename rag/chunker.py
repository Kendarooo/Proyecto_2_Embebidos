import json
import os

from pypdf import PdfReader


def load_document(file_path: str) -> str:
    """
    Supports .pdf, .txt, .md and .json files.
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

    if ext == ".pdf":
        return _pdf_to_text(file_path)

    raise ValueError(f"Formato no soportado: '{ext}'. Use .pdf, .txt, .md o .json")


def load_chunks(file_path: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """
    Carga y trocea un documento.
    JSON: un chunk por regla/ejemplo para evitar mezcla de reglas.
    Otros formatos: sliding window por caracteres.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".json":
        return _load_json_chunks(file_path)
    return chunk_text(load_document(file_path), chunk_size=chunk_size, overlap=overlap)


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

def _pdf_to_text(file_path: str) -> str:
    reader = PdfReader(file_path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(p.strip() for p in pages if p.strip())


def _json_to_text(data) -> str:
    """
    Convierte JSON DRC a texto plano para embedding.
    Soporta tres formatos:
      - Lista de ejemplos anotados (error_raw, celda, ...)
      - Objeto wrapper con clave "rules" (code, section, solution_es, ...)
      - Ejemplo anotado individual (dict)
    """
    if isinstance(data, list):
        return "\n\n".join(_example_to_text(item) for item in data if isinstance(item, dict))

    if isinstance(data, dict):
        if "rules" in data and isinstance(data["rules"], list):
            return "\n\n".join(_rule_to_text(r) for r in data["rules"] if isinstance(r, dict))
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


def _rule_to_text(rule: dict) -> str:
    aliases = rule.get("layer_aliases", [])
    typical_queries = rule.get("typical_queries_es", [])
    fields = [
        ("Código", rule.get("code", "")),
        ("Sección", rule.get("section", "")),
        ("Descripción", rule.get("description_en", "")),
        ("Descripción ES", rule.get("description_es", "")),
        ("Aliases de capa", ", ".join(aliases) if isinstance(aliases, list) else aliases),
        ("Valor", f"{rule.get('value', '')} {rule.get('unit', '')}".strip()),
        ("Tipo", rule.get("rule_type", "")),
        (
            "Consultas típicas",
            "; ".join(typical_queries) if isinstance(typical_queries, list) else typical_queries,
        ),
        ("Solución", rule.get("solution_es", "")),
    ]
    return "\n".join(f"{label}: {value}" for label, value in fields if value)


def _load_json_chunks(file_path: str) -> list[str]:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return [_example_to_text(item) for item in data if isinstance(item, dict) if _example_to_text(item).strip()]

    if isinstance(data, dict):
        if "rules" in data and isinstance(data["rules"], list):
            return [_rule_to_text(r) for r in data["rules"] if isinstance(r, dict) if _rule_to_text(r).strip()]
        text = _example_to_text(data)
        return [text] if text.strip() else []

    raise ValueError("El JSON debe ser un objeto o una lista de objetos")
