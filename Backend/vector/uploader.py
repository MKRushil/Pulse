# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List
import os, time, json, hashlib, logging
from vector.schema import get_weaviate_client

logger = logging.getLogger(__name__)

CLASS_NAME = "Case"
TAG_FIELDS = ["inspection_tags", "inquiry_tags", "pulse_tags"]
DX_FIELDS = ["diagnosis_main", "diagnosis_sub"]


def _sha256_short(s: str, n: int = 12) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:n]

# ---- schema introspection ----

def _get_class_props(client, class_name: str) -> Dict[str, List[str]]:
    schema = client.schema.get()
    for c in schema.get("classes", []):
        if c.get("class") == class_name:
            return {p["name"]: p.get("dataType", []) for p in c.get("properties", [])}
    return {}

_def_array_markers = {"text[]", "string[]"}

def _is_array_prop(datatype: List[str]) -> bool:
    if not datatype:  # defensive
        return False
    # weaviate 版本差異：可能回傳 "text[]" 或 "string[]"
    return any(dt in _def_array_markers or dt.endswith("[]") for dt in datatype)

# ---- value coercion ----

def _to_list_str(v) -> List[str]:
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return [str(x).strip() for x in v if str(x).strip()]
    s = str(v).strip()
    return [s] if s else []


def _to_joined_text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        items = [str(x).strip() for x in v if str(x).strip()]
        return "、".join(items)
    return str(v)


def _coerce_by_schema(props: Dict[str, List[str]], field: str, value: Any):
    """根據 schema 決定回傳 list[str] 或 str。未知欄位預設原值。"""
    if field not in props:
        return value
    if _is_array_prop(props[field]):
        return _to_list_str(value)
    else:
        return _to_joined_text(value)


# ---- main uploader ----

def upload_case_vector(*, view: Dict[str, Any], diag: Dict[str, Any], file_path: str, req_id: str) -> str:
    client = get_weaviate_client()

    props = _get_class_props(client, CLASS_NAME)

    case_id = _sha256_short(os.path.basename(file_path), 12)
    ts_iso = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    # 取嵌入（相容兩種鍵名）
    emb = diag.get("embedding") or (diag.get("embeddings") or {}).get("summary_vec")
    if not emb:
        raise ValueError("summary embedding 缺失，無法上傳向量物件")

    # llm_struct → 字串
    llm_struct = diag.get("llm_struct")
    if isinstance(llm_struct, (dict, list)):
        llm_struct = json.dumps(llm_struct, ensure_ascii=False)

    # age 一律字串化（schema 可能為 text）
    raw_age = view.get("age")
    age_str = "" if raw_age is None else str(raw_age)
    logger.info("[%s] [4/4 upload] age before send: value=%r type=%s → send as str='%s'", req_id, raw_age, type(raw_age).__name__, age_str)

    summary_text = diag.get("summary_text") or view.get("summary_text") or ""

    # 先組 base 物件
    obj: Dict[str, Any] = {
        "case_id": case_id,
        "timestamp": ts_iso,
        "age": age_str,
        "gender": view.get("gender") or "",
        "chief_complaint": view.get("chief_complaint") or "",
        "present_illness": view.get("present_illness") or "",
        "provisional_dx": view.get("provisional_dx") or "",
        "pulse_text": view.get("pulse_text") or "",
        "summary_text": summary_text,
        "summary": summary_text,  # 舊查詢鏡像
        # 先放原值，稍後根據 schema 強制轉型
        "inspection_tags": view.get("inspection_tags"),
        "inquiry_tags": view.get("inquiry_tags"),
        "pulse_tags": view.get("pulse_tags"),
        # 診斷（可能為 list 或 str，由下方統一轉型）
        "diagnosis_main": [m.get("name", m) if isinstance(m, dict) else m for m in (diag.get("diagnosis_main") or [])],
        "diagnosis_sub":  [s.get("name", s) if isinstance(s, dict) else s for s in (diag.get("diagnosis_sub") or [])],
        "llm_struct": llm_struct or "",
    }

    # 依 schema 自動適配欄位型別（避免 422）
    for f in TAG_FIELDS + DX_FIELDS:
        if f in obj:
            obj[f] = _coerce_by_schema(props, f, obj[f])

    logger.info("[%s] [4/4 upload] prepare record", req_id)
    client.data_object.create(data_object=obj, class_name=CLASS_NAME, vector=emb)
    logger.info("[%s] [4/4 upload] Case created de-identified id=%s", req_id, case_id)
    return case_id