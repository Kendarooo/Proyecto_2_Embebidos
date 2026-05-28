#!/usr/bin/env python3
"""
Evalua recuperacion contra el gold standard.

No llama a Ollama y no modifica la logica del asistente. Mide si el ChromaDB
activo recupera los chunks esperados mediante busqueda semantica, keyword y la
combinacion aproximada que usa el pipeline.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from rag.embeddings import generate_embedding, load_embedding_model
from rag.pipeline import _extract_rule_codes
from rag.vector_store import init_vector_store, search_by_keyword, search_relevant_chunks


ROOT = Path(__file__).resolve().parent
GOLD_PATH = ROOT / "tests" / "golden" / "drc_eval_cases.json"
CHROMA_PATH = ROOT / "data" / "chroma_db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def _load_cases() -> list[dict]:
    with GOLD_PATH.open("r", encoding="utf-8") as f:
        cases = json.load(f)
    if not isinstance(cases, list):
        raise ValueError("El gold standard debe ser una lista de casos.")
    return cases


def _contains_all(chunks: list[str], needles: list[str]) -> bool:
    text = "\n".join(chunks).lower()
    return all(needle.lower() in text for needle in needles)


def _dedupe(chunks: list[str]) -> list[str]:
    seen = set()
    unique = []
    for chunk in chunks:
        if chunk in seen:
            continue
        seen.add(chunk)
        unique.append(chunk)
    return unique


def _pct(ok: int, total: int) -> str:
    if total == 0:
        return "n/a"
    return f"{ok / total * 100:.1f}%"


def main() -> int:
    os.environ["ANONYMIZED_TELEMETRY"] = "False"

    cases = [
        case
        for case in _load_cases()
        if case.get("category") in {"exact_rule_indexed", "semantic_only"}
    ]

    collection = init_vector_store(str(CHROMA_PATH))
    if collection.count() == 0:
        print("Error: ChromaDB no tiene chunks indexados.")
        return 1

    print(f"Gold standard: {GOLD_PATH}")
    print(f"Chunks en ChromaDB: {collection.count()}")
    print(f"Casos retrieval: {len(cases)}")
    print("Cargando modelo de embeddings...")
    embedder = load_embedding_model(EMBEDDING_MODEL)
    print()

    keyword_total = 0
    keyword_ok = 0
    semantic3_ok = 0
    semantic5_ok = 0
    combined3_ok = 0
    combined5_ok = 0
    failures: list[str] = []
    started = time.perf_counter()

    for case in cases:
        case_id = case["id"]
        query = case["query"]
        must_retrieve = case.get("must_retrieve", [])

        rule_codes = _extract_rule_codes(query)
        keyword_chunks = []
        for code in rule_codes:
            keyword_chunks.extend(search_by_keyword(code, collection, n=8))
        keyword_chunks = _dedupe(keyword_chunks)

        if case.get("category") == "exact_rule_indexed":
            keyword_total += 1
            if _contains_all(keyword_chunks, must_retrieve):
                keyword_ok += 1
            else:
                failures.append(f"{case_id}: keyword no recupero {must_retrieve}.")

        query_embedding = generate_embedding(query, embedder)
        semantic5 = search_relevant_chunks(query_embedding, collection, n=5)
        semantic3 = semantic5[:3]

        combined5 = _dedupe(keyword_chunks + semantic5)[:5]
        combined3 = combined5[:3]

        if _contains_all(semantic3, must_retrieve):
            semantic3_ok += 1
        if _contains_all(semantic5, must_retrieve):
            semantic5_ok += 1
        else:
            failures.append(f"{case_id}: semantico@5 no recupero {must_retrieve}.")
        if _contains_all(combined3, must_retrieve):
            combined3_ok += 1
        if _contains_all(combined5, must_retrieve):
            combined5_ok += 1
        else:
            failures.append(f"{case_id}: combinado@5 no recupero {must_retrieve}.")

    total = len(cases)
    elapsed = time.perf_counter() - started

    print("Resultados de recuperacion")
    print(f"  Keyword hit:          {keyword_ok}/{keyword_total} = {_pct(keyword_ok, keyword_total)}")
    print(f"  Recall semantico@3:   {semantic3_ok}/{total} = {_pct(semantic3_ok, total)}")
    print(f"  Recall semantico@5:   {semantic5_ok}/{total} = {_pct(semantic5_ok, total)}")
    print(f"  Recall combinado@3:   {combined3_ok}/{total} = {_pct(combined3_ok, total)}")
    print(f"  Recall combinado@5:   {combined5_ok}/{total} = {_pct(combined5_ok, total)}")
    print(f"  Tiempo total:         {elapsed:.1f}s")
    print()

    if failures:
        print("Casos a revisar:")
        for failure in failures:
            print(f"  - {failure}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
