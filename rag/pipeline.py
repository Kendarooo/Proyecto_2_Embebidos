import requests
from sentence_transformers import SentenceTransformer
from chromadb.api.models.Collection import Collection

from rag.embeddings import generate_embedding
from rag.vector_store import search_relevant_chunks

MODEL_NAME = "phi3"
OUT_OF_SCOPE_MARKER = "[FUERA_DE_ALCANCE]"

_SYSTEM_CONTEXT = """Eres un asistente especializado en errores DRC del PDK XFAB XH018 (180nm).
Ayudas a estudiantes de VLSI del TEC a entender y corregir errores DRC generados en Cadence Virtuoso.
Tu dominio está limitado a las celdas NOT, AND y NOR, y a las capas Metal1-Metal4, Poly, Ndiff, Pdiff, Contact, Via1-Via3.
Los tipos de error que conoces son: Spacing, Width, Enclosure, Extension/Overlap y reglas de Via/Contact.
Responde siempre en español, de forma clara y directa."""

_PROMPT_TEMPLATE = """{system}

Información relevante del corpus DRC:
{context}

Pregunta del estudiante:
{query}

Si la pregunta está fuera de tu dominio (no es un error DRC del PDK XFAB XH018 para las celdas y capas indicadas), \
responde únicamente con: {marker}

De lo contrario, explica el error y cómo corregirlo."""


def build_prompt(context_chunks: list[str], user_query: str) -> str:
    context = "\n---\n".join(context_chunks) if context_chunks else "Sin contexto disponible."
    return _PROMPT_TEMPLATE.format(
        system=_SYSTEM_CONTEXT,
        context=context,
        query=user_query.strip(),
        marker=OUT_OF_SCOPE_MARKER,
    )


def query_llm(prompt: str, host: str) -> str:
    """
    Llama a Ollama en el host indicado (ej. "http://localhost:11434").
    stream=False para esperar la respuesta completa antes de retornar.
    """
    url = f"{host.rstrip('/')}/api/generate"
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
    }

    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()["response"].strip()
    except requests.exceptions.ConnectionError:
        return "Error: no se pudo conectar con Ollama. Verifique que el servicio esté corriendo."
    except requests.exceptions.Timeout:
        return "Error: el modelo tardó demasiado en responder. Intente de nuevo."
    except (requests.exceptions.HTTPError, KeyError) as e:
        return f"Error al consultar el modelo: {e}"


def process_query(
    user_query: str,
    collection: Collection,
    embedder: SentenceTransformer,
    llm_host: str,
) -> str:
    """
    Orquesta el pipeline completo:
      1. Embed de la consulta
      2. Búsqueda de chunks relevantes en ChromaDB
      3. Construcción del prompt aumentado
      4. Inferencia con Ollama
      5. Detección de fuera de alcance
    """
    query_embedding = generate_embedding(user_query, embedder)
    context_chunks = search_relevant_chunks(query_embedding, collection, n=3)
    prompt = build_prompt(context_chunks, user_query)
    answer = query_llm(prompt, llm_host)

    if OUT_OF_SCOPE_MARKER in answer:
        return (
            "Esta consulta está fuera del alcance del asistente.\n"
            "Solo puedo ayudar con errores DRC del PDK XFAB XH018 para las celdas NOT, AND y NOR."
        )

    return answer
