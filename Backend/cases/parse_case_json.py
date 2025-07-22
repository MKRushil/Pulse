# cases/parse_case_json.py

import json

def parse_case_json(case: dict) -> dict:
    """
    將原始病歷 JSON 拆解為五大段落：主訴、現病史、望診、問診、脈診
    return: dict[str, str] → {'主訴': ..., '現病史': ..., ...}
    """
    print("[ParseCaseJSON] 開始解析 JSON 為五段 summary")

    inquiry = case.get("inquiry", {})
    inspection = case.get("inspection", {})
    pulse = case.get("pulse", {})

    result = {
        "主訴": inquiry.get("chiefComplaint", ""),
        "現病史": inquiry.get("presentIllness", "")
    }
    print(f"[ParseCaseJSON] 主訴: {result['主訴']}")
    print(f"[ParseCaseJSON] 現病史: {result['現病史']}")

    # 整理望診摘要
    inspection_parts = []
    if inspection.get('bodyShape'): inspection_parts.append("體型：" + "、".join(inspection['bodyShape']))
    if inspection.get('faceColor'): inspection_parts.append("臉色：" + "、".join(inspection['faceColor']))
    if inspection.get('faceOther'): inspection_parts.append("臉部補充：" + inspection['faceOther'])
    if inspection.get('eye'): inspection_parts.append("眼部：" + "、".join(inspection['eye']))
    if inspection.get('skin'): inspection_parts.append("皮膚：" + "、".join(inspection['skin']))
    result["望診"] = "；".join(inspection_parts)
    print(f"[ParseCaseJSON] 望診: {result['望診']}")

    # 問診摘要
    inquiry_parts = []
    if inquiry.get('sleep'): inquiry_parts.append("睡眠：" + "、".join(inquiry['sleep']))
    if inquiry.get('spirit'): inquiry_parts.append("精神：" + "、".join(inquiry['spirit']))
    if inquiry.get('symptoms'): inquiry_parts.append("症狀：" + "、".join(inquiry['symptoms']))
    if inquiry.get('otherSymptom'): inquiry_parts.append("其他補充：" + inquiry['otherSymptom'])
    result["問診"] = "；".join(inquiry_parts)
    print(f"[ParseCaseJSON] 問診: {result['問診']}")

    # 脈診摘要
    pulse_parts = []
    for part in ["左寸", "左關", "左尺", "右寸", "右關", "右尺"]:
        p = pulse.get(part, {})
        if p and (p.get('types') or p.get('note')):
            t_str = "、".join(p.get('types', []))
            desc = f"{part}：{t_str}" if t_str else f"{part}"
            if p.get('note'): desc += f"（{p['note']}）"
            pulse_parts.append(desc)
    result["脈診"] = "；".join(pulse_parts)
    print(f"[ParseCaseJSON] 脈診: {result['脈診']}")

    print("[ParseCaseJSON] 完成分段 summary 輸出")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print()

    return result
