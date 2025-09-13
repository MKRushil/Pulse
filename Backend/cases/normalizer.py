# -*- coding: utf-8 -*-
"""
建立去識別視圖（De-Identified View）
- 兼容前端可能的鍵名（camelCase / snake_case / 巢狀 basic.*）
- 清洗 text，補齊 summary_text（不可為空）
"""
from __future__ import annotations
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)


def _get_str(d: Dict[str, Any], *keys: str) -> str:
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _get_age(d: Dict[str, Any]) -> int | None:
    # 允許 basic.age / age（字串或數字）
    raw = d.get("age") or (d.get("basic") or {}).get("age")
    if raw is None:
        return None
    try:
        s = str(raw).strip()
        return int(s) if s else None
    except Exception:
        return None


def build_deidentified_view(data: Dict[str, Any]) -> Dict[str, Any]:
    # 兼容鍵名（含巢狀 basic.*, inquiry.*）
    gender = _get_str(data, "gender", "sex")
    if not gender and isinstance(data.get("basic"), dict):
        gender = _get_str(data["basic"], "gender", "sex")

    # 主訴
    chief = _get_str(data, "chief_complaint", "chiefComplaint")
    if not chief and isinstance(data.get("inquiry"), dict):
        chief = _get_str(data["inquiry"], "chief_complaint", "chiefComplaint")

    # 現病史
    present = _get_str(data, "present_illness", "presentIllness")
    if not present and isinstance(data.get("inquiry"), dict):
        present = _get_str(data["inquiry"], "present_illness", "presentIllness")

    # 暫定診斷
    provisional = _get_str(data, "provisional_dx", "provisionalDx")
    if not provisional and isinstance(data.get("inquiry"), dict):
        # 前端表單欄位名：tentativeDiagnosis
        provisional = _get_str(data["inquiry"], "provisional_dx", "provisionalDx", "tentativeDiagnosis")

    # 脈象/標籤類：允許為空
    pulse_text = _get_str(data, "pulse_text", "pulseText")
    inspection_tags = data.get("inspection_tags") or data.get("inspectionTags") or []
    inquiry_tags = data.get("inquiry_tags") or data.get("inquiryTags") or []
    pulse_tags = data.get("pulse_tags") or data.get("pulseTags") or []

    # 盡量從前端巢狀欄位聚合 tags（若已提供 *_tags 則保留原值）
    if not inspection_tags and isinstance(data.get("inspection"), dict):
        ins = data["inspection"]
        inspection_tags = [
            *([str(x) for x in (ins.get("bodyShape") or [])]),
            *([str(x) for x in (ins.get("faceColor") or [])]),
            *([str(x) for x in (ins.get("eye") or [])]),
            *([str(x) for x in (ins.get("skin") or [])]),
        ]
    if not inquiry_tags and isinstance(data.get("inquiry"), dict):
        iq = data["inquiry"]
        inquiry_tags = [
            *([str(x) for x in (iq.get("sleep") or [])]),
            *([str(x) for x in (iq.get("spirit") or [])]),
        ]

    age = _get_age(data)

    # 統一的去識別視圖（snake_case）
    view = {
        "age": age,
        "gender": gender,
        "chief_complaint": chief,
        "present_illness": present,
        "provisional_dx": provisional,
        "pulse_text": pulse_text,
        "inspection_tags": inspection_tags,
        "inquiry_tags": inquiry_tags,
        "pulse_tags": pulse_tags,
    }

    # 構造摘要（不可為空）
    parts = []
    if chief:
        parts.append(f"[主訴] {chief}")
    if present:
        parts.append(f"[現病史] {present}")
    if pulse_text:
        parts.append(f"[脈象] {pulse_text}")
    if provisional:
        parts.append(f"[暫定診斷] {provisional}")
    summary_text = "\n".join(parts).strip() or "（無敘述）"
    view["summary_text"] = summary_text

    logger.info("[normalize] de-identified view ready gender=%s age=%s", gender, age if age is not None else "")
    return view
