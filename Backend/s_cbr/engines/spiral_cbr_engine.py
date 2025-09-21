"""
S-CBR 螺旋推理引擎 v2.0 - 完整 LLM 整合版

整合真實 LLM 調用邏輯、Step1-4 實際實現、三個向量庫檢索和螺旋推理多輪對話邏輯

核心功能：
1. 真實 LLM 調用邏輯
2. Step1-4 的實際實現
3. 三個向量庫（Case、PulsePJ、RPCase）的整合檢索
4. 螺旋推理的多輪對話邏輯
"""

import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging
import openai
import weaviate
from openai import AsyncOpenAI

try:
    from ..utils.spiral_logger import SpiralLogger
    logger = SpiralLogger.get_logger("SpiralCBREngine")
except ImportError:
    logger = logging.getLogger("SpiralCBREngine")

try:
    from ..config.scbr_config import SCBRConfig
except ImportError:
    logger.warning("無法載入 SCBRConfig")
    SCBRConfig = None

try:
    from ..knowledge.rpcase_manager import RPCaseManager
except ImportError:
    logger.warning("無法載入 RPCaseManager")
    RPCaseManager = None

class SpiralCBREngine:
    """
    S-CBR 螺旋推理引擎 v2.0 - 完整版
    
    整合三個向量知識庫：
    - Case: 傳統中醫病例知識庫
    - PulsePJ: 中醫脈象診斷知識庫  
    - RPCase: 螺旋推理回饋案例知識庫
    
    支援完整的螺旋推理流程：
    Step 1: 案例檢索 (Case Retrieval)
    Step 2: 案例適配 (Case Adaptation) 
    Step 3: 方案監控 (Solution Monitoring)
    Step 4: 反饋學習 (Feedback Learning)
    """
    
    def __init__(self):
        """初始化螺旋 CBR 引擎 v2.0"""
        self.logger = logger
        self.config = SCBRConfig() if SCBRConfig else None
        
        # 初始化組件
        self._init_llm_client()
        self._init_weaviate_client()
        self._init_rpcase_manager()
        
        # 推理狀態
        self.conversation_history = []
        self.current_session_id = None
        self.used_cases = []
        
        self.version = "2.0"
        self.logger.info(f"S-CBR 螺旋推理引擎 v{self.version} 初始化完成")
    
    def _init_llm_client(self):
        """初始化 LLM 客戶端"""
        try:
            if self.config:
                # 從配置獲取 LLM 設定
                self.llm_api_url = self.config.get_config("llm.api_url", "https://integrate.api.nvidia.com/v1")
                self.llm_api_key = self.config.get_config("llm.api_key", "")
                self.llm_model = self.config.get_config("llm.model", "meta/llama-3.1-405b-instruct")
            else:
                self.llm_api_url = "https://integrate.api.nvidia.com/v1"
                self.llm_api_key = ""
                self.llm_model = "meta/llama-3.1-405b-instruct"
            
            # 初始化 AsyncOpenAI 客戶端
            self.llm_client = AsyncOpenAI(
                api_key=self.llm_api_key,
                base_url=self.llm_api_url
            )
            
            self.logger.info(f"✅ LLM 客戶端初始化成功: {self.llm_model}")
            
        except Exception as e:
            self.logger.error(f"❌ LLM 客戶端初始化失敗: {e}")
            self.llm_client = None
    
    def _init_weaviate_client(self):
        """初始化 Weaviate 向量資料庫客戶端"""
        try:
            if self.config:
                db_config = self.config.get_database_config()
                weaviate_url = db_config.weaviate_url
                timeout = db_config.weaviate_timeout
            else:
                weaviate_url = "http://localhost:8080"
                timeout = 30
            
            self.weaviate_client = weaviate.Client(
                url=weaviate_url,
                timeout_config=(timeout, timeout)
            )
            
            # 測試連接
            self.weaviate_client.schema.get()
            self.logger.info(f"✅ Weaviate 客戶端連接成功: {weaviate_url}")
            
        except Exception as e:
            self.logger.error(f"❌ Weaviate 客戶端初始化失敗: {e}")
            self.weaviate_client = None
    
    def _init_rpcase_manager(self):
        """初始化 RPCase 管理器"""
        try:
            if RPCaseManager and self.weaviate_client:
                self.rpcase_manager = RPCaseManager(self.weaviate_client)
                self.logger.info("✅ RPCase 管理器初始化成功")
            else:
                self.rpcase_manager = None
                self.logger.warning("RPCase 管理器不可用")
        except Exception as e:
            self.logger.error(f"RPCase 管理器初始化失敗: {e}")
            self.rpcase_manager = None

    async def start_spiral_dialog(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        啟動螺旋推理對話 v2.0
        
        Args:
            query: 查詢參數
                - question: 患者問題描述
                - session_id: 會話ID  
                - round: 當前輪次
                - used_cases: 已使用案例列表
                - continue_spiral: 是否繼續螺旋推理
                
        Returns:
            Dict: 螺旋推理結果
        """
        try:
            # 提取查詢參數
            question = query.get("question", "")
            session_id = query.get("session_id", "")
            current_round = query.get("round", 1)
            used_cases = query.get("used_cases", [])
            patient_ctx = query.get("patient_ctx", {})
            trace_id = query.get("trace_id", "")
            
            self.current_session_id = session_id
            self.used_cases = used_cases
            
            self.logger.info(f"開始螺旋推理 v2.0 - Session: {session_id}, Round: {current_round}")
            self.logger.info(f"已使用案例數: {len(used_cases)}")
            
            # Step 1: 案例檢索 (Case Retrieval)
            self.logger.info(f"Step 1 - 案例檢索 v2.0 (Round {current_round})")
            retrieved_cases = await self._step1_case_retrieval(question, patient_ctx, used_cases)
            
            # Step 2: 案例適配 (Case Adaptation)
            self.logger.info(f"Step 2 - 案例適配 v2.0 (Round {current_round})")
            adapted_solution = await self._step2_case_adaptation(question, patient_ctx, retrieved_cases)
            
            # Step 3: 方案監控 (Solution Monitoring)
            self.logger.info(f"Step 3 - 方案監控 v2.0 (Round {current_round})")
            monitoring_result = await self._step3_solution_monitoring(question, adapted_solution, retrieved_cases)
            
            # Step 4: 反饋學習 (Feedback Learning)
            self.logger.info(f"Step 4 - 反饋學習 v2.0 (Round {current_round})")
            final_result = await self._step4_feedback_learning(question, monitoring_result, retrieved_cases)
            
            self.logger.info(f"螺旋推理 v2.0 完成 - Session: {session_id}, Round: {current_round}")
            
            return final_result
            
        except Exception as e:
            self.logger.error(f"螺旋推理失敗: {str(e)}")
            return {
                "error": True,
                "error_message": str(e),
                "diagnosis": "推理過程發生錯誤",
                "treatment_plan": "請重新嘗試或尋求專業醫師協助",
                "confidence": 0.0,
                "safety_score": 0.0,
                "efficacy_score": 0.0,
                "case_used": "",
                "llm_struct": {"error": str(e)}
            }

    async def _step1_case_retrieval(self, question: str, patient_ctx: Dict[str, Any], used_cases: List[str]) -> Dict[str, Any]:
        """
        Step 1: 案例檢索 - 從三個向量庫檢索相關案例
        
        整合檢索策略：
        1. Case 知識庫 - 傳統中醫病例
        2. PulsePJ 知識庫 - 脈象診斷知識  
        3. RPCase 知識庫 - 螺旋推理回饋案例
        """
        try:
            retrieved_cases = {
                "cases": [],
                "pulse_knowledge": [],
                "feedback_cases": [],
                "total_retrieved": 0
            }
            
            if not self.weaviate_client:
                self.logger.warning("Weaviate 客戶端不可用，使用模擬案例")
                return self._get_mock_cases(question)
            
            # 生成查詢向量
            query_vector = await self._generate_query_vector(question)
            
            # 1. 檢索 Case 知識庫
            try:
                case_results = await self._retrieve_from_case_kb(query_vector, used_cases, limit=3)
                retrieved_cases["cases"] = case_results
                self.logger.info(f"Case 知識庫檢索: {len(case_results)} 個案例")
            except Exception as e:
                self.logger.error(f"Case 知識庫檢索失敗: {e}")
            
            # 2. 檢索 PulsePJ 知識庫  
            try:
                pulse_results = await self._retrieve_from_pulse_kb(query_vector, limit=2)
                retrieved_cases["pulse_knowledge"] = pulse_results
                self.logger.info(f"PulsePJ 知識庫檢索: {len(pulse_results)} 個脈象知識")
            except Exception as e:
                self.logger.error(f"PulsePJ 知識庫檢索失敗: {e}")
            
            # 3. 檢索 RPCase 知識庫
            if self.rpcase_manager:
                try:
                    rpcase_results = await self.rpcase_manager.search_similar_rpcases(question, limit=2)
                    retrieved_cases["feedback_cases"] = rpcase_results
                    self.logger.info(f"RPCase 知識庫檢索: {len(rpcase_results)} 個回饋案例")
                except Exception as e:
                    self.logger.error(f"RPCase 知識庫檢索失敗: {e}")
            
            retrieved_cases["total_retrieved"] = (
                len(retrieved_cases["cases"]) + 
                len(retrieved_cases["pulse_knowledge"]) + 
                len(retrieved_cases["feedback_cases"])
            )
            
            self.logger.info(f"Step 1 完成 - 總檢索案例數: {retrieved_cases['total_retrieved']}")
            
            return retrieved_cases
            
        except Exception as e:
            self.logger.error(f"Step 1 案例檢索失敗: {e}")
            return self._get_mock_cases(question)

    async def _retrieve_from_case_kb(self, query_vector: List[float], used_cases: List[str], limit: int = 3) -> List[Dict[str, Any]]:
        """從 Case 知識庫檢索案例"""
        try:
            # 構建 where 過濾器排除已使用案例
            where_filter = {}
            if used_cases:
                where_filter = {
                    "path": ["case_id"],
                    "operator": "NotEqual",
                    "valueString": used_cases
                }
            
            result = (
                self.weaviate_client.query
                .get("Case", [
                    "case_id", "age", "gender", "chief_complaint", 
                    "present_illness", "diagnosis_main", "treatment_plan", "summary"
                ])
                .with_near_vector({
                    "vector": query_vector,
                    "certainty": 0.75
                })
                .with_where(where_filter) if where_filter else 
                self.weaviate_client.query.get("Case", [
                    "case_id", "age", "gender", "chief_complaint", 
                    "present_illness", "diagnosis_main", "treatment_plan", "summary"
                ]).with_near_vector({
                    "vector": query_vector,
                    "certainty": 0.75
                })
            ).with_limit(limit).do()
            
            cases = result.get("data", {}).get("Get", {}).get("Case", [])
            return cases
            
        except Exception as e:
            self.logger.error(f"Case 知識庫檢索失敗: {e}")
            return []

    async def _retrieve_from_pulse_kb(self, query_vector: List[float], limit: int = 2) -> List[Dict[str, Any]]:
        """從 PulsePJ 脈象知識庫檢索"""
        try:
            result = (
                self.weaviate_client.query
                .get("PulsePJ", [
                    "pulse_id", "pulse_name", "pulse_description",
                    "associated_conditions", "diagnostic_significance", "treatment_approach"
                ])
                .with_near_vector({
                    "vector": query_vector,
                    "certainty": 0.70
                })
                .with_limit(limit)
                .do()
            )
            
            pulses = result.get("data", {}).get("Get", {}).get("PulsePJ", [])
            return pulses
            
        except Exception as e:
            self.logger.error(f"PulsePJ 知識庫檢索失敗: {e}")
            return []

    async def _generate_query_vector(self, text: str) -> List[float]:
        """生成查詢文本的向量表示"""
        try:
            # 使用 OpenAI Embeddings API
            if self.llm_client:
                response = await self.llm_client.embeddings.create(
                    input=text,
                    model="text-embedding-ada-002"
                )
                vector = response.data[0].embedding
                self.logger.debug(f"生成 {len(vector)} 維向量")
                return vector
            else:
                # 降級：返回隨機向量
                import random
                vector = [random.random() for _ in range(1536)]
                self.logger.warning("使用隨機向量替代（LLM客戶端不可用）")
                return vector
                
        except Exception as e:
            self.logger.error(f"向量生成失敗: {e}")
            # 降級：返回零向量
            return [0.0] * 1536

    def _get_mock_cases(self, question: str) -> Dict[str, Any]:
        """獲取模擬案例數據（當向量庫不可用時）"""
        return {
            "cases": [
                {
                    "case_id": "MOCK_CASE_001",
                    "age": 35,
                    "gender": "女",
                    "chief_complaint": "壓力大，失眠多夢",
                    "diagnosis_main": "心腎不交",
                    "treatment_plan": "甘麥大棗湯合交泰丸加減",
                    "summary": "模擬案例：壓力性失眠的中醫治療"
                }
            ],
            "pulse_knowledge": [
                {
                    "pulse_name": "弦脈", 
                    "pulse_description": "脈象如琴弦，端直而長",
                    "associated_conditions": "肝氣鬱結，情志不暢"
                }
            ],
            "feedback_cases": [],
            "total_retrieved": 2
        }

    async def _step2_case_adaptation(self, question: str, patient_ctx: Dict[str, Any], retrieved_cases: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 2: 案例適配 - 使用 LLM 分析檢索案例並適配當前患者
        """
        try:
            if not self.llm_client:
                return self._get_mock_adaptation(retrieved_cases)
            
            # 構建案例適配的 LLM Prompt
            adaptation_prompt = self._build_adaptation_prompt(question, patient_ctx, retrieved_cases)
            
            # 調用 LLM 進行案例適配
            response = await self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {
                        "role": "system", 
                        "content": self._get_tcm_system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": adaptation_prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            llm_response = response.choices[0].message.content
            self.logger.debug(f"LLM 案例適配回應: {llm_response[:200]}...")
            
            # 解析 LLM 回應
            adapted_result = await self._parse_adaptation_response(llm_response, retrieved_cases)
            
            self.logger.info("Step 2 案例適配完成")
            return adapted_result
            
        except Exception as e:
            self.logger.error(f"Step 2 案例適配失敗: {e}")
            return self._get_mock_adaptation(retrieved_cases)

    def _build_adaptation_prompt(self, question: str, patient_ctx: Dict[str, Any], cases: Dict[str, Any]) -> str:
        """構建案例適配的 LLM Prompt"""
        
        # 格式化檢索到的案例
        cases_text = ""
        
        # 1. 傳統案例
        for i, case in enumerate(cases.get("cases", []), 1):
            cases_text += f"\n【病例 {i}】\n"
            cases_text += f"- 年齡性別: {case.get('age', '未知')}歲，{case.get('gender', '未知')}\n"
            cases_text += f"- 主訴: {case.get('chief_complaint', '')}\n"
            cases_text += f"- 診斷: {case.get('diagnosis_main', '')}\n"
            cases_text += f"- 治療方案: {case.get('treatment_plan', '')}\n"
        
        # 2. 脈象知識
        for i, pulse in enumerate(cases.get("pulse_knowledge", []), 1):
            cases_text += f"\n【脈象知識 {i}】\n"
            cases_text += f"- 脈象: {pulse.get('pulse_name', '')}\n"
            cases_text += f"- 描述: {pulse.get('pulse_description', '')}\n"
            cases_text += f"- 相關病症: {pulse.get('associated_conditions', '')}\n"
        
        # 3. 回饋案例
        for i, rpcase in enumerate(cases.get("feedback_cases", []), 1):
            cases_text += f"\n【回饋案例 {i}】\n"
            cases_text += f"- 原始問題: {rpcase.get('original_question', '')}\n"
            cases_text += f"- 診斷結果: {rpcase.get('final_diagnosis', '')}\n"
            cases_text += f"- 治療方案: {rpcase.get('treatment_plan', '')}\n"
            cases_text += f"- 信心度: {rpcase.get('confidence_score', 0.0):.2f}\n"

        prompt = f"""
作為專業中醫師，請基於檢索到的相關案例，為當前患者提供適配的診斷和治療建議。

【當前患者】
問題描述: {question}
患者背景: {json.dumps(patient_ctx, ensure_ascii=False)}

【相關案例參考】
{cases_text}

【任務要求】
1. 綜合分析當前患者症狀與相關案例的相似性和差異性
2. 基於中醫理論，適配現有案例形成針對性的診斷
3. 提出個性化的治療方案，考慮患者特殊情況
4. 評估診斷信心度、治療安全性和預期療效

【回應格式】
請嚴格按照以下JSON格式回應：
{{
    "analysis": "案例分析過程",
    "primary_diagnosis": "主要診斷",
    "secondary_diagnosis": "次要診斷（如有）",
    "treatment_principle": "治療原則",
    "herbal_formula": "推薦方劑",
    "modifications": "加減用藥",
    "lifestyle_advice": "生活建議",
    "confidence_score": 0.85,
    "safety_score": 0.90,
    "efficacy_score": 0.80,
    "case_similarity": "與參考案例的相似度分析",
    "adaptation_notes": "適配說明"
}}
"""
        return prompt

    async def _parse_adaptation_response(self, llm_response: str, cases: Dict[str, Any]) -> Dict[str, Any]:
        """解析 LLM 案例適配回應"""
        try:
            # 嘗試解析 JSON 回應
            if "{" in llm_response and "}" in llm_response:
                json_start = llm_response.find("{")
                json_end = llm_response.rfind("}") + 1
                json_str = llm_response[json_start:json_end]
                
                parsed = json.loads(json_str)
                
                # 標記使用的案例
                used_case_id = None
                if cases.get("cases"):
                    used_case_id = cases["cases"][0].get("case_id", "")
                
                return {
                    "adapted_diagnosis": parsed.get("primary_diagnosis", ""),
                    "treatment_plan": f"{parsed.get('herbal_formula', '')} {parsed.get('modifications', '')}".strip(),
                    "analysis": parsed.get("analysis", ""),
                    "confidence": float(parsed.get("confidence_score", 0.8)),
                    "safety_score": float(parsed.get("safety_score", 0.9)),
                    "efficacy_score": float(parsed.get("efficacy_score", 0.8)),
                    "case_used_id": used_case_id,
                    "case_similarity": parsed.get("case_similarity", ""),
                    "lifestyle_advice": parsed.get("lifestyle_advice", ""),
                    "raw_llm_response": llm_response,
                    "adaptation_success": True
                }
            else:
                # 非 JSON 格式，嘗試文本解析
                return self._parse_text_adaptation(llm_response, cases)
                
        except json.JSONDecodeError as e:
            self.logger.warning(f"LLM JSON 解析失敗: {e}")
            return self._parse_text_adaptation(llm_response, cases)
        except Exception as e:
            self.logger.error(f"適配回應解析失敗: {e}")
            return self._get_mock_adaptation(cases)

    def _parse_text_adaptation(self, text: str, cases: Dict[str, Any]) -> Dict[str, Any]:
        """解析文本格式的 LLM 回應"""
        try:
            lines = text.split('\n')
            diagnosis = ""
            treatment = ""
            
            for line in lines:
                line = line.strip()
                if any(keyword in line for keyword in ["診斷", "病名", "證型"]):
                    diagnosis = line.split(":")[-1].strip() if ":" in line else line
                elif any(keyword in line for keyword in ["治療", "方劑", "用藥"]):
                    treatment = line.split(":")[-1].strip() if ":" in line else line
            
            used_case_id = cases.get("cases", [{}])[0].get("case_id", "") if cases.get("cases") else ""
            
            return {
                "adapted_diagnosis": diagnosis or "需進一步辨證論治",
                "treatment_plan": treatment or "請諮詢專業中醫師",
                "confidence": 0.7,
                "safety_score": 0.8,
                "efficacy_score": 0.7,
                "case_used_id": used_case_id,
                "adaptation_success": True,
                "raw_llm_response": text
            }
            
        except Exception as e:
            self.logger.error(f"文本適配解析失敗: {e}")
            return self._get_mock_adaptation(cases)

    def _get_mock_adaptation(self, cases: Dict[str, Any]) -> Dict[str, Any]:
        """獲取模擬適配結果"""
        used_case_id = cases.get("cases", [{}])[0].get("case_id", "MOCK_CASE") if cases.get("cases") else "MOCK_CASE"
        
        return {
            "adapted_diagnosis": "肝鬱脾虛證",
            "treatment_plan": "逍遙散加減：柴胡10g, 當歸15g, 白芍15g, 白術12g, 茯苓15g, 甘草6g, 生薑3片, 薄荷6g",
            "confidence": 0.75,
            "safety_score": 0.85,
            "efficacy_score": 0.80,
            "case_used_id": used_case_id,
            "adaptation_success": False,
            "mock_reason": "LLM 客戶端不可用"
        }

    async def _step3_solution_monitoring(self, question: str, adapted_solution: Dict[str, Any], cases: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 3: 方案監控 - 評估適配方案的安全性、有效性和合理性
        """
        try:
            if not self.llm_client:
                return self._get_mock_monitoring(adapted_solution)
            
            # 構建監控評估的 Prompt
            monitoring_prompt = self._build_monitoring_prompt(question, adapted_solution, cases)
            
            # 調用 LLM 進行方案監控
            response = await self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {
                        "role": "system", 
                        "content": self._get_monitoring_system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": monitoring_prompt
                    }
                ],
                temperature=0.2,
                max_tokens=1500
            )
            
            monitoring_response = response.choices[0].message.content
            self.logger.debug(f"LLM 方案監控回應: {monitoring_response[:200]}...")
            
            # 解析監控結果
            monitoring_result = await self._parse_monitoring_response(monitoring_response, adapted_solution)
            
            self.logger.info("Step 3 方案監控完成")
            return monitoring_result
            
        except Exception as e:
            self.logger.error(f"Step 3 方案監控失敗: {e}")
            return self._get_mock_monitoring(adapted_solution)

    def _build_monitoring_prompt(self, question: str, solution: Dict[str, Any], cases: Dict[str, Any]) -> str:
        """構建方案監控的 Prompt"""
        
        prompt = f"""
作為中醫臨床專家和安全評估師，請對以下診療方案進行全面的安全性、有效性和合理性評估。

【患者情況】
患者問題: {question}

【當前診療方案】
診斷: {solution.get('adapted_diagnosis', '')}
治療方案: {solution.get('treatment_plan', '')}
初始信心度: {solution.get('confidence', 0.0)}

【評估要求】
1. 安全性評估：檢查是否有配伍禁忌、毒副作用、劑量安全性等
2. 有效性評估：基於中醫理論分析方案的治療針對性和預期效果
3. 合理性評估：評估診斷與治療的邏輯一致性，是否符合中醫辨證論治原則
4. 風險識別：識別潛在的治療風險和注意事項
5. 改進建議：提出優化建議

【回應格式】
請嚴格按照以下JSON格式回應：
{{
    "safety_assessment": {{
        "safety_score": 0.90,
        "safety_issues": ["issue1", "issue2"],
        "contraindications": "禁忌事項",
        "side_effects": "可能副作用"
    }},
    "efficacy_assessment": {{
        "efficacy_score": 0.85,
        "treatment_rationale": "治療理論依據",
        "expected_outcomes": "預期療效",
        "treatment_duration": "預估療程"
    }},
    "rationality_assessment": {{
        "logic_score": 0.88,
        "diagnosis_accuracy": "診斷準確性評估",
        "treatment_consistency": "治療一致性評估"
    }},
    "risk_factors": ["risk1", "risk2"],
    "improvement_suggestions": "改進建議",
    "overall_confidence": 0.85,
    "monitoring_notes": "監控要點"
}}
"""
        return prompt

    async def _parse_monitoring_response(self, response: str, solution: Dict[str, Any]) -> Dict[str, Any]:
        """解析監控評估回應"""
        try:
            # 解析 JSON 回應
            if "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
                
                parsed = json.loads(json_str)
                
                # 提取評估結果
                safety_score = parsed.get("safety_assessment", {}).get("safety_score", 0.85)
                efficacy_score = parsed.get("efficacy_assessment", {}).get("efficacy_score", 0.80)
                overall_confidence = parsed.get("overall_confidence", 0.82)
                
                return {
                    "monitored_diagnosis": solution.get("adapted_diagnosis", ""),
                    "monitored_treatment": solution.get("treatment_plan", ""),
                    "safety_score": float(safety_score),
                    "efficacy_score": float(efficacy_score),
                    "confidence": float(overall_confidence),
                    "safety_issues": parsed.get("safety_assessment", {}).get("safety_issues", []),
                    "risk_factors": parsed.get("risk_factors", []),
                    "improvement_suggestions": parsed.get("improvement_suggestions", ""),
                    "monitoring_success": True,
                    "raw_monitoring_response": response
                }
            else:
                return self._parse_text_monitoring(response, solution)
                
        except json.JSONDecodeError as e:
            self.logger.warning(f"監控 JSON 解析失敗: {e}")
            return self._parse_text_monitoring(response, solution)
        except Exception as e:
            self.logger.error(f"監控回應解析失敗: {e}")
            return self._get_mock_monitoring(solution)

    def _parse_text_monitoring(self, text: str, solution: Dict[str, Any]) -> Dict[str, Any]:
        """解析文本格式的監控回應"""
        # 簡單的文本解析邏輯
        safety_score = 0.85
        efficacy_score = 0.80
        confidence = 0.82
        
        # 尋找評分相關文本
        if "安全" in text:
            if "高" in text or "良好" in text:
                safety_score = 0.90
            elif "低" in text or "風險" in text:
                safety_score = 0.70
        
        return {
            "monitored_diagnosis": solution.get("adapted_diagnosis", ""),
            "monitored_treatment": solution.get("treatment_plan", ""),
            "safety_score": safety_score,
            "efficacy_score": efficacy_score,
            "confidence": confidence,
            "monitoring_success": True,
            "raw_monitoring_response": text
        }

    def _get_mock_monitoring(self, solution: Dict[str, Any]) -> Dict[str, Any]:
        """獲取模擬監控結果"""
        return {
            "monitored_diagnosis": solution.get("adapted_diagnosis", "肝鬱脾虛證"),
            "monitored_treatment": solution.get("treatment_plan", "逍遙散加減"),
            "safety_score": 0.85,
            "efficacy_score": 0.80,
            "confidence": 0.82,
            "monitoring_success": False,
            "mock_reason": "LLM 客戶端不可用"
        }

    async def _step4_feedback_learning(self, question: str, monitoring_result: Dict[str, Any], cases: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 4: 反饋學習 - 整合前三步結果，產生最終診斷和治療建議
        """
        try:
            if not self.llm_client:
                return self._get_mock_final_result(monitoring_result)
            
            # 構建最終整合的 Prompt
            learning_prompt = self._build_learning_prompt(question, monitoring_result, cases)
            
            # 調用 LLM 進行最終整合
            response = await self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {
                        "role": "system", 
                        "content": self._get_learning_system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": learning_prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            learning_response = response.choices[0].message.content
            self.logger.debug(f"LLM 反饋學習回應: {learning_response[:200]}...")
            
            # 解析最終結果
            final_result = await self._parse_learning_response(learning_response, monitoring_result)
            
            self.logger.info("Step 4 反饋學習完成")
            return final_result
            
        except Exception as e:
            self.logger.error(f"Step 4 反饋學習失敗: {e}")
            return self._get_mock_final_result(monitoring_result)

    def _build_learning_prompt(self, question: str, monitoring: Dict[str, Any], cases: Dict[str, Any]) -> str:
        """構建反饋學習的 Prompt"""
        
        prompt = f"""
作為資深中醫專家，請基於完整的螺旋推理過程，為患者提供最終的診療建議和學習反饋。

【患者問題】
{question}

【螺旋推理結果】
診斷: {monitoring.get('monitored_diagnosis', '')}
治療方案: {monitoring.get('monitored_treatment', '')}
安全評分: {monitoring.get('safety_score', 0.85)}
有效評分: {monitoring.get('efficacy_score', 0.80)}
信心度: {monitoring.get('confidence', 0.82)}

【已檢索案例數】
總案例數: {cases.get('total_retrieved', 0)}

【任務要求】
1. 綜合螺旋推理過程，提供最終的診斷結論
2. 完善治療方案，包括具體用藥指導
3. 提供詳細的患者建議和注意事項
4. 評估本次推理的學習價值和可改進點
5. 生成用於螺旋對話的友好回覆

【回應格式】
請嚴格按照以下JSON格式回應：
{{
    "final_diagnosis": "最終診斷",
    "treatment_plan": "完整治療方案",
    "medication_details": "用藥詳情和注意事項",
    "lifestyle_recommendations": "生活方式建議",
    "follow_up_advice": "隨訪建議",
    "safety_score": 0.88,
    "efficacy_score": 0.85,
    "confidence": 0.86,
    "learning_insights": "本次推理的學習洞察",
    "case_used_summary": "使用案例總結",
    "recommendations": "給患者的綜合建議",
    "spiral_dialog": "對話式回覆內容"
}}
"""
        return prompt

    async def _parse_learning_response(self, response: str, monitoring: Dict[str, Any]) -> Dict[str, Any]:
        """解析反饋學習回應"""
        try:
            # 解析 JSON 回應
            if "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
                
                parsed = json.loads(json_str)
                
                return {
                    "diagnosis": parsed.get("final_diagnosis", monitoring.get("monitored_diagnosis", "")),
                    "treatment_plan": parsed.get("treatment_plan", monitoring.get("monitored_treatment", "")),
                    "recommendations": parsed.get("recommendations", ""),
                    "safety_score": float(parsed.get("safety_score", monitoring.get("safety_score", 0.85))),
                    "efficacy_score": float(parsed.get("efficacy_score", monitoring.get("efficacy_score", 0.80))),
                    "confidence": float(parsed.get("confidence", monitoring.get("confidence", 0.82))),
                    "case_used": parsed.get("case_used_summary", ""),
                    "case_used_id": monitoring.get("case_used_id", ""),
                    "spiral_dialog": parsed.get("spiral_dialog", ""),
                    "llm_struct": {
                        "main_dx": parsed.get("final_diagnosis", ""),
                        "treatment": parsed.get("treatment_plan", ""),
                        "medication_details": parsed.get("medication_details", ""),
                        "lifestyle": parsed.get("lifestyle_recommendations", ""),
                        "follow_up": parsed.get("follow_up_advice", ""),
                        "learning_insights": parsed.get("learning_insights", ""),
                        "confidence": float(parsed.get("confidence", 0.82))
                    },
                    "learning_success": True,
                    "raw_learning_response": response
                }
            else:
                return self._parse_text_learning(response, monitoring)
                
        except json.JSONDecodeError as e:
            self.logger.warning(f"學習 JSON 解析失敗: {e}")
            return self._parse_text_learning(response, monitoring)
        except Exception as e:
            self.logger.error(f"學習回應解析失敗: {e}")
            return self._get_mock_final_result(monitoring)

    def _parse_text_learning(self, text: str, monitoring: Dict[str, Any]) -> Dict[str, Any]:
        """解析文本格式的學習回應"""
        lines = text.split('\n')
        diagnosis = monitoring.get("monitored_diagnosis", "")
        treatment = monitoring.get("monitored_treatment", "")
        
        for line in lines:
            line = line.strip()
            if "診斷" in line and ":" in line:
                diagnosis = line.split(":")[-1].strip()
            elif "治療" in line and ":" in line:
                treatment = line.split(":")[-1].strip()
        
        return {
            "diagnosis": diagnosis,
            "treatment_plan": treatment,
            "recommendations": "請按時服藥，注意飲食調理",
            "safety_score": monitoring.get("safety_score", 0.85),
            "efficacy_score": monitoring.get("efficacy_score", 0.80),
            "confidence": monitoring.get("confidence", 0.82),
            "case_used": "基於相似案例適配",
            "llm_struct": {
                "main_dx": diagnosis,
                "treatment": treatment,
                "confidence": monitoring.get("confidence", 0.82)
            },
            "learning_success": True,
            "raw_learning_response": text
        }

    def _get_mock_final_result(self, monitoring: Dict[str, Any]) -> Dict[str, Any]:
        """獲取模擬最終結果"""
        return {
            "diagnosis": monitoring.get("monitored_diagnosis", "肝鬱脾虛證"),
            "treatment_plan": monitoring.get("monitored_treatment", "逍遙散加減調治"),
            "recommendations": "建議：保持心情舒暢，規律作息，按時服藥。如症狀持續請及時就醫。",
            "safety_score": monitoring.get("safety_score", 0.85),
            "efficacy_score": monitoring.get("efficacy_score", 0.80),
            "confidence": monitoring.get("confidence", 0.82),
            "case_used": "參考傳統中醫經典案例",
            "llm_struct": {
                "main_dx": monitoring.get("monitored_diagnosis", "肝鬱脾虛證"),
                "treatment": monitoring.get("monitored_treatment", "逍遙散加減"),
                "confidence": monitoring.get("confidence", 0.82),
                "mock_mode": True
            },
            "learning_success": False,
            "mock_reason": "LLM 客戶端不可用，使用預設診療建議"
        }

    def _get_tcm_system_prompt(self) -> str:
        """獲取中醫系統 Prompt"""
        return """
你是一位經驗豐富的中醫師，擅長中醫辨證論治。請基於以下原則進行診療：

1. 中醫基礎理論：陰陽學說、五行學說、藏象學說、經絡學說
2. 診斷方法：望、聞、問、切四診合參
3. 辨證論治：根據證候特點確定治法方藥
4. 整體觀念：將人體看作有機整體，注重內外環境協調
5. 預防思想：治未病，重視養生保健

診療時應：
- 詳細分析患者症狀，準確辨證
- 選方用藥要有理論依據
- 考慮個體差異，個性化治療
- 注重安全性，避免毒副作用
- 給出明確的用法用量和注意事項
"""

    def _get_monitoring_system_prompt(self) -> str:
        """獲取監控評估系統 Prompt"""
        return """
你是中醫臨床安全評估專家，負責評估診療方案的安全性、有效性和合理性。

評估標準：
1. 安全性：配伍禁忌、毒副作用、劑量安全、特殊人群禁忌
2. 有效性：理法方藥一致性、治療針對性、預期療效
3. 合理性：辨證準確性、用藥邏輯、劑量合理性
4. 風險管理：潛在風險識別、預防措施、監測要點

請客觀、專業地評估，提出具體的改進建議。
"""

    def _get_learning_system_prompt(self) -> str:
        """獲取學習整合系統 Prompt"""
        return """
你是中醫臨床決策專家，負責整合螺旋推理過程，提供最終診療建議。

整合要求：
1. 綜合分析前期推理結果，形成最終診斷
2. 完善治療方案，提供具體指導
3. 給出患者友好的建議和注意事項
4. 評估推理過程的學習價值
5. 生成適合患者理解的對話式回覆

回覆應該：專業而易懂、溫暖而負責、具體而實用。
"""

# 導出
__all__ = ["SpiralCBREngine"]
