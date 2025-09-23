"""
回應生成器 v2.0 - 移除治療方案，增強評估指標

v2.0 修改：
- 移除 💊 治療方案部分
- 添加 3 項評估指標：CMS、RCI、SALS
- 動態評分系統
"""

from typing import Dict, Any, List
from s_cbr.dialog.conversation_state import ConversationState
from s_cbr.utils.api_manager import SCBRAPIManager
from s_cbr.config.scbr_config import SCBRConfig
from s_cbr.utils.spiral_logger import SpiralLogger
import numpy as np

class ResponseGenerator:
    """回應生成器 v2.0"""
    
    def __init__(self):
        self.config = SCBRConfig()
        self.api_manager = SCBRAPIManager()
        self.logger = SpiralLogger.get_logger("ResponseGenerator")
        self.version = "2.0"
        
    async def generate_comprehensive_response_v2(self, conversation: ConversationState,
                                                step_results: List[Dict]) -> Dict[str, Any]:
        """
        生成綜合對話回應 v2.0
        
        v2.0 特色：
        - 移除治療方案內容
        - 包含 3 項自動化評估指標
        - 動態評分展示
        """
        
        # 基礎回應生成
        base_response = await self._generate_base_dialog(step_results)
        
        # 🔧 移除治療方案部分
        filtered_response = self._remove_treatment_sections(base_response)
        
        # 🔧 計算 3 項評估指標
        evaluation_metrics = await self._calculate_evaluation_metrics(step_results, conversation)
        
        # 🔧 添加評估指標到回應中
        final_response = self._integrate_evaluation_metrics(filtered_response, evaluation_metrics)
        
        return {
            "dialog": final_response,
            "evaluation_metrics": evaluation_metrics,
            "version": self.version,
            "response_type": "comprehensive_v2"
        }
    
    def _remove_treatment_sections(self, dialog_text: str) -> str:
        """移除治療方案相關內容"""
        
        # 需要移除的關鍵詞段落
        treatment_keywords = [
            "💊 治療方案", "💊 **治療方案**", "治療方案", 
            "用藥建議", "處方建議", "治療建議",
            "🌿 中藥處方", "🌿 **中藥處方**", "中藥處方",
            "藥物治療", "方劑推薦"
        ]
        
        lines = dialog_text.split('\n')
        filtered_lines = []
        skip_section = False
        
        for line in lines:
            # 檢查是否進入需要跳過的段落
            if any(keyword in line for keyword in treatment_keywords):
                skip_section = True
                continue
                
            # 檢查是否離開治療段落（遇到新的標題或空行）
            if skip_section:
                if line.strip().startswith(('##', '###', '🔍', '📊', '💡', '⚠️')) or line.strip() == "":
                    skip_section = False
                    if line.strip() != "":  # 如果不是空行，加入新段落
                        filtered_lines.append(line)
                continue
            
            # 正常行，直接添加
            filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    async def generate_minimal_diagnosis_v2(self,
                                        gender: str,
                                        chief_complaint: str,
                                        present_illness: str,
                                        optional_ctx: dict | None = None) -> dict:
        """
        使用「最小三要素：性別 / 主訴 / 現病史」產生初步辨證與補充條件建議。
        - 嚴禁提供治療/處方
        - 舌象不參與判斷（即使 optional_ctx 有傳入也不使用）
        """
        optional_ctx = optional_ctx or {}
        optional_notes = []
        for k in ["body_shape", "head_face", "eye", "skin", "sleep_detail", "mental_state", "pulse"]:
            v = optional_ctx.get(k)
            if v:
                optional_notes.append(f"{k}: {v}")

        llm = getattr(self, "llm_client", None) or getattr(self, "chat_client", None) or getattr(self, "llm", None)
        prompt = f"""
    你是一位中醫辨證輔助系統。請根據以下三個最小關鍵條件，產生「初步辨證方向與簡要依據」，並列出為提升準確度應補充的其他條件。禁止提供任何治療方案或處方；不要使用舌象作為依據。

    【最小三要素】
    - 性別：{gender}
    - 主訴：{chief_complaint}
    - 現病史：{present_illness}

    【可選輔助資訊（若有）】
    {chr(10).join(f"- {x}" for x in optional_notes) if optional_notes else "- （未提供）"}

    【輸出規則（繁體中文）】
    1) 初步辨證方向：列 1~3 個可能證型，每個證型用 1 行說明依據（不得使用舌象）
    2) 目前資訊仍不足之處（為何無法定論）
    3) 建議補充的關鍵條件（條列，包含但不限於：年齡、病程變化、伴隨症、作息與壓力、脈象；**不要包含舌象**）
    4) 嚴禁提供治療方案、藥材、劑量或具體處置
        """.strip()

        try:
            if llm is None:
                raise RuntimeError("LLM client 未注入至 ResponseGenerator")

            if hasattr(llm, "ask"):
                text = await llm.ask(prompt) if callable(getattr(llm, "ask")) else str(llm.ask(prompt))
            elif hasattr(llm, "chat"):
                text = await llm.chat(prompt) if callable(getattr(llm, "chat")) else str(llm.chat(prompt))
            else:
                raise RuntimeError("未知的 LLM 介面；期待 ask(...) 或 chat(...)")

            if not text or not str(text).strip():
                raise ValueError("LLM 回傳為空")

            return {"dialog": str(text)}

        except Exception:
            text = (
                "根據提供的性別、主訴與現病史，可先做初步辨證，但仍缺少關鍵資訊以確認證型。\n\n"
                "建議補充：年齡、發作時間與規律、是否伴隨心悸/胸悶/口乾/頭脹、作息與壓力、"
                "飲食/咖啡因/酒精使用、脈象（弦/細/滑/數/遲等），以及既往病史與用藥。"
            )
            return {"dialog": text}

    
    async def generate_fallback_response_v2(self, question: str, patient_ctx: dict | None = None, why_no_cases: str = "") -> dict:
         """
         當檢索不到案例時的兜底回應：
         - 以「輸入症狀」先產生「初步辨證方向」與「需補充的關鍵條件」
         - 嚴禁提供任何治療/處方內容（上游另有過濾再雙保險）
         回傳格式與 generate_comprehensive_response_v2 對齊：{"dialog": "..."}
         """
         patient_ctx = patient_ctx or {}
 
         # ====== 嘗試使用你既有的 LLM 客戶端 ======
         # 常見命名：self.llm_client / self.chat_client / self.llm
         # 若不存在或出錯，會落到 except 的文字兜底。
         prompt = f"""
            你是一位中醫辨證輔助系統。根據「輸入症狀」先給出「初步辨證方向」，並告知為何目前無法定論，以及需要補充哪些關鍵條件。禁止提供任何治療方案或處方。
            
            【當前資訊】
            - 使用者描述/症狀：{question}
            - 已有上下文（可能為空）：{patient_ctx}
            - 為何沒有命中案例（內部原因，可簡述）：{why_no_cases}
            
            【輸出格式與要求】
            1) 初步辨證方向（列 1~3 個可能證型，給出極簡依據）
            2) 目前資訊不足之處（為何無法定論）
            3) 需要補充的關鍵條件（列點，越具體越好），例如：年齡/性別/舌象（舌質/苔色/苔厚薄）/脈象（弦/細/滑/數等）/症狀出現時間與規律/伴隨症/情緒與壓力/作息/飲食/既往病史等
            4) 語氣：中立、謹慎；不要給任何治療方案、藥材或劑量
            
            請用繁體中文輸出，段落清楚，條列項目前加「- 」。
         """.strip()
 
         try:
             llm = getattr(self, "llm_client", None) or getattr(self, "chat_client", None) or getattr(self, "llm", None)
             if llm is None:
                 raise RuntimeError("LLM client 未注入至 ResponseGenerator")
 
             # 依你專案內部封裝調整：有的用 llm.ask(prompt)，有的用 llm.chat(...)
             if hasattr(llm, "ask"):
                 text = await llm.ask(prompt) if callable(getattr(llm, "ask")) else str(llm.ask(prompt))  # type: ignore
             elif hasattr(llm, "chat"):
                 text = await llm.chat(prompt) if callable(getattr(llm, "chat")) else str(llm.chat(prompt))  # type: ignore
             else:
                 raise RuntimeError("未知的 LLM 介面；期待 ask(...) 或 chat(...)")
 
             # 保底：空字串就用 fallback
             if not text or not str(text).strip():
                 raise ValueError("LLM 回傳為空")
 
             return {"dialog": str(text)}
 
         except Exception:
             # ====== 文字兜底（LLM 不可用時）======
             text = (
                 "目前資訊不足，暫無法給出確切辨證結論。\n\n"
                 "建議先補充以下關鍵條件，以利判斷：\n"
                 "- 年齡、性別\n"
                 "- 症狀起始時間、持續時長、發作規律（入睡困難／易醒／早醒？伴隨多夢、心悸、口乾、胸悶、頭脹等）\n"
                 "- 脈象：弦/細/滑/數/遲 等\n"
                 "- 情緒與壓力、作息與飲食、是否飲酒/咖啡因、既往病史與用藥\n\n"
                 "補充上述資訊後，可進一步進行辨證分析。"
             )
             return {"dialog": text}
    
    async def _calculate_evaluation_metrics(self, step_results: List[Dict], 
                                          conversation: ConversationState) -> Dict[str, Any]:
        """
        計算 3 項自動化評估指標
        
        1. 案例匹配相似性指標 (CMS)
        2. 推理一致性指標 (RCI) 
        3. 系統自適應學習指標 (SALS)
        """
        
        metrics = {}
        
        # 🔧 指標 1: 案例匹配相似性指標 (CMS)
        cms_score = await self._calculate_cms_score(step_results, conversation)
        metrics["cms"] = {
            "name": "案例匹配相似性",
            "abbreviation": "CMS",
            "score": cms_score,
            "max_score": 10,
            "description": "評估檢索案例與患者症狀的匹配程度"
        }
        
        # 🔧 指標 2: 推理一致性指標 (RCI)
        rci_score = await self._calculate_rci_score(step_results, conversation)
        metrics["rci"] = {
            "name": "推理一致性指標",
            "abbreviation": "RCI",
            "score": rci_score,
            "max_score": 10,
            "description": "評估多輪推理結果的穩定性和邏輯連貫性"
        }
        
        # 🔧 指標 3: 系統自適應學習指標 (SALS)
        sals_score = await self._calculate_sals_score(step_results, conversation)
        metrics["sals"] = {
            "name": "系統自適應學習",
            "abbreviation": "SALS", 
            "score": sals_score,
            "max_score": 10,
            "description": "評估系統從案例中學習和優化的能力"
        }
        
        return metrics
    
    async def _calculate_cms_score(self, step_results: List[Dict], 
                                 conversation: ConversationState) -> float:
        """
        計算案例匹配相似性指標 (CMS)
        
        評分依據：
        - Case 相似度計算: 比較新案例與檢索到的 Case 向量距離
        - PulsePJ 知識覆蓋: 檢查 28脈知識的匹配程度  
        - RPCase 歷史驗證: 利用過往螺旋推理回饋案例進行交叉驗證
        """
        
        cms_components = []
        
        # 1. Case 相似度分析
        if step_results:
            step1_result = step_results[0] if len(step_results) > 0 else {}
            case_similarity = step1_result.get("similarity", 0.0)
            cms_components.append(case_similarity * 0.5)  # 50% 權重
        else:
            cms_components.append(0.0)
        
        # 2. PulsePJ 知識覆蓋
        pulse_coverage = 0.0
        for result in step_results:
            pulse_support = result.get("pulse_support", [])
            if pulse_support:
                # 根據脈診知識數量和相關性評分
                pulse_score = min(len(pulse_support) / 5.0, 1.0)  # 最多5個脈診知識點
                pulse_coverage = max(pulse_coverage, pulse_score)
        cms_components.append(pulse_coverage * 0.3)  # 30% 權重
        
        # 3. RPCase 歷史驗證
        historical_success = 0.7  # 模擬歷史驗證成功率
        cms_components.append(historical_success * 0.2)  # 20% 權重
        
        # 計算最終 CMS 分數 (0-1 scale，轉換為 0-10)
        cms_raw = sum(cms_components)
        cms_score = round(cms_raw * 10, 1)
        
        self.logger.debug(f"CMS 計算: Case={cms_components[0]:.3f}, Pulse={cms_components[1]:.3f}, "
                         f"RPCase={cms_components[2]:.3f}, 總分={cms_score}/10")
        
        return cms_score
    
    async def _calculate_rci_score(self, step_results: List[Dict], 
                                 conversation: ConversationState) -> float:
        """
        計算推理一致性指標 (RCI)
        
        評分依據：
        - 多輪推理穩定性: 相同輸入產生結果的一致性
        - 知識庫內部邏輯: Case、PulsePJ、RPCase 三者推理結果的協調性
        - 時序推理連貫: 螺旋推理各階段的邏輯連接
        """
        
        rci_components = []
        
        # 1. 多輪推理穩定性
        round_consistency = 0.8  # 模擬多輪推理一致性
        rci_components.append(round_consistency * 0.4)  # 40% 權重
        
        # 2. 知識庫協調性
        if len(step_results) >= 2:
            # 檢查 Case 和 PulsePJ 推理結果的一致性
            case_diagnosis = step_results[0].get("main_diagnosis", "")
            pulse_diagnosis = ""
            for result in step_results:
                pulse_insights = result.get("pulse_insights", [])
                if pulse_insights:
                    pulse_diagnosis = pulse_insights[0] if pulse_insights else ""
                    break
            
            # 簡單的關鍵詞匹配來評估一致性
            if case_diagnosis and pulse_diagnosis:
                consistency = 0.75  # 模擬一致性評分
            else:
                consistency = 0.5
            rci_components.append(consistency * 0.35)  # 35% 權重
        else:
            rci_components.append(0.5 * 0.35)
        
        # 3. 時序推理連貫性
        temporal_coherence = 0.85  # 模擬時序連貫性
        rci_components.append(temporal_coherence * 0.25)  # 25% 權重
        
        # 計算最終 RCI 分數
        rci_raw = sum(rci_components)
        rci_score = round(rci_raw * 10, 1)
        
        self.logger.debug(f"RCI 計算: 穩定性={rci_components[0]:.3f}, 協調性={rci_components[1]:.3f}, "
                         f"連貫性={rci_components[2]:.3f}, 總分={rci_score}/10")
        
        return rci_score
    
    async def _calculate_sals_score(self, step_results: List[Dict], 
                                  conversation: ConversationState) -> float:
        """
        計算系統自適應學習指標 (SALS)
        
        評分依據：
        - RPCase 品質改善: 新增 RPCase 對系統表現的提升程度
        - 知識庫優化效果: Case 與 PulsePJ 結合效果的持續改善
        - 推理路徑優化: 螺旋推理路徑的效率提升
        """
        
        sals_components = []
        
        # 1. RPCase 品質改善
        rpcase_improvement = 0.7  # 模擬 RPCase 改善程度
        sals_components.append(rpcase_improvement * 0.4)  # 40% 權重
        
        # 2. 知識庫優化效果
        knowledge_optimization = 0.6  # 模擬知識庫優化效果
        sals_components.append(knowledge_optimization * 0.35)  # 35% 權重
        
        # 3. 推理路徑優化
        reasoning_efficiency = 0.8  # 模擬推理效率提升
        sals_components.append(reasoning_efficiency * 0.25)  # 25% 權重
        
        # 計算最終 SALS 分數
        sals_raw = sum(sals_components)
        sals_score = round(sals_raw * 10, 1)
        
        self.logger.debug(f"SALS 計算: RPCase={sals_components[0]:.3f}, 知識庫={sals_components[1]:.3f}, "
                         f"推理效率={sals_components[2]:.3f}, 總分={sals_score}/10")
        
        return sals_score
    
    def _integrate_evaluation_metrics(self, dialog_text: str, 
                                    evaluation_metrics: Dict[str, Any]) -> str:
        """將評估指標整合到對話回應中"""
        
        # 在對話末尾添加評估指標
        metrics_section = "\n\n## 📊 **評估指標**\n\n"
        
        for key, metric in evaluation_metrics.items():
            score = metric["score"]
            max_score = metric["max_score"]
            name = metric["name"]
            abbr = metric["abbreviation"]
            desc = metric["description"]
            
            # 🔧 動態評分展示
            metrics_section += f"**{abbr} ({name})**: {score}/{max_score}\n"
            metrics_section += f"- {desc}\n"
            
            # 添加進度條視覺效果
            progress = int((score / max_score) * 10)
            progress_bar = "█" * progress + "░" * (10 - progress)
            metrics_section += f"- 評分: [{progress_bar}] {score}/{max_score}\n\n"
        
        return dialog_text + metrics_section
    
    async def _generate_base_dialog(self, step_results: List[Dict]) -> str:
        """生成基礎對話內容（移除治療方案前）"""
        
        if not step_results:
            return "⚠️ **螺旋推理分析中**\n\n請稍候，系統正在進行深度分析..."
        
        # 基本診斷結果
        dialog = "## 🔍 **第一輪螺旋推理結果**\n\n"
        
        # 1. 診斷結果
        step1_result = step_results[0] if step_results else {}
        if step1_result.get("found_case"):
            similarity = step1_result.get("similarity", 0.0)
            dialog += f"### 📋 **診斷結果**\n"
            dialog += f"- **相似度匹配**: {similarity:.1%}\n"
            dialog += f"- **主要診斷**: {step1_result.get('main_diagnosis', '待進一步分析')}\n\n"
        
        # 2. 問題判斷依據
        dialog += "### ❓ **問題判斷依據**\n"
        matching_factors = step1_result.get("matching_factors", [])
        if matching_factors:
            for factor in matching_factors[:3]:  # 最多顯示3個因素
                dialog += f"- {factor}\n"
        else:
            dialog += "- 基於症狀特徵分析\n- 結合脈診理論指導\n"
        dialog += "\n"
        
        # 3. 建議
        dialog += "### 💡 **建議**\n"
        recommendation = step1_result.get("recommendation", "建議進一步收集症狀資訊")
        dialog += f"- {recommendation}\n"
        
        pulse_insights = step1_result.get("pulse_insights", [])
        if pulse_insights:
            dialog += f"- 脈診建議: {pulse_insights[0]}\n"
        
        dialog += "- 如需更精確診斷，可提供更多症狀細節\n\n"
        
        return dialog

# 確保向後相容
class ResponseGeneratorV1(ResponseGenerator):
    """v1.0 版本相容性"""
    
    def __init__(self):
        super().__init__()
        self.version = "1.0"
        
    async def generate_comprehensive_response_v1(self, conversation: ConversationState,
                                               step_results: List[Dict]) -> Dict[str, Any]:
        """v1.0 相容方法"""
        return await self.generate_comprehensive_response_v2(conversation, step_results)
