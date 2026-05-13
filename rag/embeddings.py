from sentence_transformers import SentenceTransformer


def load_embedding_model(model_name: str) -> SentenceTransformer:
    """
    Carga el modelo desde disco local. model_name puede ser:
      - nombre estándar:  "all-MiniLM-L6-v2"
      - ruta absoluta:    "/opt/models/all-MiniLM-L6-v2"
    En Jetson Nano sin internet se pasa la ruta local al modelo pre-descargado.
    device="cpu" forzado para no depender de CUDA en el pipeline de embeddings.
    """
    return SentenceTransformer(model_name, device="cpu")


def generate_embedding(text: str, model: SentenceTransformer) -> list[float]:
    """
    Retorna el embedding de un texto como lista de floats.
    normalize_embeddings=True mejora la búsqueda por similitud coseno en ChromaDB.
    """
    if not text or not text.strip():
        raise ValueError("El texto para embedding no puede estar vacío")

    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()
