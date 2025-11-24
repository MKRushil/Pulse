# tcm_tools.py
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import time
import random
import logging

# [新增] 設定 Logger
logger = logging.getLogger("TCMTools")

class TCMTools:
    """
    中醫專業資源工具箱 (穩定性增強版)
    """

    # [新增] 隨機 User-Agent 列表，防止單一 UA 被封鎖
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0"
    ]

    @staticmethod
    def _get_headers():
        return {"User-Agent": random.choice(TCMTools.USER_AGENTS)}

    @staticmethod
    def tool_a_standardize_term(term: str) -> str:
        """
        [Tool A] WHO ICD-11 術語標準化工具
        """
        print(f"--- [Tool A] 正在標準化術語: {term} ---")
        # [修改] 增加簡單的重試機制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                query = f"site:icd.who.int/ct11/icd11_mms/zh {term}"
                # [修改] DDGS 有時會 timeout，增加 timeout 參數 (若函式庫支援) 或外層包 try-except
                results = DDGS().text(query, max_results=3)
                
                if not results:
                    return f"未在 ICD-11 找到關於 '{term}' 的直接定義。"
                
                summary = "【ICD-11 參考搜尋結果】:\n"
                for res in results:
                    summary += f"- 標題: {res.get('title', '無標題')}\n  連結: {res.get('href', '#')}\n  摘要: {res.get('body', '無摘要')}\n"
                return summary

            except Exception as e:
                logger.warning(f"Tool A 嘗試第 {attempt+1} 次失敗: {e}")
                time.sleep(1) # 稍作等待
        
        return "Tool A 執行失敗：ICD-11 搜尋服務暫時無法使用。"

    @staticmethod
    def tool_b_syndrome_logic(syndrome_name: str) -> str:
        """
        [Tool B] A+ 醫學百科辨證邏輯工具
        """
        print(f"--- [Tool B] 正在查詢辨證邏輯: {syndrome_name} ---")
        base_url = "http://cht.a-hospital.com/w/"
        target_url = base_url + syndrome_name
        
        try:
            # [修改] 使用隨機 Headers 與 Timeout
            response = requests.get(target_url, headers=TCMTools._get_headers(), timeout=10)
            
            # [修改] 針對 404 進行友善處理
            if response.status_code == 404:
                return f"外部知識庫中未找到 '{syndrome_name}' (404 Not Found)。"
            if response.status_code != 200:
                return f"外部知識庫連線錯誤 (Status: {response.status_code})。"

            soup = BeautifulSoup(response.content, 'html.parser')
            
            # [修改] 增強解析邏輯 (Fallback 機制)
            content_div = soup.find('div', {'id': 'bodyContent'})
            if not content_div:
                # 嘗試備用 ID，有些 wiki 結構不同
                content_div = soup.find('div', {'class': 'mw-parser-output'})
            
            if not content_div:
                return "無法解析頁面結構 (未找到主要內容區塊)。"

            output_text = f"【來源：A+ 醫學百科 - {syndrome_name}】\n"
            target_sections = ["臨床表現", "症狀", "辨證施治", "診斷", "病因", "病機"] # [修改] 增加病因病機關鍵字
            found_data = False

            # [修改] 抓取邏輯優化，避免只抓標題沒抓到內容
            for h2 in content_div.find_all(['h2', 'h3']): # 增加 h3 支援
                headline_text = h2.get_text(strip=True)
                if any(section in headline_text for section in target_sections):
                    found_data = True
                    output_text += f"\n### {headline_text}\n"
                    
                    # 抓取該標題下的所有段落，直到下一個標題
                    next_node = h2.find_next_sibling()
                    node_count = 0
                    while next_node and next_node.name not in ['h2', 'h3'] and node_count < 10: # 限制長度防止抓太多
                        if next_node.name in ['p', 'ul', 'div']:
                            text = next_node.get_text(strip=True)
                            if len(text) > 5: # 過濾空行
                                output_text += f"{text}\n"
                        next_node = next_node.find_next_sibling()
                        node_count += 1
            
            # [修改] 若精確解析失敗，執行兜底策略：抓取前三段文字
            if not found_data:
                paragraphs = content_div.find_all('p', limit=3)
                if paragraphs:
                    output_text += "\n(未找到特定章節，顯示摘要):\n"
                    for p in paragraphs:
                        output_text += p.get_text(strip=True) + "\n"
                else:
                    return "頁面解析成功但未找到相關文字內容。"

            return output_text

        except requests.exceptions.Timeout:
            return "Tool B 連線逾時 (A+百科回應過慢)。"
        except Exception as e:
            return f"Tool B 執行發生未預期錯誤: {str(e)}"

    @staticmethod
    def tool_c_modern_evidence(syndrome_name: str) -> str:
        """
        [Tool C] ETCM 2.0 現代科學對照工具
        """
        print(f"--- [Tool C] 正在查詢現代科學證據: {syndrome_name} ---")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # [修改] 增加 site 關鍵字變體，ETCM 有時索引不全
                query = f"(site:tcmip.cn OR site:ncbi.nlm.nih.gov) {syndrome_name} mechanism"
                results = DDGS().text(query, max_results=3)
                
                if not results:
                    return f"未在 ETCM 或 PubMed 資料庫找到 '{syndrome_name}' 的相關對照。"
                    
                summary = "【現代科學對照參考 (ETCM/PubMed)】:\n"
                for res in results:
                    summary += f"- 相關條目: {res.get('title', '無標題')}\n  連結: {res.get('href', '#')}\n  摘要: {res.get('body', '無摘要')}\n"
                return summary

            except Exception as e:
                logger.warning(f"Tool C 嘗試第 {attempt+1} 次失敗: {e}")
                time.sleep(1)
        
        return "Tool C 執行失敗：搜尋服務暫時無法使用。"
    
class TCMUnifiedToolkit:
    """
    這就是您要的「大插件」。
    L2 只需要呼叫這個類別的方法，它會自動決定怎麼調用 A, B, C。
    """
    def __init__(self):
        self.tools = TCMTools()

    def run_full_validation(self, syndrome_name: str) -> str:
        """
        一鍵執行：同時調用 A, B, C 進行全方位驗證 (適合 Fallback 模式)
        """
        report = f"====== 外部工具庫驗證報告: {syndrome_name} ======\n\n"
        
        # 1. 查標準 (Tool A)
        report += self.tools.tool_a_standardize_term(syndrome_name) + "\n\n"
        
        # 2. 查邏輯 (Tool B) - 這是最重要的，如果有結果，標記為重點
        logic_data = self.tools.tool_b_syndrome_logic(syndrome_name)
        report += logic_data + "\n\n"
        
        # 3. 查科學 (Tool C)
        report += self.tools.tool_c_modern_evidence(syndrome_name) + "\n"
        
        return report

    def look_up_knowledge_only(self, syndrome_name: str) -> str:
        """
        輕量查詢：只查辨證邏輯 (適合 L2 輔助模式)
        """
        return self.tools.tool_b_syndrome_logic(syndrome_name)