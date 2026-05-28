# Gold standard del asistente DRC

Este directorio contiene casos dorados para evaluar el asistente RAG sin modificar
la lógica del sistema. Los casos describen entradas esperadas y criterios de
verificación; no entrenan, ajustan ni cambian el pipeline.

Antes de usar los casos `exact_rule_indexed`, valida que el ChromaDB activo tenga
indexados los documentos correctos:

```bash
uv run python main.py --stats
uv run python eval_validate_gold.py
```

El gold standard actual asume que están indexados estos archivos:

- `corpus/raw/xh018-DR-v10_1_1.txt`
- `corpus/annotated/xh018_drc_solutions_only_txt_codes.json`

Categorias usadas:

- `exact_rule_indexed`: código confirmado en el ChromaDB activo y parseable por
  la ruta de regla exacta sin llamar a Ollama.
- `semantic_only`: consulta en lenguaje natural que depende de recuperación
  semántica.
- `missing_code`: código con forma válida, pero intencionalmente no indexado.
- `out_of_scope`: consulta fuera del dominio DRC XFAB XH018.
- `conversational`: saludo, ayuda, agradecimiento o despedida que debe responder
  sin usar RAG ni Ollama.
