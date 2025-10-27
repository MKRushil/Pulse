# -*- coding: utf-8 -*-
"""
Backend/s_cbr/core/output_formatter.py
固定輸出模板 - 結構化診斷報告生成
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from ..utils.logger import get_logger

logger = get_logger("OutputFormatter")

class OutputFormatter:
    """診斷輸出格式化器"""
    
    def __init__(self):
        logger.info("✅ 輸出格式化器初始化")
    
    # ==================== 主輸出模板 ====================
    def format_diagnosis_output(
        self,
        session_id: str,
        round_num: int,
        question: str,
        accumulated_symptoms: List[str],
        new_symptoms: List[str],
        syndrome_result: Dict[str, Any],
        pathogenesis: Dict[str, Any],
        suggestions: List[str],
        convergence_metrics: Dict[str, float],
        next_questions: List[str] = None,
        case_reference: Dict[str, Any] = None
    ) -> str:
        """
        生成完整的結構化診斷報告
        
        模板結構：
        1. 當前問題（標記新增）
        2. 辨證結果（主證、病機、病位）
        3. 關鍵依據（本輪新命中）
        4. 調理建議（治則 + 生活作息）
        5. 收斂指標條
        6. 下一步追問（高鑑別問題）
        """
        lines = []
        
        # ==================== 標題 ====================
        lines.append("=" * 60)
        lines.append(f"【第 {round_num} 輪中醫辨證診斷報告】")
        lines.append(f"會話 ID: {session_id}")
        lines.append(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        lines.append("")
        
        # ==================== 1. 當前問題 ====================
        lines.append("📋 一、當前問題")
        lines.append("-" * 60)
        
        if round_num == 1:
            lines.append(f"【初診主訴】")
            lines.append(f"{question}")
        else:
            lines.append(f"【本輪補充】")
            lines.append(f"{question}")
            lines.append("")
            lines.append(f"【累積症狀】")
            
            # 標記新增症狀
            for symptom in accumulated_symptoms:
                if symptom in new_symptoms:
                    lines.append(f"  • {symptom} ✨（新增）")
                else:
                    lines.append(f"  • {symptom}")
        
        lines.append("")
        
        # ==================== 2. 辨證結果 ====================
        lines.append("🏥 二、辨證結果")
        lines.append("-" * 60)
        
        # 主證
        primary_syndrome = syndrome_result.get("primary_syndrome", "待定")
        primary_confidence = syndrome_result.get("confidence", 0.0)
        
        lines.append(f"【主要證型】{primary_syndrome}")
        lines.append(f"  置信度: {primary_confidence:.1%} {self._confidence_bar(primary_confidence)}")
        
        # 次證（如果有）
        secondary_syndromes = syndrome_result.get("secondary_syndromes", [])
        if secondary_syndromes:
            lines.append("")
            lines.append(f"【次要證型】")
            for idx, syndrome in enumerate(secondary_syndromes[:2], 1):
                sec_conf = syndrome_result.get("secondary_scores", {}).get(syndrome, 0.0)
                lines.append(f"  {idx}. {syndrome} ({sec_conf:.1%})")
        
        # 病機分析
        if pathogenesis:
            lines.append("")
            lines.append(f"【病機分析】")
            
            if "etiology" in pathogenesis and pathogenesis["etiology"]:
                lines.append(f"  • 病因: {', '.join(pathogenesis['etiology'])}")
            
            if "location" in pathogenesis and pathogenesis["location"]:
                lines.append(f"  • 病位: {', '.join(pathogenesis['location'])}")
            
            if "nature" in pathogenesis and pathogenesis["nature"]:
                lines.append(f"  • 病性: {', '.join(pathogenesis['nature'])}")
            
            if "trend" in pathogenesis:
                lines.append(f"  • 病勢: {pathogenesis['trend']}")
        
        lines.append("")
        
        # ==================== 3. 關鍵依據 ====================
        lines.append("🔍 三、關鍵依據")
        lines.append("-" * 60)
        
        key_clues = syndrome_result.get("key_clues", {})
        
        if key_clues:
            # 核心症狀
            if "core_symptoms" in key_clues and key_clues["core_symptoms"]:
                lines.append(f"【核心症狀】")
                for symptom in key_clues["core_symptoms"][:5]:
                    lines.append(f"  ✓ {symptom}")
            
            # 舌脈證據
            if "tongue_pulse" in key_clues and key_clues["tongue_pulse"]:
                lines.append("")
                lines.append(f"【舌脈證據】")
                for evidence in key_clues["tongue_pulse"]:
                    lines.append(f"  ✓ {evidence}")
            
            # 本輪新命中
            if round_num > 1 and new_symptoms:
                lines.append("")
                lines.append(f"【本輪新增依據】")
                for symptom in new_symptoms[:3]:
                    lines.append(f"  🆕 {symptom}")
        else:
            lines.append("  暫無明確關鍵依據")
        
        lines.append("")
        
        # ==================== 4. 調理建議 ====================
        lines.append("💡 四、調理建議")
        lines.append("-" * 60)
        
        if suggestions:
            for idx, suggestion in enumerate(suggestions[:3], 1):
                lines.append(f"{idx}. {suggestion}")
        else:
            lines.append("  （待補充更多資訊後提供）")
        
        lines.append("")
        
        # ==================== 5. 收斂指標 ====================
        lines.append("📊 五、診斷收斂狀態")
        lines.append("-" * 60)
        
        convergence = convergence_metrics.get("overall_convergence", 0.0)
        stability = convergence_metrics.get("case_stability", 0.0)
        coverage = convergence_metrics.get("evidence_coverage", 0.0)
        confidence = convergence_metrics.get("confidence", 0.0)
        
        lines.append(f"【綜合收斂度】 {convergence:.1%} {self._convergence_bar(convergence)}")
        lines.append("")
        lines.append(f"  案例穩定度: {stability:.1%} {self._mini_bar(stability)}")
        lines.append(f"  症狀覆蓋率: {coverage:.1%} {self._mini_bar(coverage)}")
        lines.append(f"  證型置信度: {confidence:.1%} {self._mini_bar(confidence)}")
        
        # 收斂狀態判定
        if convergence >= 0.90:
            lines.append("")
            lines.append("  ✅ 診斷已達收斂標準，建議可依此調理")
        elif convergence >= 0.75:
            lines.append("")
            lines.append("  ⚠️  診斷基本穩定，建議補充1-2個症狀提高準確度")
        else:
            lines.append("")
            lines.append("  ℹ️  診斷尚未收斂，建議繼續補充症狀資訊")
        
        lines.append("")
        
        # ==================== 6. 下一步追問 ====================
        if next_questions and convergence < 0.90:
            lines.append("❓ 六、建議補充資訊（選擇1-2項回答）")
            lines.append("-" * 60)
            
            for idx, question in enumerate(next_questions[:3], 1):
                lines.append(f"{idx}. {question}")
            
            lines.append("")
        
        # ==================== 參考案例 ====================
        if case_reference:
            lines.append("📚 參考案例")
            lines.append("-" * 60)
            lines.append(f"  案例編號: {case_reference.get('id', 'N/A')}")
            lines.append(f"  來源庫: {case_reference.get('source', 'N/A')}")
            lines.append(f"  匹配度: {case_reference.get('_final', 0.0):.1%}")
            lines.append("")
        
        # ==================== 結尾 ====================
        lines.append("=" * 60)
        lines.append("💬 如需繼續補充症狀，請直接描述")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    # ==================== 醫師版專業報告 ====================
    def format_professional_diagnosis_report(
        self,
        session_id: str,
        round_num: int,
        question: str,
        accumulated_symptoms: List[str],
        new_symptoms: List[str],
        syndrome_result: Dict[str, Any],
        pathogenesis: Dict[str, Any],
        suggestions: List[str],
        convergence_metrics: Dict[str, float],
        next_questions: List[str] = None,
        case_reference: Dict[str, Any] = None
    ) -> str:
        """
        生成醫師版專業辨證推理報告
        
        強調:
        - 四診合參
        - 辨證思路
        - 病機描述
        - 收斂解釋
        - 無對話語氣,無emoji
        """
        lines = []
        
        # ==================== 標題 ====================
        lines.append("=" * 60)
        lines.append(f"【第 {round_num} 輪辨證推理報告】")
        lines.append(f"會話ID：{session_id}")
        lines.append(f"時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        lines.append("")
        
        # ==================== 一、主訴 ====================
        lines.append("一、主訴")
        lines.append("")
        
        # 提取主症狀構建主訴
        chief_symptoms = accumulated_symptoms[:5] if accumulated_symptoms else []
        if chief_symptoms:
            # 構建專業主訴格式
            complaint_parts = []
            for symptom in chief_symptoms:
                complaint_parts.append(symptom)
            
            # 加入脈象資訊
            tongue_pulse = syndrome_result.get("key_clues", {}).get("tongue_pulse", [])
            if tongue_pulse:
                complaint_parts.extend(tongue_pulse)
            
            lines.append("、".join(complaint_parts) + "。")
        else:
            lines.append(question)
        
        lines.append("")
        
        # ==================== 二、四診綜合 ====================
        lines.append("二、四診綜合")
        lines.append("")
        
        # 從症狀中推斷四診資訊
        inspection = self._infer_inspection(accumulated_symptoms)
        auscultation = self._infer_auscultation(accumulated_symptoms)
        inquiry = self._infer_inquiry(accumulated_symptoms, question)
        palpation = self._infer_palpation(accumulated_symptoms, syndrome_result)
        
        if inspection:
            lines.append(f"- 望診：{inspection}")
        if auscultation:
            lines.append(f"- 聞診：{auscultation}")
        if inquiry:
            lines.append(f"- 問診：{inquiry}")
        if palpation:
            lines.append(f"- 切診：{palpation}")
        
        if not (inspection or auscultation or inquiry or palpation):
            lines.append("- 四診資訊待補充完善")
        
        lines.append("")
        
        # ==================== 三、辨證思路 ====================
        lines.append("三、辨證思路")
        lines.append("")
        
        # 構建辨證思路段落
        reasoning = self._build_syndrome_reasoning(
            syndrome_result, 
            pathogenesis, 
            accumulated_symptoms,
            convergence_metrics
        )
        lines.append(reasoning)
        lines.append("")
        
        # ==================== 四、治法 ====================
        lines.append("四、治法")
        lines.append("")
        
        treatment_principle = self._extract_treatment_principle(
            syndrome_result.get("primary_syndrome", ""),
            pathogenesis
        )
        lines.append(treatment_principle)
        lines.append("")
        
        # ==================== 五、評估 ====================
        lines.append("五、評估")
        lines.append("")
        
        # 症狀覆蓋率
        coverage = convergence_metrics.get("evidence_coverage", 0.0)
        coverage_level = self._get_coverage_level(coverage)
        lines.append(f"- 症狀覆蓋率：{coverage_level}（{coverage:.1%}）")
        
        # 病機一致性
        consistency = convergence_metrics.get("consistency", 0.0)
        consistency_level = self._get_consistency_level(consistency)
        lines.append(f"- 病機一致性：{consistency_level}")
        
        # 收斂度
        convergence = convergence_metrics.get("overall_convergence", 0.0)
        convergence_note = self._get_convergence_note(convergence, round_num)
        lines.append(f"- 收斂度：{convergence:.1%}（{convergence_note}）")
        
        lines.append("")
        
        # ==================== 六、後續建議 ====================
        lines.append("六、後續建議")
        lines.append("")
        
        if convergence >= 0.90:
            lines.append("辨證已基本收斂,可據此制定治療方案。")
        else:
            if next_questions:
                suggestion_text = "請補充" + "與".join(self._translate_questions_to_items(next_questions)) + "，以利下一輪螺旋推理。"
                lines.append(suggestion_text)
            else:
                lines.append("請補充更多四診資訊,以提高辨證準確度。")
        
        lines.append("")
        
        # ==================== 資料來源 ====================
        if case_reference:
            source_line = f"資料來源：案例 {case_reference.get('id', 'N/A')} ({case_reference.get('source', 'TCMCase')})"
            lines.append(source_line)
            lines.append("")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)

    # ==================== 輔助方法(醫師版專用) ====================

    def _infer_inspection(self, symptoms: List[str]) -> str:
        """從症狀推斷望診資訊"""
        inspection_clues = []
        
        # 氣色相關
        if any(s in symptoms for s in ["疲倦", "乏力", "氣虛"]):
            inspection_clues.append("氣色略淡")
        if any(s in symptoms for s in ["面紅", "煩熱"]):
            inspection_clues.append("面色潮紅")
        if any(s in symptoms for s in ["面黃", "納差"]):
            inspection_clues.append("面色萎黃")
        
        # 精神狀態
        if any(s in symptoms for s in ["失眠", "多夢", "心悸"]):
            inspection_clues.append("神情疲憊")
        
        return "、".join(inspection_clues) if inspection_clues else ""

    def _infer_auscultation(self, symptoms: List[str]) -> str:
        """從症狀推斷聞診資訊"""
        auscultation_clues = []
        
        # 語聲相關
        if any(s in symptoms for s in ["氣虛", "乏力"]):
            auscultation_clues.append("語聲低微")
        if any(s in symptoms for s in ["咽痛", "咳嗽"]):
            auscultation_clues.append("語音嘶啞")
        
        # 呼吸相關
        if any(s in symptoms for s in ["氣短", "喘息"]):
            auscultation_clues.append("呼吸急促")
        
        return "、".join(auscultation_clues) if auscultation_clues else ""

    def _infer_inquiry(self, symptoms: List[str], question: str) -> str:
        """從症狀推斷問診資訊"""
        inquiry_parts = []
        
        # 情志相關
        if any(s in symptoms for s in ["失眠", "多夢", "心煩"]):
            inquiry_parts.append("思慮過度")
        if "失眠" in symptoms:
            inquiry_parts.append("心煩不寐")
        
        # 飲食相關
        if any(s in symptoms for s in ["納差", "腹脹"]):
            inquiry_parts.append("納食不香")
        
        # 二便相關
        if "便溏" in symptoms:
            inquiry_parts.append("大便溏瀉")
        
        return "、".join(inquiry_parts) if inquiry_parts else ""

    def _infer_palpation(self, symptoms: List[str], syndrome_result: Dict) -> str:
        """從症狀推斷切診(脈象)資訊"""
        pulse_info = syndrome_result.get("key_clues", {}).get("tongue_pulse", [])
        
        if pulse_info:
            return "、".join([p for p in pulse_info if "脈" in p])
        
        # 從症狀推斷可能的脈象
        inferred_pulse = []
        if any(s in symptoms for s in ["氣虛", "乏力"]):
            inferred_pulse.append("脈細弱")
        if any(s in symptoms for s in ["熱", "煩"]):
            inferred_pulse.append("脈數")
        if any(s in symptoms for s in ["肝鬱", "脅痛"]):
            inferred_pulse.append("脈弦")
        
        return "、".join(inferred_pulse) if inferred_pulse else ""

    def _build_syndrome_reasoning(
        self,
        syndrome_result: Dict,
        pathogenesis: Dict,
        symptoms: List[str],
        convergence_metrics: Dict
    ) -> str:
        """構建辨證思路段落"""
        reasoning_parts = []
        
        # 病因病機
        primary_syndrome = syndrome_result.get("primary_syndrome", "")
        
        # 分析病因
        etiology_hints = []
        if "虛" in primary_syndrome:
            etiology_hints.append("素體虛弱")
        if any(s in symptoms for s in ["失眠", "多夢", "心煩"]):
            etiology_hints.append("長期勞心傷脾")
        if "氣" in primary_syndrome or "血" in primary_syndrome:
            etiology_hints.append("氣血生化不足")
        
        reasoning_parts.append("患者" + "，".join(etiology_hints) if etiology_hints else "患者")
        
        # 病機分析
        if pathogenesis:
            location = pathogenesis.get("location", [])
            nature = pathogenesis.get("nature", [])
            
            if location:
                reasoning_parts.append(f"病位在{' '.join(location[:2])}")
            if nature:
                reasoning_parts.append(f"病性屬{' '.join(nature[:2])}")
        
        # 證型判斷
        if primary_syndrome:
            reasoning_parts.append(f"為「{primary_syndrome}」證")
        
        # 病機屬性
        if "虛" in primary_syndrome:
            reasoning_parts.append("病機屬虛")
        elif "實" in primary_syndrome:
            reasoning_parts.append("病機屬實")
        
        return "，".join(reasoning_parts) + "。"

    def _extract_treatment_principle(self, primary_syndrome: str, pathogenesis: Dict) -> str:
        """提取治法"""
        # 根據證型返回治法
        treatment_map = {
            "心脾兩虛": "補益心脾，養血安神",
            "肝鬱氣滯": "疏肝理氣，調暢氣機",
            "陰虛火旺": "滋陰降火，清心安神",
            "脾胃虛弱": "健脾益氣，和胃消食",
            "肝腎陰虛": "滋補肝腎，養陰清熱",
            "氣血兩虛": "補益氣血，調和營衛",
            "痰濕內阻": "健脾化濕，理氣化痰",
            "血瘀": "活血化瘀，通絡止痛"
        }
        
        # 精確匹配
        for syndrome_key, treatment in treatment_map.items():
            if syndrome_key in primary_syndrome:
                return treatment
        
        # 模糊匹配
        if "虛" in primary_syndrome:
            return "補益正氣，扶正祛邪"
        elif "實" in primary_syndrome:
            return "祛邪扶正，標本兼治"
        elif "鬱" in primary_syndrome:
            return "疏肝解鬱，調暢氣機"
        else:
            return "辨證施治，調和陰陽"

    def _get_coverage_level(self, coverage: float) -> str:
        """獲取覆蓋率等級"""
        if coverage >= 0.90:
            return "高"
        elif coverage >= 0.70:
            return "中等"
        elif coverage >= 0.50:
            return "尚可"
        else:
            return "待提高"

    def _get_consistency_level(self, consistency: float) -> str:
        """獲取一致性等級"""
        if consistency >= 0.85:
            return "優良"
        elif consistency >= 0.70:
            return "良好"
        elif consistency >= 0.55:
            return "尚可"
        else:
            return "待改善"

    def _get_convergence_note(self, convergence: float, round_num: int) -> str:
        """獲取收斂度註解"""
        if convergence >= 0.90:
            return "辨證已收斂"
        elif convergence >= 0.75:
            return "辨證基本明確"
        elif convergence >= 0.50:
            return "初步建立辨證方向"
        else:
            if round_num == 1:
                return "首輪診斷，待補充資訊"
            else:
                return "辨證尚不明確，需繼續收集資訊"

    def _translate_questions_to_items(self, questions: List[str]) -> List[str]:
        """將追問轉換為專業術語"""
        items = []
        for q in questions[:3]:
            if "舌" in q:
                items.append("舌象")
            elif "脈" in q:
                items.append("脈象")
            elif "大便" in q or "小便" in q:
                items.append("二便情況")
            elif "睡眠" in q or "失眠" in q:
                items.append("睡眠詳情")
            elif "飲食" in q:
                items.append("飲食狀況")
            elif "寒熱" in q:
                items.append("寒熱傾向")
            else:
                items.append("相關症狀")
        return items



    def format_from_roc(self, roc: Dict) -> str:
        """
        從 ROC 生成格式化輸出
        """
        lines = []
        meta = roc.get("meta", {})
        
        # 標題
        lines.append("=" * 60)
        lines.append(f"【第 {meta.get('round', 1)} 輪中醫辨證診斷報告】")
        lines.append(f"會話 ID: {meta.get('session_id', '')[:8]}...")
        lines.append(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        lines.append("")
        
        # 1. 辨證結果
        pattern_reasoning = roc.get("pattern_reasoning", {})
        if pattern_reasoning:
            lines.append("🔍 一、辨證分析")
            lines.append("-" * 60)
            
            primary = pattern_reasoning.get("primary_pattern", {})
            lines.append(f"【主證】{primary.get('label', '待定')} (置信度: {primary.get('p_score', 0):.1%})")
            
            if pattern_reasoning.get("eight_principles"):
                lines.append(f"【八綱】{'/'.join(pattern_reasoning['eight_principles'])}")
            
            if pattern_reasoning.get("zangfu"):
                lines.append(f"【臟腑】{'/'.join(pattern_reasoning['zangfu'])}")
            
            lines.append("")
        
        # 2. 診斷結果
        diagnosis_reasoning = roc.get("diagnosis_reasoning", {})
        if diagnosis_reasoning:
            lines.append("💊 二、診斷建議")
            lines.append("-" * 60)
            
            lines.append(f"【病名】{diagnosis_reasoning.get('tcm_disease', '待定')}")
            lines.append(f"【病機】{diagnosis_reasoning.get('pathomechanism', '待明')}")
            lines.append(f"【治則】{' '.join(diagnosis_reasoning.get('treatment_principle', []))}")
            
            lines.append("")
        
        # 3. 案例證據（Top-3 結構化）
        evidence = roc.get("evidence", {})
        cases = evidence.get("cases", [])
        if cases:
            lines.append("📚 三、案例佐證（Top-3）")
            lines.append("-" * 60)
            
            for case in cases[:3]:
                lines.append(f"{case['rank']}. {case['case_id']} (相似度: {case['similarity']:.2f})")
                
                # 顯示片段
                snippets = case.get("snippets", [])
                if snippets:
                    lines.append(f"   片段: {snippets[0]}")
                
                # 顯示證型標籤
                pattern_tags = case.get("pattern_tags", [])
                if pattern_tags:
                    lines.append(f"   證型: {' '.join(pattern_tags)}")
                
                lines.append("")
        
        # 4. 收斂狀態
        scores = roc.get("scores", {})
        if scores:
            lines.append("📊 四、診斷收斂狀態")
            lines.append("-" * 60)
            
            final = scores.get("Final", 0.0)
            lines.append(f"【綜合置信度】{final:.1%} {self._confidence_bar(final)}")
            lines.append("")
            
            lines.append(f"  RCI (檢索指數): {scores.get('RCI', 0):.1%}")
            lines.append(f"  CMS (收斂度): {scores.get('CMS', 0):.1%}")
            lines.append(f"  CSC (一致性): {scores.get('CSC', 0):.1%}")
            lines.append(f"  CAS (案例符合): {scores.get('CAS', 0):.1%}")
            
            if final >= 0.90:
                lines.append("")
                lines.append("  ✅ 診斷已達收斂標準，建議可依此調理")
            elif final >= 0.75:
                lines.append("")
                lines.append("  ⚠️ 診斷基本穩定，建議補充1-2個症狀")
            else:
                lines.append("")
                lines.append("  ℹ️ 診斷尚未收斂，建議繼續補充症狀")
            
            lines.append("")
        
        # 5. 下一步建議
        next_turn = roc.get("next_turn", {})
        questions = next_turn.get("questions", [])
        if questions and scores.get("Final", 0) < 0.90:
            lines.append("❓ 五、建議補充資訊")
            lines.append("-" * 60)
            
            for idx, q in enumerate(questions, 1):
                lines.append(f"{idx}. {q}")
            
            lines.append("")
        
        return "\n".join(lines)

    # ==================== 簡潔版輸出 ====================
    def format_concise_output(
        self,
        round_num: int,
        primary_syndrome: str,
        confidence: float,
        key_symptoms: List[str],
        suggestions: List[str],
        convergence: float
    ) -> str:
        """
        生成簡潔版診斷報告（用於 API 返回）
        """
        lines = []
        
        lines.append(f"【第 {round_num} 輪診斷】")
        lines.append("")
        lines.append(f"證型: {primary_syndrome} (置信度 {confidence:.0%})")
        lines.append("")
        
        if key_symptoms:
            lines.append(f"依據: {', '.join(key_symptoms[:5])}")
            lines.append("")
        
        lines.append("建議:")
        for idx, suggestion in enumerate(suggestions[:3], 1):
            lines.append(f"{idx}. {suggestion}")
        
        lines.append("")
        lines.append(f"收斂度: {convergence:.0%} {self._mini_bar(convergence)}")
        
        return "\n".join(lines)
    
    # ==================== 進度條生成 ====================
    def _convergence_bar(self, value: float, length: int = 30) -> str:
        """生成收斂度進度條"""
        filled = int(value * length)
        bar = "█" * filled + "░" * (length - filled)
        
        if value >= 0.90:
            icon = "✅"
        elif value >= 0.75:
            icon = "⚠️"
        else:
            icon = "🔄"
        
        return f"[{bar}] {icon}"
    
    def _mini_bar(self, value: float, length: int = 20) -> str:
        """生成小型進度條"""
        filled = int(value * length)
        return "[" + "█" * filled + "░" * (length - filled) + "]"
    
    def _confidence_bar(self, confidence: float) -> str:
        """生成置信度條"""
        if confidence >= 0.85:
            return "⭐⭐⭐⭐⭐"
        elif confidence >= 0.70:
            return "⭐⭐⭐⭐"
        elif confidence >= 0.55:
            return "⭐⭐⭐"
        elif confidence >= 0.40:
            return "⭐⭐"
        else:
            return "⭐"
    
    # ==================== JSON 格式輸出 ====================
    def format_json_output(
        self,
        session_id: str,
        round_num: int,
        syndrome_result: Dict[str, Any],
        convergence_metrics: Dict[str, float],
        suggestions: List[str],
        formatted_text: str
    ) -> Dict[str, Any]:
        """
        生成 JSON 格式診斷結果（用於 API）
        """
        return {
            "session_id": session_id,
            "round": round_num,
            "timestamp": datetime.now().isoformat(),
            "diagnosis": {
                "primary_syndrome": syndrome_result.get("primary_syndrome"),
                "confidence": syndrome_result.get("confidence"),
                "secondary_syndromes": syndrome_result.get("secondary_syndromes", []),
                "pathogenesis": syndrome_result.get("pathogenesis", {})
            },
            "convergence": {
                "overall": convergence_metrics.get("overall_convergence"),
                "stability": convergence_metrics.get("case_stability"),
                "coverage": convergence_metrics.get("evidence_coverage"),
                "confidence": convergence_metrics.get("confidence"),
                "converged": convergence_metrics.get("overall_convergence", 0) >= 0.90
            },
            "suggestions": suggestions,
            "formatted_report": formatted_text,
            "continue_available": convergence_metrics.get("overall_convergence", 0) < 0.90
        }