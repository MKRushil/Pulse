中醫智慧輔助診斷系統 —— Backend & CBR+LLM 流程說明

# 1️⃣ 檔案文字架構圖

```
backend/
├── main.py                          ← FastAPI 路由入口
├── config.py                        ← API/模型/向量庫連線設定
├── cases/
│   ├── case_storage.py             ← 病歷儲存與診斷流程
│   ├── case_diagnosis.py           ← 病歷摘要、主次病推理、權重分析
│   └── result_listing.py           ← 歷史診斷列表（暫未啟用）
├── vector/
│   ├── uploader.py                 ← 向量資料自動上傳 Weaviate
│   ├── cleaner.py                  ← 匿名化（去個資）向量處理
│   ├── schema.py                   ← Weaviate schema 管理
│   └── embedding.py                ← 產生查詢/入庫語意向量
├── cbr/
│   ├── query_router.py             ← 自動選擇 A/B 流程（是否含個人 ID）
│   ├── spiral_a.py                 ← 方案A：無身分，查詢 Case + PulsePJ
│   ├── spiral_b.py                 ← 方案B：有身分，查詢 PCD + Case + PulsePJ
│   ├── utils.py                    ← 聚合、排序、去重等工具
│   ├── reasoning_logger.py         ← 推理流程/推理鏈紀錄、可視化支持
│   └── tree_builder.py             ← 推理樹結構生成
├── llm/
│   ├── prompt_builder.py           ← Prompt 組裝/組合（for LLM）
│   ├── llm_executor.py             ← 發送 prompt 給 LLM 模型、解析結構
│   └── embedding.py                ← 向量嵌入
├── prompt/
│   └── template.txt                ← Prompt 樣板外部管理（選用）
├── data/                           ← 病歷原始 JSON
├── result/                         ← 診斷摘要與推理結果
ui/                                 ← 前端（index.html、main.js…）
```

# 2️⃣ 整體檔案流程圖

```
[前端表單]
    ↓
POST /api/case/save   ← main.py
    ↓
[ cases/case_storage.py ]  (儲存→診斷→上傳向量)
    ↓
[ cases/case_diagnosis.py ]
    ↓
[ vector/uploader.py → schema.py → embedding.py ]
    ↓
病歷、診斷、權重資料 進入向量庫（Case/PCD）

用戶查詢（問診/模擬推理）
    ↓
POST /api/query    ← main.py
    ↓
[ cbr/query_router.py ]  → 自動選擇 A/B 流程
    ↓                 ↙
spiral_a.py       spiral_b.py
（匿名查詢）      （有身分查詢）
    ↓                 ↓
  查詢 Case/PulsePJ    查詢 PCD→Case→PulsePJ
    ↓                 ↓
[ llm/prompt_builder.py ]
    ↓
[ llm/llm_executor.py ]
    ↓
LLM AI 綜合推理
    ↓
回傳 dialog + 推理鏈給前端
```

# 3️⃣ 對話整體流程圖

```
使用者問題/症狀（如：最近總是頭暈、氣短，脈象偏細弱…）
    ↓
API 查詢（/api/query）
    ↓
CBR 系統查詢相關案例與脈象知識（Case/PulsePJ/PCD）
    ↓
推理鏈組裝（reasoning_chain、tree）
    ↓
Prompt Builder 組合所有摘要
    ↓
送至 LLM（大模型）AI 綜合分析
    ↓
AI 條列回覆診斷總結、主次病推理、臨床建議（dialog）
    ↓
前端顯示（dialog + 資料表格/推理鏈樹狀可視化）
```

# 4️⃣ 病例整體流程圖與檔案流向

```
[前端送出病例表單]          ↓
    main.py  (POST /api/case/save)
         ↓
   cases/case_storage.py
         ↓
1. 儲存至 ./data/
2. 呼叫 cases/case_diagnosis.py 生成摘要與主次病、權重
3. 自動上傳向量資料（vector/uploader.py）→ Weaviate
4. 回傳診斷結果給前端
5. result/ 目錄保存語意摘要、推理結構
```

# 5️⃣ 主要檔案與API/功能說明

## main.py

| 路由                   | 功能說明                |
| -------------------- | ------------------- |
| POST /api/case/save  | 儲存病歷 JSON（含時間與 ID）  |
| POST /api/diagnose   | 執行病歷摘要與模型推理         |
| GET /api/result/list | 列出歷史診斷結果            |
| POST /api/query      | 查詢（自動選擇 A/B 案例推理流程） |
| GET /                | 回傳前端首頁 index.html   |
| GET /static/...      | 掛載靜態前端檔案            |

## cases/case\_storage.py

病歷儲存模組：接收前端表單（結構固定），儲存 JSON 至 ./data/（含時間戳、身分末四碼），執行診斷摘要並上傳向量庫，回傳完整診斷結果與檔名。

## cases/case\_diagnosis.py

病歷語意摘要與主次病推理，萃取主病、次病與計算權重，可串接 LLM AI 協助摘要推理。

## vector/

* uploader.py：整合診斷、權重、病例資料，自動上傳至 Weaviate 向量庫（含時間戳）
* schema.py：Weaviate schema 初始化、class 建立、結構查詢
* embedding.py：產生語意向量（查詢/入庫）

## cbr/

* query\_router.py：判斷查詢內容，自動選擇 spiral\_a（匿名查詢）或 spiral\_b（個人化查詢）
* spiral\_a.py：方案A：查 Case/PulsePJ，無身分資訊，整合推理給 LLM
* spiral\_b.py：方案B：查 PCD→Case→PulsePJ，根據個人資料串推理
* utils.py：聚合排序、去重、脈象知識 mapping 統一格式
* reasoning\_logger.py：推理鏈紀錄，流程樹狀資料結構組成，方便前端可視化
* tree\_builder.py：將推理鏈 reasoning\_chain 組成樹狀結構（供前端展示）

## llm/

* prompt\_builder.py：Prompt 組裝模組，支援 build\_prompt\_from\_case、build\_spiral\_prompt\_from\_cases、build\_integrated\_prompt 等方式，亦可匯入 template.txt 樣板
* llm\_executor.py：負責呼叫 LLM 模型（NVIDIA/OpenAI/本地），正規解析主病/次病/權重/推理說明，回傳結構化與原始資料

# 6️⃣ 系統特色與擴充

* 支援病例資料存儲、向量化自動搜尋、權重推理與推理鏈完整紀錄
* 支援多步推理、AI 臨床推理整合（CBR + RAG + LLM）
* 推理流程與資料來源皆可追溯（Explainable AI）
* 前端支援推理樹狀結構、病例/脈象查詢詳表、AI 條列式臨床診斷建議
