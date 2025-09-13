# -*- coding: utf-8 -*-
"""
查詢 Weaviate 中 Class `Case` 的**所有欄位**與**所有物件**，可選擇匯出 JSON/CSV。
- 會動態讀取 schema 來取得所有 properties。
- 以 offset 分頁讀取，避免單次拉太多造成逾時。
- 可選擇是否一併拉 `_additional { id, vector }`（向量很大，預設不帶）。

用法：
    python tools/test_query_case_all.py --batch 100 --export json --out cases.json
    python tools/test_query_case_all.py --with-vector --limit 200

參數說明：
    --class-name    預設 Case
    --batch         每批次筆數（預設 100）
    --limit         最多抓取筆數（預設無上限）
    --with-vector   是否回傳 _additional.vector（預設否）
    --export        匯出格式：json / csv / none（預設 none）
    --out           匯出路徑（預設 output.json 或 output.csv）
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import sys
from typing import Any, Dict, List

from vector.schema import get_weaviate_client


def get_all_properties(client, class_name: str) -> List[str]:
    schema = client.schema.get()
    classes = schema.get("classes", [])
    for c in classes:
        if c.get("class") == class_name:
            return [p["name"] for p in c.get("properties", [])]
    return []


def flatten(v: Any) -> str:
    """將 list 轉為 '、' 連接之字串，其他型態轉字串。"""
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        return "、".join(str(x) for x in v)
    return str(v)


def iter_objects(client, class_name: str, props: List[str], batch: int = 100, limit: int | None = None, with_vector: bool = False):
    total = 0
    offset = 0
    addl = ["id"]
    if with_vector:
        addl.append("vector")

    while True:
        q = client.query.get(class_name, props).with_limit(batch).with_offset(offset).with_additional(addl)
        res = q.do()
        hits = res.get("data", {}).get("Get", {}).get(class_name, [])
        if not hits:
            break
        for h in hits:
            yield h
            total += 1
            if limit is not None and total >= limit:
                return
        offset += batch


def export_json(rows: List[Dict[str, Any]], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def export_csv(rows: List[Dict[str, Any]], path: str) -> None:
    if not rows:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write("")
        return
    # 取所有 keys（含 _additional）
    keys = set()
    for r in rows:
        keys.update(r.keys())
    fieldnames = sorted(keys)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            row = {k: (json.dumps(r[k], ensure_ascii=False) if isinstance(r.get(k), (dict, list)) else flatten(r.get(k))) for k in fieldnames}
            writer.writerow(row)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--class-name", default="Case", help="Weaviate class 名稱（預設 Case）")
    ap.add_argument("--batch", type=int, default=100, help="每批抓取數量（預設 100）")
    ap.add_argument("--limit", type=int, default=None, help="最多抓取筆數（預設無上限）")
    ap.add_argument("--with-vector", action="store_true", help="是否包含 _additional.vector（資料量大，預設否）")
    ap.add_argument("--export", choices=["json", "csv", "none"], default="none", help="匯出格式（預設 none）")
    ap.add_argument("--out", default=None, help="匯出檔名（預設 output.json / output.csv）")
    args = ap.parse_args()

    client = get_weaviate_client()
    props = get_all_properties(client, args.class_name)
    if not props:
        print(f"找不到 {args.class_name} 的 schema 或無 properties，請確認 Class 是否存在")
        sys.exit(1)

    print(f"\n===== {args.class_name}（全部欄位，共 {len(props)} 欄）=====")
    print("、".join(props))

    rows: List[Dict[str, Any]] = []
    count = 0
    for obj in iter_objects(client, args.class_name, props, batch=args.batch, limit=args.limit, with_vector=args.with_vector):
        count += 1
        print(f"\n--- 第{count}筆 ---")
        for k, v in obj.items():
            print(f"{k}: {v}")
        rows.append(obj)

    print(f"\n總筆數：{count}")

    if args.export != "none":
        out = args.out
        if out is None:
            out = "output.json" if args.export == "json" else "output.csv"
        if args.export == "json":
            export_json(rows, out)
        else:
            export_csv(rows, out)
        print(f"已匯出：{out}")


if __name__ == "__main__":
    main()
