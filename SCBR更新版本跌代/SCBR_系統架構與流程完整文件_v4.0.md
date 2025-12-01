Agentic SCBR 系統架構與流程完整文件

版本: v4.0 (Agentic Edition)

最後更新: 2025-11-29

文件狀態: 正式版

適用範圍: Backend/s_cbr/* 核心模組

📋 目錄

系統概述

系統分層架構

核心流程詳解 (The Agentic Flow)

智能代理與工具體系 (Agents & Tools)

安全防護體系 (Security Architecture)

螺旋式會話管理

測試與驗證

1. 系統概述

Agentic SCBR (Spiral Case-Based Reasoning) 是 SCBR 系統的第四代演進版本。與傳統的線性流水線不同，v4.0 引入了智能代理 (Agentic) 架構，讓系統具備了動態決策、工具調用 (Tool Use) 和複雜推理的能力。

核心升級點 (v4.0 vs v3.0)

特性

v3.0 (四層流水線)

v4.0 (Agentic SCBR)

流程控制

固定線性 (L1→L2→L3→L4)

動態協作 (Agent 根據情境決策)

檢索策略

靜態混合檢索

智能檢索 (Query Expansion + 動態權重)

診斷推理

單次 LLM 生成

多模組協同 (辨證 + 病機 + 工具調用)

外部能力

無

工具調用 (Function Calling)

收斂機制

簡單閾值判斷

覆蓋度驅動的螺旋收斂

2. 系統分層架構

系統採用六層階層式架構，確保職責分離與高可維護性。

graph TD
    User((用戶 User)) --> API[API 網關層]
    
    subgraph Layer 1: Access & Security
        API --> RateLimit[Rate Limiter]
        RateLimit --> InputSanitizer[Input Sanitizer & PII Masker]
    end
    
    subgraph Layer 2: Orchestration & Session
        InputSanitizer --> DialogMgr[Dialog Manager]
        DialogMgr --> Pipeline[Agentic Pipeline Orchestrator]
    end
    
    subgraph Layer 3: Agentic Intelligence (The Core)
        Pipeline --> L1[L1 Agent: Intent & NLU]
        Pipeline --> Retrieval[Retrieval Agent]
        Pipeline --> L2[L2 Agent: Diagnosis & Reasoning]
        Pipeline --> L3[L3 Agent: Safety Review]
        Pipeline --> L4[L4 Agent: Presentation]
    end
    
    subgraph Layer 4: Knowledge & Tools
        L1 -.-> TermTool[Terminology Manager]
        Retrieval -.-> SearchEng[Search Engine]
        L2 -.-> TCMTools[TCM Tools Set]
        SearchEng -.-> VectorDB[(Vector DB / Weaviate)]
    end
    
    subgraph Layer 5: Output Guardrails
        Pipeline --> OutputVal[Output Validator]
        OutputVal --> UnifiedResp[Unified Response]
    end


3. 核心流程詳解 (The Agentic Flow)

本章節描述單次 /diagnose 請求的完整生命週期。

階段 I: 請求預處理與安全前置 (Pre-processing)

負責模組: main.py, security/

接收請求: api.py 接收 POST 請求。

速率限制: rate_limiter.py 檢查 IP/Session 是否超限 (LLM10 防護)。

輸入淨化: input_sanitizer.py 攔截 Prompt Injection (LLM01)，並呼叫 pii_masker.py 對敏感個資 (電話、身分證) 進行脫敏 (LLM02)。

螺旋累積: dialog_manager.py 將當前輸入與歷史對話合併，形成累積問題上下文 (Accumulated Context)。

階段 II: L1 意圖識別與預處理 (L1 Agentic Gate)

負責模組: prompts/l1_gate_agentic_prompt.txt

意圖判斷: LLM 分析用戶是否在詢問中醫病情。

關鍵詞提取: 提取症狀、舌象、脈象、病史等結構化實體。

工具調用 (Tool Use): L1 Agent 判斷是否需要呼叫 utils/terminology_manager.py 將口語化症狀 (如 "心裡慌") 轉換為標準術語 ("心悸")。

決策路由:

reject: 非中醫或惡意內容 → 觸發 422 安全阻斷。

ask_more: 資訊嚴重不足 → 直接生成引導式追問。

vector_search: 資訊有效 → 進入檢索層。

階段 III: 智能檢索 (Agentic Retrieval)

負責模組: core/agentic_retrieval.py

查詢優化: Agent 根據上下文進行 查詢擴展 (Query Expansion)，生成多組語義相關的查詢詞。

策略調整: 動態決定混合檢索的權重 (Vector vs Keyword) 和檢索欄位 (Symptoms/Pattern)。

執行檢索: 呼叫 core/search_engine.py + llm/embedding.py，從資料庫返回 Top N (預設 3-5) 最相關案例。

階段 IV: L2 診斷與推理 (L2 Agentic Diagnosis)

負責模組: core/l2_agentic_diagnosis.py, prompts/l2_case_anchored_diagnosis_prompt.txt

這是系統的「大腦」，執行複雜的認知任務：

案例錨定 (Anchoring): 從 Top N 案例中鎖定一個最匹配的參考案例。

協同推理:

辨證分析: 分析病因、病機、證型。

工具輔助: 若需要，呼叫 tools/tcm_tools.py 查詢藥方禁忌或穴位資訊。

收斂評估 (Coverage Logic):

計算 Coverage Ratio (覆蓋度)。

若 Ratio $\ge$ 閾值 (如 0.8) $\rightarrow$ 收斂 (Converged)，生成最終診斷。

若 Ratio $<$ 閾值 $\rightarrow$ 未收斂，基於缺失資訊生成 精準追問 (Follow-up Questions)。

階段 V: 安全審核與輸出 (Review & Presentation)

負責模組: prompts/l3_safety_review_prompt.txt, l4_presentation_prompt.txt

L3 安全審核: 檢查 L2 輸出是否包含具體劑量、保證療效等醫療風險 (LLM05) 或邏輯矛盾 (LLM09)。

結果: passed / rewritten (改寫) / rejected (阻斷)。

L4 呈現: 將內容格式化為結構清晰的 Markdown 報告。

輸出驗證: output_validator.py 執行最終檢查，強制添加免責聲明。

4. 智能代理與工具體系 (Agents & Tools)

Agentic SCBR v4.0 的核心在於 Agent 對 Tool 的靈活調用。

4.1 核心 Agents

Agent 名稱

職責

對應 Prompt/程式碼

Gatekeeper Agent (L1)

意圖識別、關鍵詞提取、路由決策

l1_gate_agentic_prompt.txt

Retrieval Agent

查詢重寫、檢索策略優化

core/agentic_retrieval.py

Diagnostician Agent (L2)

案例錨定、辨證推理、收斂判斷

l2_agentic_diagnosis.py

Safety Auditor (L3)

醫療合規性審查、風險阻斷

l3_safety_review_prompt.txt

Reporter Agent (L4)

用戶友善格式化、報告生成

l4_presentation_prompt.txt

4.2 工具集 (Tools)

工具名稱

檔案路徑

功能描述

調用者

Terminology Mgr

utils/terminology_manager.py

中醫術語標準化、同義詞轉換

L1 Agent

Search Engine

core/search_engine.py

執行向量與關鍵字混合檢索

Retrieval Agent

TCM Knowledge

tools/tcm_tools.py

查詢方劑組成、穴位定位、禁忌

L2 Agent

Embedder

llm/embedding.py

文本轉向量服務

Search Engine

5. 安全防護體系 (Security Architecture)

本系統全面實作 OWASP Top 10 for LLM 防護標準。

LLM01 (Prompt Injection): 由 input_sanitizer.py (正則與規則) 和 L1 Agent (語義判斷) 雙重過濾。

LLM02 (Sensitive Info Leak): pii_masker.py 對輸入進行脫敏；output_validator.py 檢查輸出是否洩露系統 Prompt。

LLM05 (Supply Chain): L3 Agent 專門審核生成的醫療建議，禁止輸出具體藥量。

LLM10 (Model Denial of Service): rate_limiter.py 實作 Token Bucket 或計數器限流。

6. 螺旋式會話管理

系統通過 dialog_manager.py 實現獨特的螺旋式 (Spiral) 上下文管理：

累積機制: Context_N = Query_N + History(Summary)。

動態更新: 每一輪的追問回答都會補充到 Context 中，使 L1 和 L2 在下一輪擁有更完整的資訊。

收斂終止: 當 L2 判斷 Coverage Ratio 達標，或達到最大輪次 (max_rounds，定義於 config.py)，螺旋過程終止。

7. 測試與驗證

系統包含完整的自動化測試框架。

測試執行器: debug/agentic_test_runner.py

測試案例: debug/agentic_test_cases.yaml (包含 OWASP 攻擊測試與 TCM 準確度測試)

綜合測試: debug/scbr_comprehensive_test.py 負責端對端 (E2E) 的流程驗證與指標收集。

附註: 本文件對應的程式碼版本為 GitHub 提交雜