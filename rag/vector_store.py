import hashlib

import chromadb
from chromadb.api.models.Collection import Collection


def init_vector_store(path: str) -> Collection:
    """
    Inicializa ChromaDB persistente en disco.
    Si ya existe la colección, la retorna tal cual — los chunks previos se conservan.
    """
    client = chromadb.PersistentClient(path=path)
    collection = client.get_or_create_collection(
        name="drc_corpus",
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def index_chunks(
    chunks: list[str],
    embeddings: list[list[float]],
    collection: Collection,
) -> None:
    """
    Inserta chunks con sus embeddings en la colección.
    El ID de cada chunk es un hash SHA-1 de su texto para evitar duplicados
    si el mismo documento se indexa más de una vez.
    """
    if len(chunks) != len(embeddings):
        raise ValueError("chunks y embeddings deben tener el mismo largo")

    ids = [_chunk_id(chunk) for chunk in chunks]

    existing = set(collection.get(ids=ids)["ids"])
    new_indices = [i for i, id_ in enumerate(ids) if id_ not in existing]

    if not new_indices:
        return

    collection.add(
        ids=[ids[i] for i in new_indices],
        embeddings=[embeddings[i] for i in new_indices],
        documents=[chunks[i] for i in new_indices],
    )


def search_relevant_chunks(
    query_embedding: list[float],
    collection: Collection,
    n: int = 3,
) -> list[str]:
    """
    Retorna los n chunks más similares al embedding de la consulta.
    Devuelve lista vacía si la colección está vacía.
    """
    if collection.count() == 0:
        return []

    n = min(n, collection.count())
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n,
        include=["documents"],
    )
    return results["documents"][0]


# ---------------------------------------------------------------------------

def _chunk_id(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()
