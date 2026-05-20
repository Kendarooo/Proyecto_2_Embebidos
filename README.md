# Asistente DRC VLSI — BitBakers

Sistema RAG (Retrieval-Augmented Generation) de borde para asistir a estudiantes del curso Diseño mediante VLSI del Instituto Tecnológico de Costa Rica en la interpretación y corrección de errores DRC generados en Cadence Virtuoso con el PDK XFAB XH018 (180nm). Opera completamente de forma local sobre una NVIDIA Jetson Nano 4GB, sin conexión a internet ni dependencia de servicios externos.

---

## Descripción del sistema

Cuando el estudiante encuentra un error DRC en el log de Calibre/Pegasus, lo ingresa en la interfaz de terminal del asistente en lenguaje natural. El pipeline RAG genera el embedding de la consulta, recupera los fragmentos más relevantes del corpus DRC indexado en ChromaDB y construye un prompt aumentado que envía al modelo de lenguaje local (gemma3:4b via Ollama). El sistema responde con la explicación del error y los pasos específicos para corregirlo en Cadence Virtuoso.

```
Consulta del estudiante
        ↓
  Embedding (all-MiniLM-L6-v2, CPU)
        ↓
  Búsqueda semántica en ChromaDB
        ↓
  Prompt aumentado (contexto + consulta)
        ↓
  Inferencia local (gemma3:4b via Ollama)
        ↓
  Respuesta en terminal (explicación + pasos de corrección)
```

### Dominio delimitado

| Atributo | Valor |
|---|---|
| PDK | XFAB XH018 (180nm) |
| Celdas | NOT, AND, NOR |
| Capas | Metal1–Metal5, Poly, Ndiff, Pdiff, Contact, Via1–Via4 |
| Tipos de error | Spacing, Width, Enclosure, Extension/Overlap, Via/Contact |
| Fuera de scope | Antenna rules, LVS, Density global, Well rules, Notch |

Las consultas fuera del dominio son notificadas explícitamente al usuario.

---

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Hardware | NVIDIA Jetson Nano 4GB |
| Sistema operativo | Linux ARM64 via Yocto Project |
| LLM | gemma3:4b via Ollama (`http://localhost:11434`) |
| Embeddings | all-MiniLM-L6-v2 (sentence-transformers, ~80MB, CPU) |
| Vector store | ChromaDB persistente en disco (`data/chroma_db/`) |
| Interfaz | Terminal CLI |
| Lenguaje | Python 3 |

---

## Estructura del proyecto

```
Proyecto_2_Embebidos/
├── rag/
│   ├── chunker.py          # Módulo 1 — carga y troceado de documentos
│   ├── embeddings.py       # Módulo 2 — modelo de embeddings
│   ├── vector_store.py     # Módulo 3 — ChromaDB
│   ├── pipeline.py         # Módulo 4 — orquestador RAG
│   └── corpus_admin.py     # Módulo 5 — gestión del corpus
├── corpus/
│   ├── raw/                # Documentos fuente (PDFs, TXTs del PDK)
│   └── annotated/          # Ejemplos anotados en JSON
├── data/
│   └── chroma_db/          # Base de datos vectorial (NO versionar)
├── docs/                   # Propuesta de diseño y documentación
├── logs/                   # Logs de consultas con timestamp (NO versionar)
├── pyproject.toml
└── main.py                 # Punto de entrada CLI
```

---

## Requisitos previos

- Python 3.10+
- [Ollama](https://ollama.com) instalado y corriendo como servicio local
- Modelo `gemma3:4b` descargado en Ollama

```bash
# Verificar que Ollama está corriendo
ollama list

# Descargar el modelo si no está instalado
ollama pull gemma3:4b
```

---

## Instalación

```bash
# Clonar el repositorio
git clone <url-del-repositorio>
cd Proyecto_2_Embebidos

# Instalar dependencias Python
pip install -r requirements.txt
```

---

## Uso

### Modo consulta (estudiante)

```bash
python main.py
```

El sistema carga el modelo de embeddings, conecta a ChromaDB e inicia un prompt interactivo:

```
============================================================
  Asistente DRC — PDK XFAB XH018 (180nm)
  Celdas: NOT, AND, NOR
  Escribe 'salir' para terminar.
============================================================

Consulta DRC> METAL1_S: SPACE < 0.28, actual = 0.13um
```

Se puede ingresar el error tal como aparece en el log de Pegasus, o formularlo en lenguaje natural.

---

### Modo administración del corpus (asistente del curso)

#### Agregar un documento al corpus

```bash
python main.py --add corpus/raw/xh018-DR-v10_1_1.txt
python main.py --add corpus/raw/reglas_metal.pdf
python main.py --add corpus/annotated/not_drc_errors.json
```

Formatos soportados: `.txt`, `.pdf`, `.md`, `.json`

#### Ver estadísticas del corpus

```bash
python main.py --stats
# Chunks indexados en ChromaDB: 1243
```

#### Eliminar todos los chunks de un documento

```bash
python main.py --remove corpus/raw/xh018-DR-v10_1_1.txt
```

#### Eliminar un chunk individual por ID

```bash
python main.py --delete a3f2c1d9e8b7...
```

El ID SHA-1 de cada chunk se puede obtener consultando ChromaDB directamente o de los logs de indexación.

#### Usar un modelo de embeddings alternativo

```bash
python main.py --model /opt/models/all-MiniLM-L6-v2
```

Útil en Jetson Nano para apuntar a la ruta local del modelo pre-descargado.

---

## Formato del corpus anotado (JSON)

Los ejemplos anotados en `corpus/annotated/` deben seguir este esquema:

```json
{
  "error_raw": "METAL1_S: SPACE < 0.28, actual = 0.13um",
  "celda": "NOT",
  "capa": "Metal1",
  "tipo": "Spacing",
  "explicacion": "El espacio entre dos trazos de Metal1 es menor al mínimo permitido por el PDK (0.28µm).",
  "correccion": "Aumentar la separación entre los trazos en el layout editor de Virtuoso hasta cumplir el mínimo.",
  "error_comun": "Ocurre al compactar el layout manualmente sin verificar las design rules del PDK."
}
```

También se acepta un archivo JSON con una lista de objetos con el mismo esquema.

---

## Requerimientos del sistema

| ID | Requerimiento |
|---|---|
| NFR-01 | Tiempo de respuesta máximo: 60 segundos |
| NFR-02 | Operación completamente offline (sin internet en producción) |
| NFR-03 | Consumo máximo de memoria RAM: 4GB |
| NFR-04 | Precisión mínima dentro del dominio: 80% |
| NFR-06 | Privacidad total — ningún dato sale del dispositivo |

---

## Fases de despliegue

El sistema se despliega en tres fases:

1. **Compilación Yocto** — en máquina de desarrollo, genera la imagen Linux ARM64 para la Jetson Nano (~2–4 horas en primera compilación).
2. **Post-despliegue en Jetson Nano** — única vez con internet: `ollama pull gemma3:4b` + `pip install -r requirements.txt` + indexación del corpus DRC.
3. **Operación en laboratorio** — completamente offline. El estudiante consulta, el sistema responde.

---

## Entregas

| Fecha | Entrega |
|---|---|
| 2026-05-25 | Bitácoras + repositorio GitHub completo |
| 2026-06-01 | Demostración final presencial en Jetson Nano |
