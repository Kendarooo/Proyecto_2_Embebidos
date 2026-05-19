import requests
from sentence_transformers import SentenceTransformer
from chromadb.api.models.Collection import Collection

from rag.embeddings import generate_embedding
from rag.vector_store import search_relevant_chunks

MODEL_NAME = "gemma3:4b"
OUT_OF_SCOPE_MARKER = "[FUERA_DE_ALCANCE]"

_GREETINGS = {"hola", "hi", "hey", "buenas", "buenos días", "buenas tardes", "buenas noches", "buen día"}
_HELP_TRIGGERS = {"ayuda", "help", "qué puedes hacer", "que puedes hacer", "para qué sirves", "para que sirves", "cómo funciona", "como funciona"}
_THANKS_TRIGGERS = {"gracias", "thanks", "thank you", "perfecto", "listo", "ok", "entendido", "vale"}

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


def _conversational_response(user_query: str) -> str | None:
    normalized = user_query.strip().lower().rstrip("!?.,")
    if normalized in _GREETINGS or any(normalized.startswith(g) for g in _GREETINGS):
        return (
            "¡Hola! Soy el asistente DRC para el PDK XFAB XH018 (180nm).\n"
            "Puedo ayudarte a entender y corregir errores DRC en tus diseños de celdas "
            "NOT, AND y NOR en Cadence Virtuoso.\n"
            "Describe el error que estás viendo en Pegasus y te explico la causa y cómo resolverlo."
        )
    if any(t in normalized for t in _HELP_TRIGGERS):
        return (
            "Puedo ayudarte con errores DRC del PDK XFAB XH018 (180nm) en Cadence Virtuoso.\n"
            "- Tipos de error: Spacing, Width, Enclosure, Extension/Overlap, Via/Contact\n"
            "- Capas: Metal1–Metal4, Poly, Ndiff, Pdiff, Contact, Via1–Via3\n"
            "- Celdas: NOT, AND, NOR\n"
            "Pega el mensaje de error de Pegasus y te explico qué significa y cómo corregirlo."
        )
    if any(t in normalized for t in _THANKS_TRIGGERS):
        return "¡Con gusto! Si tienes otro error DRC, aquí estoy."
    return None


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
    conversational = _conversational_response(user_query)
    if conversational:
        return conversational

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
