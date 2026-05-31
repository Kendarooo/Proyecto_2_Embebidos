import re
import requests
from sentence_transformers import SentenceTransformer
from chromadb.api.models.Collection import Collection

from rag.embeddings import generate_embedding
from rag.vector_store import search_relevant_chunks, search_by_keyword

_RULE_CODE_RE = re.compile(r'\b([A-Z][A-Z0-9]{2,7})\b')

MODEL_NAME = "phi4-mini"
OUT_OF_SCOPE_MARKER = "[FUERA_DE_ALCANCE]"

_GREETINGS = {"hola", "hi", "hey", "buenas", "buenos días", "buenas tardes", "buenas noches", "buen día"}
_HELP_TRIGGERS = {"ayuda", "help", "qué puedes hacer", "que puedes hacer", "para qué sirves", "para que sirves", "cómo funciona", "como funciona"}
_THANKS_TRIGGERS = {"gracias", "thanks", "thank you", "perfecto", "listo", "ok", "entendido", "vale"}
_FAREWELL_TRIGGERS = {
    "adiós",
    "adios",
    "hasta luego",
    "hasta pronto",
    "hasta mañana",
    "nos vemos",
    "bye",
    "goodbye",
    "chao",
    "chau",
    "me voy",
}

_SYSTEM_CONTEXT = """Eres un asistente especializado en errores DRC del PDK XFAB XH018 (180nm).
Ayudas a estudiantes de VLSI del TEC a entender y corregir errores DRC generados en Cadence Virtuoso.
Puedes responder sobre cualquier regla DRC del PDK XFAB XH018, incluyendo reglas de Metal, Poly, Difusión, Contactos, Vías, NWELL, PWELL y otras capas del proceso.
Los tipos de error que conoces son: Spacing, Width, Enclosure, Extension/Overlap, Área mínima y reglas de Via/Contact.
Responde siempre en español, de forma clara y directa."""

_PROMPT_TEMPLATE = """{system}

Información relevante del corpus DRC:
{context}

Pregunta del estudiante:
{query}

Si la pregunta no tiene nada que ver con errores DRC del PDK XFAB XH018, \
responde únicamente con: {marker}

Si la pregunta incluye un código de regla exacto, prioriza cualquier bloque marcado como
"Regla exacta encontrada". No infieras la capa, sección ni valor desde líneas cercanas
o desde otra regla con código parecido.

De lo contrario, usando la información del corpus como base, responde con:
1. Qué significa el código de error (capa afectada, tipo de violación, valor mínimo o máximo requerido).
2. Por qué ocurre este error en el diseño de la celda.
3. Cómo corregirlo paso a paso en Cadence Virtuoso."""


def _conversational_response(user_query: str) -> str | None:
    normalized = user_query.strip().lower().rstrip("!?.,")
    if normalized in _FAREWELL_TRIGGERS or any(t in normalized for t in _FAREWELL_TRIGGERS):
        return (
            "Hasta luego. Cuando tengas otro error DRC del PDK XFAB XH018, "
            "puedes volver y lo revisamos paso a paso.\n"
            "Escribe 'Salir' para terminar el chat."
        )
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
            "- Capas: Metal1–Metal5, Poly, Ndiff, Pdiff, Contact, Via1–Via4\n"
            "- Celdas: NOT, AND, NOR\n"
            "Pega el mensaje de error de Pegasus y te explico qué significa y cómo corregirlo.\n"
            "Escribe 'Salir' para terminar el chat."
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


def _extract_rule_codes(user_query: str) -> list[str]:
    codes = [c for c in _RULE_CODE_RE.findall(user_query.upper()) if any(ch.isdigit() for ch in c)]
    return list(dict.fromkeys(codes))


def _extract_exact_rule_snippet(code: str, chunk: str) -> str | None:
    lines = [line.strip() for line in chunk.splitlines() if line.strip()]

    for index, line in enumerate(lines):
        if re.fullmatch(rf"Código:\s*{re.escape(code)}", line, flags=re.IGNORECASE):
            return "\n".join(lines[index:])

        if re.match(rf"^{re.escape(code)}\s*\|", line, flags=re.IGNORECASE):
            return line

    return None


def _build_exact_rule_context(code: str, keyword_chunks: list[str]) -> list[str]:
    exact_context = []
    seen = set()

    for chunk in keyword_chunks:
        snippet = _extract_exact_rule_snippet(code, chunk)
        if not snippet or snippet in seen:
            continue

        seen.add(snippet)
        exact_context.append(f"Regla exacta encontrada para {code}:\n{snippet}")

    return exact_context


def _parse_exact_rule(code: str, keyword_chunks: list[str]) -> dict[str, str] | None:
    raw_fallback = None

    for chunk in keyword_chunks:
        snippet = _extract_exact_rule_snippet(code, chunk)
        if not snippet:
            continue

        parsed = _parse_structured_rule(code, snippet)
        if parsed:
            return parsed

        raw_fallback = raw_fallback or _parse_table_rule(code, snippet)

    return raw_fallback


def _parse_structured_rule(code: str, snippet: str) -> dict[str, str] | None:
    fields = {}
    for line in snippet.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip().lower()] = value.strip()

    if fields.get("código", "").upper() != code:
        return None

    description = fields.get("descripción", "")
    return {
        "code": code,
        "affected": _affected_from_description(description) or fields.get("sección", "la capa indicada"),
        "description": description,
        "value": fields.get("valor", "no especificado"),
        "rule_type": fields.get("tipo", _rule_type_from_description(description)),
        "solution": _clean_solution(fields.get("solución", "")),
    }


def _parse_table_rule(code: str, snippet: str) -> dict[str, str] | None:
    parts = [part.strip() for part in snippet.split("|")]
    if len(parts) < 4 or parts[0].upper() != code:
        return None

    description = parts[1]
    value = f"{parts[2]} {parts[3]}".strip()
    rule_type = _rule_type_from_description(description)
    return {
        "code": code,
        "affected": _affected_from_description(description) or "la capa indicada",
        "description": description,
        "value": value,
        "rule_type": rule_type,
        "solution": _default_solution_for_rule(rule_type, value),
    }


def _affected_from_description(description: str) -> str:
    match = re.search(
        r"\b(?:Minimum|Maximum)\s+(.+?)\s+"
        r"(?:area|width|spacing/notch|spacing|enclosure|extension|ratio)\b",
        description,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    affected = re.sub(r"\s*\(.*?\)\s*", " ", match.group(1)).strip()
    return affected or ""


def _rule_type_from_description(description: str) -> str:
    lowered = description.lower()
    qualifier = "máxima" if "maximum" in lowered else "mínima"

    if "area" in lowered:
        return f"área {qualifier}"
    if "width" in lowered:
        return f"anchura {qualifier}"
    if "spacing" in lowered or "notch" in lowered:
        return f"espaciado {qualifier}"
    if "enclosure" in lowered:
        return f"encerramiento {qualifier}"
    if "extension" in lowered or "overlap" in lowered:
        return f"extensión/solape {qualifier}"
    if "ratio" in lowered:
        return f"relación {qualifier}"
    return "regla DRC"


def _default_solution_for_rule(rule_type: str, value: str) -> str:
    if "área" in rule_type:
        return f"Aumenta el área de la figura marcada hasta cumplir {value}."
    if "anchura" in rule_type:
        return f"Aumenta el ancho de la geometría marcada hasta cumplir {value}."
    if "espaciado" in rule_type:
        return f"Aumenta la separación indicada hasta cumplir {value}."
    if "encerramiento" in rule_type:
        return f"Ajusta la capa que encierra la geometría marcada hasta cumplir {value}."
    if "extensión" in rule_type or "solape" in rule_type:
        return f"Ajusta la extensión o el solape indicado hasta cumplir {value}."
    return "Corrige la geometría marcada según el valor requerido y vuelve a ejecutar DRC."


def _clean_solution(solution: str) -> str:
    return re.sub(r"(\S)\(", r"\1 (", solution.strip())


def _format_exact_rule_answer(rule: dict[str, str]) -> str:
    code = rule["code"]
    affected = rule["affected"]
    rule_type = rule["rule_type"]
    value = rule["value"]
    solution = rule["solution"] or _default_solution_for_rule(rule_type, value)

    return (
        f"1. Significado del código de error:\n"
        f"   - Código: {code}\n"
        f"   - Capa/región afectada: {affected}\n"
        f"   - Tipo de violación: {rule_type}\n"
        f"   - Valor requerido: {value}\n\n"
        f"2. Por qué ocurre este error en el diseño:\n"
        f"   El marcador {code} indica que una geometría de {affected} no cumple la regla "
        f"de {rule_type} definida por el PDK XFAB XH018.\n\n"
        f"3. Cómo corregirlo en Cadence Virtuoso:\n"
        f"   - Localiza el marcador DRC {code} en el layout.\n"
        f"   - Identifica la geometría de {affected} señalada por el marcador.\n"
        f"   - {solution}\n"
        f"   - Revisa que el cambio no cree nuevas violaciones de spacing, enclosure u overlap.\n"
        f"   - Guarda el layout y vuelve a ejecutar DRC."
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

    rule_codes = _extract_rule_codes(user_query)
    keyword_chunks_by_code = {}

    for code in rule_codes:
        keyword_chunks = search_by_keyword(code, collection, n=8)
        keyword_chunks_by_code[code] = keyword_chunks
        exact_rule = _parse_exact_rule(code, keyword_chunks)
        if exact_rule:
            return _format_exact_rule_answer(exact_rule)

    query_embedding = generate_embedding(user_query, embedder)
    context_chunks = search_relevant_chunks(query_embedding, collection, n=3)

    for code in rule_codes:
        keyword_chunks = keyword_chunks_by_code[code]
        exact_context = _build_exact_rule_context(code, keyword_chunks)
        for exact_rule_context in reversed(exact_context):
            if exact_rule_context not in context_chunks:
                context_chunks.insert(0, exact_rule_context)

        for chunk in keyword_chunks:
            if chunk not in context_chunks and not _extract_exact_rule_snippet(code, chunk):
                context_chunks.append(chunk)

    prompt = build_prompt(context_chunks, user_query)
    answer = query_llm(prompt, llm_host)

    _OOS_RE = re.compile(r'[-–]?\s*\[?FUERA_DE_ALCANCE\]?', re.IGNORECASE)
    cleaned = _OOS_RE.sub("", answer).strip()
    marker_present = cleaned != answer.strip()

    if marker_present and len(cleaned) < 30:
        return (
            "Esta consulta está fuera del alcance del asistente.\n"
            "Solo puedo ayudar con errores DRC del PDK XFAB XH018."
        )

    return cleaned if marker_present else answer
