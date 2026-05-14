import hashlib

from sentence_transformers import SentenceTransformer
from chromadb.api.models.Collection import Collection

from rag.chunker import load_document, chunk_text
from rag.embeddings import generate_embedding
from rag.vector_store import index_chunks


def add_document(
    file_path: str,
    collection: Collection,
    embedder: SentenceTransformer,
    chunk_size: int = 512,
    overlap: int = 64,
) -> None:
    """
    Carga un documento, lo trocea, genera embeddings e indexa en ChromaDB.
    Chunks duplicados (mismo SHA-1) se omiten automáticamente.
    """
    text = load_document(file_path)
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)

    if not chunks:
        print(f"Advertencia: el documento '{file_path}' no produjo chunks.")
        return

    embeddings = [generate_embedding(chunk, embedder) for chunk in chunks]
    index_chunks(chunks, embeddings, collection)
    print(f"Indexados {len(chunks)} chunks de '{file_path}'.")


def update_example(
    example_id: str,
    new_content: str,
    collection: Collection,
    embedder: SentenceTransformer,
) -> None:
    """
    Reemplaza un chunk existente por nuevo contenido.
    example_id es el SHA-1 del chunk original (retornado al indexar).
    El nuevo chunk recibe un nuevo ID basado en su propio contenido.
    """
    existing = collection.get(ids=[example_id])
    if not existing["ids"]:
        raise ValueError(f"No existe ningún chunk con ID '{example_id}'.")

    collection.delete(ids=[example_id])

    new_content = new_content.strip()
    new_id = hashlib.sha1(new_content.encode("utf-8")).hexdigest()
    new_embedding = generate_embedding(new_content, embedder)

    collection.add(
        ids=[new_id],
        embeddings=[new_embedding],
        documents=[new_content],
    )
    print(f"Chunk actualizado. Nuevo ID: {new_id}")


def delete_example(example_id: str, collection: Collection) -> None:
    """
    Elimina un chunk de la colección por su ID (SHA-1).
    """
    existing = collection.get(ids=[example_id])
    if not existing["ids"]:
        raise ValueError(f"No existe ningún chunk con ID '{example_id}'.")

    collection.delete(ids=[example_id])
    print(f"Chunk '{example_id}' eliminado.")
