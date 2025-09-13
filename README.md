中醫智慧輔助診斷系統 —— 單一路由 & 去識別化新增流程

本系統已簡化為：單一路由查詢（spiral）＋去識別化的新增病例處理鏈（DCIP）。

## 1) 目錄與模組

```
Backend/
├── main.py                 ← FastAPI 入口（/api/case/save、/api/query、/healthz）
├── config.py               ← API/模型/向量庫連線設定
├── cases/
│   ├── case_storage.py     ← 新增病例總控（save→normalize→triage→upload）
│   └── case_diagnosis.py   ← 簡化診斷（主/次病與權重）＋嵌入
├── cbr/
│   ├── spiral.py           ← 單一路由查詢：Case + PulsePJ 檢索、聚合、LLM
│   ├── utils.py            ← 排序、聚合、去重、PulsePJ 映射
│   └── tree_builder.py     ← 推理樹結構
├── llm/
│   ├── prompt_builder.py   ← Prompt 組裝
│   └── llm_executor.py     ← LLM 呼叫與回應解析
├── vector/
│   ├── embedding.py        ← 產生查詢/入庫嵌入向量
│   ├── uploader.py         ← 去識別 Case 上傳（匿名 case_id）
│   └── schema.py           ← Weaviate 連線（僅保留 Case）
└── data/, logs/, result/   ← 原始病例、日誌與輸出
```

## 2) 新增病例處理鏈（DCIP）

```
前端 TCMForm → POST /api/case/save → cases/case_storage.save_case_data
  [1/4 save]  寫原始 JSON → Backend/data/{timestamp_id}.json
  [2/4 normalize] 去識別視圖（age/gender/chief/present/provisional）
  [3/4 triage]   產出主/次病與權重（預設 0.7/0.3）＋ embedding
  [4/4 upload]   上傳 Weaviate「Case」類別（匿名 case_id）
```

## 3) 查詢（單一路由 spiral）

```
POST /api/query → cbr/spiral.run(question, patient_ctx?)
  嵌入 question → 檢索 Case + PulsePJ → 聚合與 Prompt → LLM 回覆（dialog + llm_struct）
  可回 reasoning_chain 與樹狀結構（tree）供可視化
```

## 4) Weaviate Schema（Case）

- 主要欄位：`case_id`（匿名）、`timestamp`、`age`、`gender`、`summary`、
  `chief_complaint`、`present_illness`、`provisional_dx`、
  `diagnosis_main`、`diagnosis_sub`、`embedding`
- 兼容欄位：`llm_struct`、`main_disease`、`sub_diseases`、`semantic_scores`、
  `source_model`、`source_score_method` 等
- 建議先執行 `Backend/vector/weaviate_schema_create.py` 以建立 `Case` 類別

## 5) 開發與啟動

- 後端：`uvicorn Backend.main:app --reload`
- 前端：`cd ui && npm install && npm run dev`（Vite 代理 `/api` → `:8000`）

## 6) 變更紀要（簡）

- 合併查詢為單一路由：刪除 `cbr/spiral_b.py` 與 `cbr/query_router.py`
- Weaviate 僅保留 Case：`vector/schema.py` 僅輸出 Case；`weaviate_schema_create.py` 只建立 Case
- 新增病例入庫改為去識別化：不上傳個資（不建 PCD），匿名 `case_id`
