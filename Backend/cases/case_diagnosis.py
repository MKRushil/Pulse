import os
import json
import logging
import datetime
from typing import Dict, List, Tuple

from vector.embedding import generate_embedding

logger = logging.getLogger("cases.case_diagnosis")

# -----------------------------------------------------------------------------
# Rulebook loading
# -----------------------------------------------------------------------------
_RULEBOOK_CACHE: Dict | None = None


def _default_rulebook_paths() -> List[str]:
    """Candidate paths (first existing wins)."""
    here = os.path.dirname(__file__)
    return [
        # 1) env override
        os.environ.get("TCM_RULEBOOK_PATH", ""),
        # 2) project default: Backend/prompt/tcm_rulebook_v1.1.json
        os.path.normpath(os.path.join(here, "..", "prompt", "tcm_rulebook_v1.1.json")),
        # 3) fallbacks (older names)
        os.path.normpath(os.path.join(here, "..", "prompt", "tcm_rulebook.json")),   
    ]


def _load_rulebook() -> Dict:
    global _RULEBOOK_CACHE
    if _RULEBOOK_CACHE is not None:
        return _RULEBOOK_CACHE

    paths = [p for p in _default_rulebook_paths() if p]
    for p in paths:
        try:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    rb = json.load(f)
                _RULEBOOK_CACHE = rb
                logger.info(
                    "[rulebook] loaded path=%s version=%s rules=%s",
                    p,
                    rb.get("version"),
                    len(rb.get("diseases", [])),
                )
                return _RULEBOOK_CACHE
        except Exception as e:
            logger.warning("[rulebook] failed to load %s: %s", p, e)

    # Minimal safe fallback
    logger.warning("[rulebook] no rulebook file found, using minimal fallback rules")
    _RULEBOOK_CACHE = {
        "version": "fallback",
        "weights": {"symptoms": 0.7, "inspection": 0.0, "pulse": 0.0, "free_text": 0.3},
        "thresholds": {"rule_hit": 0.1, "primary_min_score": 0.2, "secondary_min_score": 0.1, "max_secondary": 2},
        "synonyms": {"失眠": ["睡不好", "難入眠", "入睡困難"], "胸悶": ["胸口悶"], "心煩": ["煩躁不安", "煩躁"]},
        "diseases": [
            {"label": "肝鬱氣滯·fallback", "symptoms": ["胸悶", "心煩", "睡不好"], "inspection": [], "pulse": [], "pulse_28": []},
            {"label": "心脾兩虛·fallback", "symptoms": ["失眠", "乏力"], "inspection": [], "pulse": [], "pulse_28": []},
        ],
    }
    return _RULEBOOK_CACHE


# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------

def _nowstr() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _ensure_list_str(x) -> List[str]:
    if not x:
        return []
    if isinstance(x, str):
        return [x]
    if isinstance(x, list):
        return [str(i) for i in x if i]
    return [str(x)]


def _build_text(view: Dict) -> str:
    chief = (view.get("chiefComplaint") or "").strip()
    present = (view.get("presentIllness") or "").strip()
    provisional = (view.get("provisionalDx") or view.get("provisional_dx") or "").strip()

    sections: List[str] = []
    if chief:
        sections.append(f"[主訴] {chief}")
    if present:
        sections.append(f"[現病史] {present}")
    if provisional:
        sections.append(f"[暫定診斷] {provisional}")

    summary_text = "\n".join(sections).strip()
    # 保底，避免空 embedding 造成外部 API 400
    if not summary_text:
        summary_text = "臨床摘要缺失；僅做系統保底處理。"
    return summary_text


def _expand_terms(text: str, synonyms: Dict[str, List[str]]):
    """Return (hits, hit_map) where hits is set of canonical terms matched in text.
    hit_map maps canonical -> list of variants hit.
    """
    t = text.lower().replace(" ", "")
    hits = set()
    hit_map: Dict[str, List[str]] = {}

    def _add_hit(key: str, var: str):
        hits.add(key)
        hit_map.setdefault(key, []).append(var)

    for canonical, vars_ in (synonyms or {}).items():
        variants = set(vars_ or []) | {canonical}
        for v in variants:
            vv = str(v).lower().replace(" ", "")
            if vv and vv in t:
                _add_hit(canonical, v)
    return hits, hit_map


def _score_disease(rule: Dict, token_sets: Dict[str, set], weights: Dict[str, float]) -> Tuple[float, Dict[str, List[str]]]:
    """Compute score and detail map of hits for one disease rule."""
    detail: Dict[str, List[str]] = {"symptoms": [], "inspection": [], "pulse": [], "free_text": []}

    score = 0.0
    # symptoms
    sym = set(_ensure_list_str(rule.get("symptoms")))
    if sym:
        hit = sym & token_sets.get("symptoms", set())
        ratio = len(hit) / max(1, len(sym))
        score += weights.get("symptoms", 0.0) * ratio
        detail["symptoms"] = list(hit)

    # inspection
    ins = set(_ensure_list_str(rule.get("inspection")))
    if ins:
        hit = ins & token_sets.get("inspection", set())
        ratio = len(hit) / max(1, len(ins))
        score += weights.get("inspection", 0.0) * ratio
        detail["inspection"] = list(hit)

    # pulse
    pul = set(_ensure_list_str(rule.get("pulse")))
    if pul:
        hit = pul & token_sets.get("pulse", set())
        ratio = len(hit) / max(1, len(pul))
        score += weights.get("pulse", 0.0) * ratio
        detail["pulse"] = list(hit)

    # free_text boost by label present in provisional dx / summary
    label = str(rule.get("label") or "").strip()
    free_bank = token_sets.get("free_text_bank", set())
    if label and any(label.lower() in s for s in free_bank):
        score += weights.get("free_text", 0.0)
        detail["free_text"].append(label)

    return score, detail


def _vector_to_list(emb):
    """Accept numpy array, list, tuple, memoryview; return Python list or None."""
    if emb is None:
        return None
    try:
        if isinstance(emb, list):
            return emb
        if hasattr(emb, "tolist"):
            return emb.tolist()
        # last resort
        return list(emb)
    except Exception as e:
        logger.error("[diagnose_triage] cannot convert embedding to list: %s", e)
        return None


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def diagnose_triage(view: Dict) -> Dict:
    """
    規則庫 + 輕量匹配版診斷：
      - 讀取 tcm_rulebook_v1.3.json（可用環境變數 TCM_RULEBOOK_PATH 覆蓋）
      - 用主訴/現病史/暫定診斷做症狀匹配；若有在文字中出現的望診/脈象詞也會納入
      - 依 weights/thresholds 計分，輸出主病/次病與 llm_struct
      - 生成 embedding（保證非空，且兼容 list / numpy array）
    回傳欄位與既有流程相容：
      - diagnosis_main: List[str]
      - diagnosis_sub:  List[str]
      - llm_struct:     Dict (由 uploader 轉 JSON 字串存放)
      - summary_text, embedding, timestamp
    """
    rb = _load_rulebook()
    weights = rb.get("weights", {})
    th = rb.get("thresholds", {})
    synonyms = rb.get("synonyms", {})

    # 1) 組摘要文本
    summary_text = _build_text(view)

    # 2) 建 token bank（雙模式：專有名詞 + 白話描述）
    provisional = (view.get("provisionalDx") or view.get("provisional_dx") or "").strip()
    free_bank = {summary_text.lower(), provisional.lower()} - {""}

    # symptoms from synonyms
    sym_hits, _sym_map = _expand_terms(summary_text + "\n" + provisional, synonyms)
    token_sets = {
        "symptoms": sym_hits,         # 來自同義詞展開
        "inspection": set(),          # 若未來 normalizer 提供，這裡自動吸收
        "pulse": set(),               # 同上
        "free_text_bank": free_bank,
    }

    # 3) 規則逐條計分
    scored: List[Tuple[str, float, Dict[str, List[str]], List[str]]] = []  # (label, score, detail, pulse28)
    for rule in rb.get("diseases", []):
        label = str(rule.get("label") or "").strip()
        if not label:
            continue
        score, detail = _score_disease(rule, token_sets, weights)
        if score >= float(th.get("rule_hit", 0.0)):
            scored.append((label, score, detail, _ensure_list_str(rule.get("pulse_28"))))

    if not scored:
        # 沒有命中任何規則時，採用暫定診斷作為主病
        provisional_label = provisional or "未能匹配規則"
        main_labels = [provisional_label]
        sub_labels: List[str] = []
        pulse28: List[str] = []
    else:
        # 排序取主/次
        scored.sort(key=lambda x: x[1], reverse=True)
        primary_min = float(th.get("primary_min_score", 0.0))
        secondary_min = float(th.get("secondary_min_score", 0.0))
        max_secondary = int(th.get("max_secondary", 3))

        main_labels: List[str] = []
        sub_labels: List[str] = []
        pulse28: List[str] = []

        if scored[0][1] >= primary_min:
            main_labels = [scored[0][0]]
            pulse28 = scored[0][3]
        else:
            main_labels = [provisional or scored[0][0]]
            pulse28 = scored[0][3]

        for label, s, _d, _p28 in scored[1:]:
            if s >= secondary_min and label not in main_labels:
                sub_labels.append(label)
                if not pulse28:
                    pulse28 = _p28
            if len(sub_labels) >= max_secondary:
                break

    # 4) llm_struct（結構化、可追溯說明）
    llm_struct = {
        "主病": main_labels,
        "次病": sub_labels,
        "推理說明": (
            f"規則庫 v{rb.get('version', 'NA')}；主病={main_labels} 次病={sub_labels}；權重={weights}；門檻={th}."
        ),
    }

    # 5) 向量（保證非空；兼容 list/ndarray）
    emb_input = summary_text
    if sym_hits:
        emb_input += "\n命中要點：" + "、".join(sorted(sym_hits))
    emb = generate_embedding(emb_input)

    return {
        "status": "ok",
        "summary": summary_text,
        "summary_text": summary_text,
        "embedding": _vector_to_list(emb),
        "diagnosis_main": main_labels,
        "diagnosis_sub": sub_labels,
        "llm_struct": llm_struct,
        "pulse_28": pulse28,
        "timestamp": _nowstr(),
    }
