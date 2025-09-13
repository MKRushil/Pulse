# -*- coding: utf-8 -*-
from __future__ import annotations
import weaviate, os
from weaviate.exceptions import WeaviateBaseError
from vector.schema import get_weaviate_client  # 若你已有統一的連線函式

# 若你沒有 get_weaviate_client，可改用：
# client = weaviate.Client(
#     url=os.environ.get("WEAVIATE_URL", "http://localhost:8080"),
#     auth_client_secret=None,
# )


def ensure_case_class():
    client = get_weaviate_client()
    schema = client.schema.get()
    classes = {c.get("class") for c in schema.get("classes", [])}
    if "Case" in classes:
        print("[schema] Class 'Case' already exists. Skip creating.")
        return

    case_class = {
        "class": "Case",
        "description": "De-identified TCM cases",
        "vectorizer": "none",
        "properties": [
            {"name": "case_id", "dataType": ["text"]},
            {"name": "timestamp", "dataType": ["text"]},
            {"name": "age", "dataType": ["text"]},
            {"name": "gender", "dataType": ["text"]},
            {"name": "chief_complaint", "dataType": ["text"]},
            {"name": "present_illness", "dataType": ["text"]},
            {"name": "provisional_dx", "dataType": ["text"]},
            {"name": "pulse_text", "dataType": ["text"]},
            {"name": "inspection_tags", "dataType": ["text[]"]},
            {"name": "inquiry_tags", "dataType": ["text[]"]},
            {"name": "pulse_tags", "dataType": ["text[]"]},
            {"name": "summary_text", "dataType": ["text"]},
            {"name": "summary", "dataType": ["text"]},
            # 如需多值，建議改 text[]；目前 uploader 以字串存單欄避免 422
            {"name": "diagnosis_main", "dataType": ["text"]},
            {"name": "diagnosis_sub", "dataType": ["text"]},
            {"name": "llm_struct", "dataType": ["text"]},
        ]
    }

    try:
        client.schema.create_class(case_class)
        print("[schema] Class 'Case' created.")
    except WeaviateBaseError as e:
        print("[schema] create class failed:", e)
        raise


if __name__ == "__main__":
    ensure_case_class()