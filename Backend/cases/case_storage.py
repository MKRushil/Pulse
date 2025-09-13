import os
import json
import logging
import datetime
from typing import Dict, Any

from cases.normalizer import build_deidentified_view
from cases.case_diagnosis import diagnose_triage
from vector.uploader import upload_case_vector

logger = logging.getLogger("cases.case_storage")


def _now_req_id() -> str:
    # e.g. 20250901_025706_6069
    now = datetime.datetime.now()
    return now.strftime("%Y%m%d_%H%M%S_") + f"{now.microsecond // 100:04d}"


def _data_dir() -> str:
    here = os.path.dirname(__file__)
    d = os.path.normpath(os.path.join(here, "..", "data"))
    os.makedirs(d, exist_ok=True)
    return d


def save_case_data(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    DCIP: 新增病例總控流程（1/4~4/4）
      1. save       : 保存原始 JSON 到 Backend/data/
      2. normalize  : 去識別視圖（僅保留 age/gender/chief/present/provisional）
      3. triage     : 輕量規則匹配 + 向量（diagnosis_main/sub 皆為 List[str]；llm_struct 為 Dict）
      4. upload     : 上傳 Case 物件與向量到 Weaviate

    備註：舊版流程曾假設 diagnosis_main/sub 為 List[Dict{name: str, weight: float}]；
          現版已簡化為 List[str]。本函式已相容處理，不再使用 m.get("name").
    """
    req_id = _now_req_id()

    # 1/4 save
    data_path = os.path.join(_data_dir(), f"{req_id}.json")
    try:
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        logger.info("[%s] [1/4 save] saved original file=%s", req_id, os.path.basename(data_path))
    except Exception as e:
        logger.error("[%s] [1/4 save] failed: %s", req_id, e)
        return {"ok": False, "error": f"save_failed: {e}"}

    # 2/4 normalize
    try:
        view = build_deidentified_view(raw)
        logger.info("[normalize] de-identified view ready gender=%s age=%s", view.get("gender", ""), view.get("age", ""))
        logger.info("[%s] [2/4 normalize] gender=%s age=%s", req_id, view.get("gender", ""), view.get("age", ""))
    except Exception as e:
        logger.error("[%s] [2/4 normalize] failed: %s", req_id, e)
        return {"ok": False, "error": f"normalize_failed: {e}"}

    # 3/4 triage
    try:
        diag = diagnose_triage(view)
        main_list = diag.get("diagnosis_main") or []  # List[str]
        sub_list = diag.get("diagnosis_sub") or []    # List[str]
        logger.info("[%s] [3/4 triage] main=%s sub=%s", req_id, main_list, sub_list)
    except Exception as e:
        logger.error("[%s] DCIP failed: %s", req_id, e, exc_info=True)
        return {"ok": False, "error": f"triage_failed: {e}"}

    # 4/4 upload
    try:
        case_id = upload_case_vector(view=view, diag=diag, file_path=data_path, req_id=req_id)
        return {"ok": True, "req_id": req_id, "case_id": case_id}
    except Exception as e:
        logger.error("[%s] [4/4 upload] failed: %s", req_id, e, exc_info=True)
        # 即使上傳失敗也回報基本資訊以便除錯
        return {"ok": False, "error": f"upload_failed: {e}", "req_id": req_id}
