#!/usr/bin/env python3
"""
Valida que el gold standard corresponda al ChromaDB activo.

No modifica la lógica del asistente ni escribe en la base vectorial. Su objetivo
es detectar casos dorados que apuntan a códigos no indexados o no parseables.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from rag.pipeline import _extract_rule_codes, _parse_exact_rule
from rag.vector_store import init_vector_store, search_by_keyword


ROOT = Path(__file__).resolve().parent
GOLD_PATH = ROOT / "tests" / "golden" / "drc_eval_cases.json"
CHROMA_PATH = ROOT / "data" / "chroma_db"


def _load_cases() -> list[dict]:
    with GOLD_PATH.open("r", encoding="utf-8") as f:
        cases = json.load(f)
    if not isinstance(cases, list):
        raise ValueError("El gold standard debe ser una lista de casos.")
    return cases


def _contains_all(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return all(needle.lower() in lowered for needle in needles)


def main() -> int:
    os.environ["ANONYMIZED_TELEMETRY"] = "False"

    cases = _load_cases()
    collection = init_vector_store(str(CHROMA_PATH))

    print(f"Gold standard: {GOLD_PATH}")
    print(f"Chunks en ChromaDB: {collection.count()}")
    print()

    failures: list[str] = []
    category_counts: dict[str, int] = {}

    for case in cases:
        case_id = case.get("id", "<sin id>")
        category = case.get("category", "<sin categoria>")
        category_counts[category] = category_counts.get(category, 0) + 1

        if category == "exact_rule_indexed":
            expected_code = case.get("expected_code")
            if not expected_code:
                failures.append(f"{case_id}: falta expected_code.")
                continue

            extracted = _extract_rule_codes(case.get("query", ""))
            if expected_code not in extracted:
                failures.append(
                    f"{case_id}: la query no extrae {expected_code}; extrae {extracted}."
                )

            keyword_hits = search_by_keyword(expected_code, collection, n=8)
            if not keyword_hits:
                failures.append(f"{case_id}: {expected_code} no tiene hits por keyword.")
                continue

            combined_text = "\n".join(keyword_hits)
            if not _contains_all(combined_text, case.get("must_retrieve", [])):
                failures.append(
                    f"{case_id}: keyword hits no contienen must_retrieve={case.get('must_retrieve', [])}."
                )

            parsed = _parse_exact_rule(expected_code, keyword_hits)
            if not parsed:
                failures.append(f"{case_id}: {expected_code} no es parseable como regla exacta.")
                continue

            expected_value = case.get("expected_value")
            if expected_value and expected_value not in parsed.get("value", ""):
                failures.append(
                    f"{case_id}: valor parseado {parsed.get('value')!r} no contiene {expected_value!r}."
                )

            expected_affected = case.get("expected_affected")
            if expected_affected and expected_affected.lower() not in parsed.get("affected", "").lower():
                failures.append(
                    f"{case_id}: affected parseado {parsed.get('affected')!r} no contiene {expected_affected!r}."
                )

        elif category == "missing_code":
            expected_code = case.get("expected_code")
            if not expected_code:
                failures.append(f"{case_id}: falta expected_code.")
                continue
            keyword_hits = search_by_keyword(expected_code, collection, n=3)
            if keyword_hits:
                failures.append(
                    f"{case_id}: {expected_code} era missing_code, pero tiene {len(keyword_hits)} hits."
                )

        elif category in {"semantic_only", "out_of_scope", "conversational"}:
            continue

        else:
            failures.append(f"{case_id}: categoria desconocida {category!r}.")

    print("Casos por categoria:")
    for category, count in sorted(category_counts.items()):
        print(f"  {category}: {count}")
    print()

    if failures:
        print("Validacion: FALLA")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("Validacion: OK")
    print("Los casos exact_rule_indexed son recuperables y parseables en el ChromaDB activo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
