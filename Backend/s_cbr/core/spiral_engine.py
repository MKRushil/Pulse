# -*- coding: utf-8 -*-
"""
螺旋推理引擎 - 優化版
"""

from typing import Any, Dict, List, Optional, Tuple
import logging
import json
import asyncio

from ..config import SCBRConfig
from .search_engine import SearchEngine
from ..llm.embedding import EmbedClient
from ..llm.client import LLMClient
from ..utils.text_processor import TextProcessor
from ..utils.logger import get_logger

logger = get_logger("SpiralEngine")

class SpiralEngine:
    """螺旋推理引擎"""
    
    def __init__(
        self,
        config: SCBRConfig,
        search_engine: Optional[SearchEngine] = None,
        embed_client: Optional[EmbedClient] = None,
    ):
        self.cfg = config
        self.SE = search_engine or SearchEngine(self.cfg)
        self.embedder = embed_client or EmbedClient(self.cfg)
        # 正確初始化 LLM 客戶端
        if config.features.enable_llm:
            try:
                self.llm = LLMClient(self.cfg)
                logger.info("✅ LLM 客戶端初始化成功")
            except Exception as e:
                logger.error(f"❌ LLM 客戶端初始化失敗: {e}")
                self.llm = None
        else:
            self.llm = None
            logger.info("LLM 功能已禁用")
        self.text_processor = TextProcessor(self.cfg.text_processor)
        
        # 配置參數
        self.alpha = config.search.hybrid_alpha
        self.top_k = config.search.top_k
        
        logger.info("螺旋推理引擎初始化完成")
    
    async def execute_spiral_cycle(
        self,
        question: str,
        session_id: str,
        round_num: int = 1
    ) -> Dict[str, Any]:
        """
        執行單輪螺旋推理
        """
        logger.info(f"🌀 執行第 {round_num} 輪螺旋推理")
        
        # 文本預處理
        processed_question = self.text_processor.segment_text(question)
        logger.info(f"分詞後問題: {processed_question[:100]}...")
        
        # 1. 生成向量
        qvec = await self._generate_embedding(question)
        
        # 2. 三庫並行檢索
        case_hits, pulse_hits, rpcase_hits = await self._parallel_search(
            question, processed_question, qvec
        )
        
        logger.info(f"📊 檢索結果 - Case: {len(case_hits)}, PulsePJ: {len(pulse_hits)}, RPCase: {len(rpcase_hits)}")
        
        # 3. 選擇最佳案例
        primary, supplement = self._select_best_cases(
            case_hits, pulse_hits, rpcase_hits
        )
        
        # 4. 構建融合句
        fused_sentence = self._build_fused_sentence(primary, supplement)
        
        # 5. LLM 生成診斷
        final_text = await self._generate_diagnosis(
            question, primary, supplement, fused_sentence, round_num
        )
        
        # 6. 構建返回結果
        result = {
            "ok": True,
            "question": question,
            "round": round_num,
            "primary": primary,
            "supplement": supplement,
            "fused_sentence": fused_sentence,
            "final_text": final_text,
            "text": final_text,  # 兼容舊接口
            "answer": final_text,  # 兼容舊接口
            "search_results": {
                "case_count": len(case_hits),
                "pulse_count": len(pulse_hits),
                "rpcase_count": len(rpcase_hits)
            }
        }
        
        return result
    
    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """生成向量"""
        try:
            vec = await self.embedder.embed(text)
            logger.info(f"🧭 生成向量: dim={len(vec)}")
            return vec
        except Exception as e:
            logger.warning(f"生成向量失敗，降級為 BM25: {e}")
            return None
    
    async def _parallel_search(
        self,
        raw_question: str,
        processed_question: str,
        vector: Optional[List[float]]
    ) -> Tuple[List, List, List]:
        """並行執行三庫檢索"""
        
        # 決定使用原始還是處理後的問題
        search_text = processed_question if processed_question else raw_question
        
        # 並行檢索
        results = await asyncio.gather(
            self.SE.hybrid_search(
                index="Case",
                text=search_text,
                vector=vector,
                alpha=self.alpha,
                limit=self.top_k,
                search_fields=["bm25_cjk"],
                return_props=["case_id", "chiefComplaint", "presentIllness", 
                             "pulse_text", "search_text", "diagnosis_main"]
            ),
            self.SE.hybrid_search(
                index="PulsePJ",
                text=search_text,
                vector=vector,
                alpha=self.alpha,
                limit=self.top_k,
                search_fields=["bm25_cjk"],
                return_props=["pid", "name", "category", "symptoms", 
                             "main_disease", "search_text"]
            ),
            self.SE.hybrid_search(
                index="RPCase",
                text=search_text,
                vector=vector,
                alpha=self.alpha,
                limit=self.top_k,
                search_fields=["bm25_text"],
                return_props=["rid", "final_diagnosis", "pulse_tags", 
                             "symptom_tags", "search_text"]
            ),
            return_exceptions=True
        )
        
        # 處理異常
        case_hits = results[0] if not isinstance(results[0], Exception) else []
        pulse_hits = results[1] if not isinstance(results[1], Exception) else []
        rpcase_hits = results[2] if not isinstance(results[2], Exception) else []
        
        return case_hits, pulse_hits, rpcase_hits
    
    def _select_best_cases(
        self,
        case_hits: List[Dict],
        pulse_hits: List[Dict],
        rpcase_hits: List[Dict]
    ) -> Tuple[Optional[Dict], Optional[Dict]]:
        """選擇最佳主案例和補充案例"""
        
        # 獲取 Top-1
        case_top = self._fuse_case(case_hits[0]) if case_hits else None
        rpcase_top = self._fuse_rpcase(rpcase_hits[0]) if rpcase_hits else None
        pulse_top = self._fuse_pulse(pulse_hits[0]) if pulse_hits else None
        
        # 選擇主案例：比較 Case 和 RPCase
        if case_top and rpcase_top:
            case_score = case_top.get("_final", 0)
            rpcase_score = rpcase_top.get("_final", 0)
            
            # 加權比較
            case_weighted = case_score * self.cfg.spiral.case_weight
            rpcase_weighted = rpcase_score * self.cfg.spiral.rpcase_weight
            
            primary = case_top if case_weighted >= rpcase_weighted else rpcase_top
            logger.info(f"主案例選擇: {primary.get('source')} (分數: {primary.get('_final', 0):.3f})")
        else:
            primary = case_top or rpcase_top
        
        # 補充案例總是 PulsePJ
        supplement = pulse_top
        
        return primary, supplement
    
    def _fuse_case(self, hit: Optional[Dict]) -> Optional[Dict]:
        """融合 Case 結果"""
        if not hit:
            return None
        
        case_id = hit.get("case_id", "")
        cc = hit.get("chiefComplaint", "")
        pi = hit.get("presentIllness", "")
        pulse = hit.get("pulse_text", "")
        search_text = hit.get("search_text", "")
        diagnosis = hit.get("diagnosis_main", "")
        
        # 提取關鍵症狀
        symptoms_text = f"{cc} {pi}".strip()
        key_symptoms = self._extract_key_symptoms(search_text)
        
        # 計算分數
        confidence = hit.get("_confidence", 0.0)
        symptom_score = len(key_symptoms) / max(1, len(self.cfg.text_processor.tcm_keywords))
        final_score = confidence * 0.7 + symptom_score * 0.3
        
        return {
            "source": "Case",
            "id": str(case_id),
            "diagnosis": diagnosis,
            "pulse": pulse,
            "symptoms": symptoms_text,
            "_confidence": confidence,
            "_final": final_score,
            "_hits": key_symptoms,
            "raw": hit
        }
    
    def _fuse_rpcase(self, hit: Optional[Dict]) -> Optional[Dict]:
        """融合 RPCase 結果"""
        if not hit:
            return None
        
        rid = hit.get("rid", "")
        diagnosis = hit.get("final_diagnosis", "")
        pulse_tags = hit.get("pulse_tags", [])
        symptom_tags = hit.get("symptom_tags", [])
        
        # 合併症狀
        symptoms = " ".join(symptom_tags) if isinstance(symptom_tags, list) else str(symptom_tags)
        pulse = " ".join(pulse_tags) if isinstance(pulse_tags, list) else str(pulse_tags)
        
        confidence = hit.get("_confidence", 0.0)
        
        return {
            "source": "RPCase",
            "id": str(rid),
            "diagnosis": diagnosis,
            "pulse": pulse,
            "symptoms": symptoms,
            "_confidence": confidence,
            "_final": confidence * self.cfg.spiral.rpcase_weight,
            "_hits": symptom_tags if isinstance(symptom_tags, list) else [],
            "raw": hit
        }
    
    def _fuse_pulse(self, hit: Optional[Dict]) -> Optional[Dict]:
        """融合 PulsePJ 結果"""
        if not hit:
            return None
        
        pid = hit.get("pid", "")
        name = hit.get("name", "")
        symptoms = hit.get("symptoms", [])
        
        # 處理症狀
        if isinstance(symptoms, list):
            symptoms_text = "、".join(symptoms)
        else:
            symptoms_text = str(symptoms)
        
        confidence = hit.get("_confidence", 0.0)
        
        return {
            "source": "PulsePJ",
            "id": str(pid),
            "diagnosis": name,
            "pulse": name,
            "symptoms": symptoms_text,
            "_confidence": confidence,
            "_final": confidence * self.cfg.spiral.pulse_weight,
            "_hits": symptoms if isinstance(symptoms, list) else [],
            "raw": hit
        }
    
    def _extract_key_symptoms(self, text: str) -> List[str]:
        """提取關鍵症狀"""
        if not text:
            return []
        
        found_symptoms = []
        for symptom in self.cfg.text_processor.tcm_keywords:
            if symptom in text:
                found_symptoms.append(symptom)
        
        return found_symptoms[:10]  # 最多返回10個
    
    def _build_fused_sentence(
        self,
        primary: Optional[Dict],
        supplement: Optional[Dict]
    ) -> str:
        """構建融合句"""
        if not primary:
            return "無匹配案例"
        
        parts = []
        parts.append(f"【主案例】{primary['source']}#{primary['id']}")
        
        if primary.get("symptoms"):
            parts.append(f"症狀：{primary['symptoms'][:100]}")
        
        if primary.get("pulse"):
            parts.append(f"脈象：{primary['pulse'][:50]}")
        
        if supplement:
            parts.append(f"【輔助】{supplement['source']}#{supplement['id']}")
            if supplement.get("symptoms"):
                parts.append(f"補充症狀：{supplement['symptoms'][:100]}")
        
        parts.append(f"融合分數：{primary.get('_final', 0):.3f}")
        
        return " | ".join(parts)
    
    async def _generate_diagnosis(
        self,
        question: str,
        primary: Optional[Dict],
        supplement: Optional[Dict],
        fused_sentence: str,
        round_num: int
    ) -> str:
        """生成診斷結果"""
        
        # 如果沒有 LLM 或主案例，使用模板
        if not self.llm or not primary:
            return self._generate_template_diagnosis(
                question, primary, supplement, round_num
            )
        
        try:
            # 構建提示詞
            prompt = self._build_diagnosis_prompt(
                question, primary, supplement, fused_sentence, round_num
            )
            
            # 調用 LLM
            response = await self.llm.chat_complete(
                system_prompt="你是專業的中醫診斷助手，基於案例推理提供診斷建議。",
                user_prompt=prompt,
                temperature=0.3
            )
            
            # 後處理
            diagnosis = self._postprocess_diagnosis(response)
            
            # 格式化輸出
            return self._format_diagnosis_output(
                question, primary, supplement, diagnosis, round_num
            )
            
        except Exception as e:
            logger.error(f"LLM 生成失敗: {e}")
            return self._generate_template_diagnosis(
                question, primary, supplement, round_num
            )
    
    def _build_diagnosis_prompt(
        self,
        question: str,
        primary: Dict,
        supplement: Optional[Dict],
        fused_sentence: str,
        round_num: int
    ) -> str:
        """構建診斷提示詞"""
        
        prompt_parts = [
            f"這是第 {round_num} 輪診斷推理。",
            f"\n患者問題：{question}",
            f"\n參考案例：{fused_sentence}",
            "\n請基於以上資訊，提供：",
            "1. 診斷結果：明確的中醫證型（一句話）",
            "2. 建議：2-3條調理建議（作息、情志、飲食）",
            "\n注意：",
            "- 不要提及舌診相關內容",
            "- 不要開具處方",
            "- 保持簡潔專業"
        ]
        
        return "\n".join(prompt_parts)
    
    def _postprocess_diagnosis(self, llm_response: str) -> Dict[str, str]:
        """後處理 LLM 響應"""
        
        # 過濾舌診相關內容
        if self.cfg.text_processor.ignore_tongue:
            llm_response = self._filter_tongue_content(llm_response)
        
        # 解析診斷和建議
        lines = llm_response.strip().split("\n")
        diagnosis = ""
        advice = []
        
        for line in lines:
            line = line.strip()
            if "診斷" in line or line.startswith("1"):
                diagnosis = line.split("：", 1)[-1].strip()
            elif "建議" in line or line.startswith("2"):
                continue
            elif line and not line.startswith("#"):
                advice.append(line)
        
        return {
            "diagnosis": diagnosis or "證型待定",
            "advice": "\n".join(advice[:3]) or "調理建議待定"
        }
    
    def _filter_tongue_content(self, text: str) -> str:
        """過濾舌診內容"""
        if not text:
            return text
        
        filtered_lines = []
        for line in text.split("\n"):
            if "舌" not in line and "苔" not in line:
                filtered_lines.append(line)
        
        return "\n".join(filtered_lines)
    
    def _format_diagnosis_output(
        self,
        question: str,
        primary: Dict,
        supplement: Optional[Dict],
        diagnosis: Dict[str, str],
        round_num: int
    ) -> str:
        """格式化診斷輸出"""
        
        lines = [
            f"【第 {round_num} 輪診斷】",
            "",
            f"使用案例編號：{primary['id']}",
            "",
            "當前問題：",
            question,
            "",
            "依據過往案例線索：",
        ]
        
        # 添加線索
        if primary.get("_hits"):
            lines.append(f"- 關鍵線索：{'、'.join(primary['_hits'])}")
        if primary.get("pulse"):
            lines.append(f"- 脈象：{primary['pulse']}")
        if primary.get("symptoms"):
            lines.append(f"- 症狀：{primary['symptoms'][:100]}")
        
        if supplement:
            lines.append(f"- 輔助條文：{supplement.get('symptoms', '')[:100]}")
        
        lines.extend([
            "",
            "診斷結果：",
            diagnosis["diagnosis"],
            "",
            "建議：",
            diagnosis["advice"]
        ])
        
        return "\n".join(lines)
    
    def _generate_template_diagnosis(
        self,
        question: str,
        primary: Optional[Dict],
        supplement: Optional[Dict],
        round_num: int
    ) -> str:
        """生成模板診斷（fallback）"""
        
        if not primary:
            return f"第 {round_num} 輪：暫無匹配案例，請補充更多症狀資訊。"
        
        diagnosis = primary.get("diagnosis", "證型待定")
        
        template = f"""【第 {round_num} 輪診斷】

使用案例編號：{primary.get('id', 'NA')}

當前問題：
{question}

診斷結果：
{diagnosis if diagnosis else '證型待定'}

建議：
- 作息：保持規律作息，避免熬夜
- 情志：保持心情舒暢，適當運動
- 飲食：清淡飲食，忌辛辣刺激

匹配度：{primary.get('_final', 0):.1%}"""
        
        return template