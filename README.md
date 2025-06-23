# main.py
| 路由                     | 功能說明                 |
| ---------------------- | -------------------- |
| `POST /api/case/save`  | 儲存病歷 JSON（含時間與 ID）   |
| `POST /api/diagnose`   | 執行病歷摘要與模型推理          |
| `GET /api/result/list` | 列出歷史診斷結果             |
| `POST /api/query`      | 查詢（會自動選擇 A/B 案例推理流程） |
| `GET /`                | 回傳前端首頁 index.html    |
| `GET /static/...`      | 掛載靜態前端檔案             |

# cases/case_storage.py

功能模組化流程
1.接收前端表單（符合你提供的結構）
2.儲存病歷 JSON 至 ./data/（含時間戳與身分末四碼）  
3.自動執行診斷（呼叫 diagnose_case()）
4.自動上傳至向量庫（呼叫 upload_case_vector()，可含摘要與推理權重）
5.回傳完整診斷結果與檔名路徑供前端確認


# llm/prompt_builder.py

"""
Prompt 組裝模組：專責產生送給 LLM 的多種 prompt 需求
包含：
1. build_prompt_from_case           —— 標準病歷摘要→診斷（主病/次病/權重）
2. build_spiral_prompt_from_cases   —— 多案例CBR比對推理
3. build_custom_prompt              —— 輸入自訂指令+摘要(暫時不啟用)
4. prompt_template                  —— 主格式外部化，方便之後用 template.txt 管理(暫時不啟用)
"""