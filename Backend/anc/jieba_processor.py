# -*- coding: utf-8 -*-
"""
TCM Jieba Processor
中醫術語 Jieba 分詞處理器
支援白話文、專業術語、病症、習慣詞與古文形式
"""

import jieba
import jieba.posseg as pseg
from typing import List, Dict, Set, Any
from pathlib import Path
import re


class TCMJiebaProcessor:
    """中醫術語 Jieba 分詞處理器"""
    
    # 術語類別映射
    TERM_CATEGORIES = {
        "syndrome": ["證", "感冒", "中風", "痺證", "消渴", "郁證", "虛勞"],
        "zangfu": ["心", "肝", "脾", "肺", "腎", "胃", "膽", "腸", "膀胱", "三焦"],
        "symptom": ["痛", "咳", "嗽", "熱", "寒", "汗", "眩暈", "失眠", "便秘", "腹瀉"],
        "pulse": ["脈", "浮", "沉", "遲", "數", "滑", "澀", "弦", "緊", "細", "洪", "虛", "實", "結", "代"],
        "tongue": ["舌", "苔", "淡", "紅", "絳", "紫", "白", "黃", "膩", "腐", "剝"],
        "treatment": ["清", "補", "瀉", "溫", "涼", "散", "收", "宣", "通", "調"],
    }
    
    def __init__(self, dict_path: Path = None):
        """
        初始化 Jieba 處理器
        
        Args:
            dict_path: 自定義詞典路徑
        """
        # 驗證並規範化詞典路徑
        if dict_path is not None:
            if isinstance(dict_path, str):
                dict_path = Path(dict_path)
            
            if not dict_path.exists():
                print(f"⚠️  指定的詞典路徑不存在: {dict_path}")
                print(f"⚠️  將使用內建預設術語")
                dict_path = None
        
        self.dict_path = dict_path
        self._initialized = False
        self._load_dict()
    
    def _load_dict(self):
        """載入中醫詞典"""
        if self._initialized:
            return
        
        # 載入自定義詞典 (如果存在且有效)
        if self.dict_path is not None and self.dict_path.exists():
            try:
                # 使用 context manager 確保檔案關閉
                with open(self.dict_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        
                        parts = line.split()
                        if len(parts) >= 2:
                            word, freq = parts[0], int(parts[1])
                            jieba.add_word(word, freq=freq)
                        elif len(parts) == 1:
                            jieba.add_word(parts[0], freq=1000)
                
                print(f"✅ 已載入中醫詞典: {self.dict_path}")
                print(f"   檔案大小: {self.dict_path.stat().st_size / 1024:.2f} KB")
                
            except Exception as e:
                print(f"❌ 載入詞典失敗: {e}")
                print(f"⚠️  將使用內建預設術語")
                self._load_default_terms()
        else:
            # 使用內建預設詞典
            if self.dict_path is None:
                print(f"ℹ️  未指定詞典路徑,使用內建預設術語")
            else:
                print(f"⚠️  詞典檔案不存在: {self.dict_path}")
                print(f"⚠️  將使用內建預設術語")
            self._load_default_terms()

        self._initialized = True
    
    def _load_default_terms(self):
        """載入內建中醫術語"""
        default_terms = self._get_default_tcm_terms()
        for term, freq in default_terms:
            jieba.add_word(term, freq=freq)
        print(f"✅ 已載入 {len(default_terms)} 個內建中醫術語")
    
    def _get_default_tcm_terms(self) -> List[tuple]:
        """
        獲取預設中醫術語列表
        返回: [(詞彙, 詞頻), ...]
        """
        terms = []
        
        # ==================== 八綱辨證 ====================
        terms.extend([
            ("表證", 1000), ("裡證", 1000), ("寒證", 1000), ("熱證", 1000),
            ("虛證", 1000), ("實證", 1000), ("陰證", 1000), ("陽證", 1000),
        ])
        
        # ==================== 氣血津液辨證 ====================
        terms.extend([
            ("氣虛", 1000), ("氣滯", 1000), ("氣陷", 800), ("氣逆", 800),
            ("血虛", 1000), ("血瘀", 1000), ("血熱", 800), ("血寒", 800),
            ("陰虛", 1000), ("陽虛", 1000), ("津液不足", 800),
            ("痰濕", 1000), ("痰熱", 800), ("痰飲", 800), ("濕熱", 1000),
        ])
        
        # ==================== 臟腑辨證 ====================
        zangfu_syndromes = [
            # 心系
            "心氣虛", "心血虛", "心陰虛", "心陽虛", "心火亢盛", "痰火擾心", "心血瘀阻",
            # 肺系
            "肺氣虛", "肺陰虛", "風寒束肺", "風熱犯肺", "燥邪犯肺", "痰濕阻肺", "痰熱壅肺",
            # 脾系
            "脾氣虛", "脾陽虛", "脾虛濕困", "寒濕困脾", "濕熱蘊脾",
            # 肝系
            "肝血虛", "肝陰虛", "肝氣鬱結", "肝火上炎", "肝陽上亢", "肝風內動",
            # 腎系
            "腎陰虛", "腎陽虛", "腎氣不固", "腎精不足", "腎不納氣",
            # 胃系
            "胃氣虛", "胃陰虛", "胃寒", "胃熱", "食滯胃脘",
        ]
        terms.extend([(s, 1000) for s in zangfu_syndromes])
        
        # ==================== 六經辨證 ====================
        terms.extend([
            ("太陽病", 1000), ("陽明病", 1000), ("少陽病", 1000),
            ("太陰病", 1000), ("少陰病", 1000), ("厥陰病", 1000),
        ])
        
        # ==================== 衛氣營血辨證 ====================
        terms.extend([
            ("衛分證", 1000), ("氣分證", 1000),
            ("營分證", 1000), ("血分證", 1000),
        ])
        
        # ==================== 三焦辨證 ====================
        terms.extend([
            ("上焦病", 800), ("中焦病", 800), ("下焦病", 800),
        ])
        
        # ==================== 常見病證 ====================
        diseases = [
            "感冒", "咳嗽", "哮喘", "肺炎", "胸痺", "心悸", "不寐", "健忘",
            "眩暈", "中風", "頭痛", "胃痛", "腹痛", "嘔吐", "泄瀉", "痢疾",
            "便秘", "黃疸", "水腫", "淋證", "癃閉", "遺精", "陽痿", "不孕",
            "月經不調", "痛經", "崩漏", "帶下", "妊娠惡阻", "產後腹痛",
            "癮疹", "濕疹", "痤瘡", "痺證", "腰痛", "痿證", "痙證",
            "消渴", "郁證", "癲狂", "癇病", "虛勞", "積聚", "噎膈",
        ]
        terms.extend([(d, 1000) for d in diseases])
        
        # ==================== 脈象 ====================
        pulse_types = [
            "浮脈", "沉脈", "遲脈", "數脈", "滑脈", "澀脈", "虛脈", "實脈",
            "洪脈", "細脈", "弦脈", "緊脈", "緩脈", "濡脈", "弱脈", "散脈",
            "革脈", "牢脈", "芤脈", "伏脈", "動脈", "促脈", "結脈", "代脈",
            "長脈", "短脈", "疾脈", "微脈",
        ]
        terms.extend([(p, 1000) for p in pulse_types])
        
        # ==================== 舌診 ====================
        tongue_terms = [
            "舌質淡紅", "舌質淡白", "舌質紅", "舌質絳紅", "舌質青紫",
            "舌苔薄白", "舌苔厚白", "舌苔薄黃", "舌苔厚黃", "舌苔白膩",
            "舌苔黃膩", "舌苔黃燥", "舌苔少", "舌苔無", "舌苔剝落",
            "舌體胖大", "舌體瘦薄", "舌有齒痕", "舌有裂紋", "舌有瘀點",
            "舌尖紅", "舌邊紅", "舌中黃", "舌根厚",
        ]
        terms.extend([(t, 1000) for t in tongue_terms])
        
        # ==================== 治法 ====================
        treatments = [
            "解表", "清熱", "瀉火", "涼血", "溫裡", "祛寒", "補益", "瀉下",
            "消導", "理氣", "行氣", "破氣", "理血", "活血", "止血", "化瘀",
            "祛風", "散寒", "清暑", "利濕", "化濕", "燥濕", "潤燥", "祛痰",
            "止咳", "平喘", "開竅", "安神", "平肝", "息風", "固澀", "驅蟲",
            "疏風散寒", "疏風清熱", "清熱解毒", "清熱瀉火", "清熱涼血",
            "溫中散寒", "溫經散寒", "溫陽散寒", "益氣健脾", "補血養肝",
            "滋陰降火", "補腎固精", "活血化瘀", "行氣活血", "化痰止咳",
            "健脾利濕", "清熱利濕", "疏肝理氣", "養心安神", "平肝息風",
        ]
        terms.extend([(t, 1000) for t in treatments])
        
        # ==================== 常用方劑 ====================
        formulas = [
            # 解表劑
            "麻黃湯", "桂枝湯", "小青龍湯", "九味羌活湯", "香蘇散",
            "銀翹散", "桑菊飲", "麻杏石甘湯", "柴葛解肌湯",
            # 瀉下劑
            "大承氣湯", "小承氣湯", "調胃承氣湯", "麻子仁丸",
            # 和解劑
            "小柴胡湯", "大柴胡湯", "逍遙散", "四逆散",
            # 清熱劑
            "白虎湯", "竹葉石膏湯", "黃連解毒湯", "清營湯", "犀角地黃湯",
            "普濟消毒飲", "仙方活命飲", "龍膽瀉肝湯", "左金丸",
            # 溫裡劑
            "理中丸", "小建中湯", "吳茱萸湯", "四逆湯", "當歸四逆湯",
            # 補益劑
            "四君子湯", "參苓白朮散", "補中益氣湯", "生脈散", "玉屏風散",
            "四物湯", "當歸補血湯", "歸脾湯", "炙甘草湯",
            "六味地黃丸", "左歸丸", "右歸丸", "金匱腎氣丸",
            # 理氣劑
            "越鞠丸", "半夏厚朴湯", "蘇子降氣湯", "定喘湯",
            # 理血劑
            "桃核承氣湯", "血府逐瘀湯", "補陽還五湯", "溫經湯",
            "小蓟飲子", "槐花散", "黃土湯",
            # 治風劑
            "川芎茶調散", "大秦艽湯", "小活絡丹", "天麻鉤藤飲", "鎮肝息風湯",
            # 祛濕劑
            "平胃散", "藿香正氣散", "茵陳蒿湯", "八正散", "五苓散",
            # 祛痰劑
            "二陳湯", "溫膽湯", "貝母瓜蔞散", "清氣化痰丸",
            # 安神劑
            "朱砂安神丸", "天王補心丹", "酸棗仁湯", "甘麥大棗湯",
        ]
        terms.extend([(f, 1200) for f in formulas])
        
        # ==================== 常用中藥 ====================
        herbs = [
            # 解表藥
            "麻黃", "桂枝", "紫蘇", "生薑", "香薷", "荊芥", "防風", "羌活",
            "白芷", "細辛", "薄荷", "牛蒡子", "蟬蛻", "桑葉", "菊花", "葛根",
            # 清熱藥
            "石膏", "知母", "梔子", "黃芩", "黃連", "黃柏", "龍膽草",
            "生地黃", "玄參", "牡丹皮", "赤芍", "紫草", "金銀花", "連翹",
            "蒲公英", "魚腥草", "白花蛇舌草", "板藍根", "青黛",
            # 瀉下藥
            "大黃", "芒硝", "番瀉葉", "火麻仁", "郁李仁",
            # 祛風濕藥
            "獨活", "威靈仙", "秦艽", "防己", "桑寄生", "五加皮",
            # 化濕藥
            "蒼朮", "厚朴", "廣藿香", "佩蘭", "砂仁", "白豆蔻",
            # 利水滲濕藥
            "茯苓", "豬苓", "澤瀉", "薏苡仁", "車前子", "滑石", "木通",
            "金錢草", "茵陳", "虎杖",
            # 溫裡藥
            "附子", "乾薑", "肉桂", "吳茱萸", "小茴香", "丁香", "高良薑",
            # 理氣藥
            "陳皮", "青皮", "枳實", "枳殼", "木香", "香附", "烏藥", "檀香",
            "沉香", "川楝子", "佛手", "薤白",
            # 消食藥
            "山楂", "神曲", "麥芽", "萊菔子", "雞內金",
            # 止血藥
            "大薊", "小薊", "地榆", "白茅根", "槐花", "側柏葉", "艾葉",
            "三七", "蒲黃", "茜草", "白及", "仙鶴草",
            # 活血化瘀藥
            "川芎", "延胡索", "鬱金", "薑黃", "乳香", "沒藥", "丹參",
            "紅花", "桃仁", "益母草", "牛膝", "雞血藤", "澤蘭", "水蛭",
            # 化痰止咳平喘藥
            "半夏", "天南星", "白附子", "桔梗", "川貝母", "浙貝母",
            "瓜蔞", "竹茹", "竹瀝", "前胡", "杏仁", "紫蘇子", "百部",
            "紫菀", "款冬花", "枇杷葉", "桑白皮", "葶藶子", "白果",
            # 安神藥
            "朱砂", "磁石", "龍骨", "琥珀", "酸棗仁", "柏子仁", "遠志",
            # 平肝息風藥
            "石決明", "珍珠母", "牡蠣", "代赭石", "羚羊角", "牛黃",
            "鉤藤", "天麻", "地龍", "全蠍", "蜈蚣", "僵蠶",
            # 補虛藥
            "人參", "黨參", "太子參", "黃芪", "白朮", "山藥", "甘草",
            "當歸", "白芍", "熟地黃", "阿膠", "何首烏", "龍眼肉",
            "鹿茸", "杜仲", "續斷", "菟絲子", "補骨脂", "益智仁",
            "沙參", "麥門冬", "天門冬", "石斛", "玉竹", "百合", "枸杞子",
            # 收澀藥
            "五味子", "烏梅", "山茱萸", "覆盆子", "桑螵蛸", "金櫻子",
            "蓮子", "芡實", "訶子", "肉豆蔻", "赤石脂",
        ]
        terms.extend([(h, 800) for h in herbs])
        
        # ==================== 藥物劑量單位 ====================
        terms.extend([
            ("克", 500), ("g", 500), ("錢", 500), ("兩", 500),
            ("片", 500), ("枚", 500), ("粒", 500), ("味", 500),
        ])
        
        # ==================== 古文常用詞 ====================
        classical_terms = [
            "病患", "病者", "病人", "素體", "平素", "向來", "夙有",
            "今", "茲因", "緣於", "由於", "遂致", "以致", "致使",
            "診得", "查得", "見", "現", "目下", "時下",
            "脈來", "脈見", "舌見", "舌診", "望其", "按其", "切其",
            "辨為", "證屬", "病機", "當以", "治宜", "法當", "方用",
            "加減", "去", "易", "倍", "酌加", "酌減",
            "水煎服", "頓服", "分服", "日三服", "飯前服", "飯後服",
        ]
        terms.extend([(t, 600) for t in classical_terms])
        
        return terms
    
    def tokenize(self, text: str, mode: str = "precise") -> List[str]:
        """
        對文本進行分詞
        
        Args:
            text: 輸入文本
            mode: 分詞模式 - "precise"(精確), "search"(搜索), "full"(全模式)
        
        Returns:
            分詞結果列表
        """
        if mode == "search":
            return jieba.cut_for_search(text)
        elif mode == "full":
            return jieba.cut(text, cut_all=True)
        else:  # precise
            return list(jieba.cut(text, cut_all=False))
    
    def analyze_case(self, case_text: str) -> Dict[str, Any]:
        """
        分析病例文本，提取各類中醫術語
        
        Args:
            case_text: 病例完整文本
        
        Returns:
            {
                "all_tokens": [...],  # 所有詞彙
                "syndrome": [...],    # 證型術語
                "zangfu": [...],      # 臟腑術語
                "symptom": [...],     # 症狀術語
                ...
            }
        """
        # 分詞
        tokens = self.tokenize(case_text, mode="precise")
        
        # 去除停用詞和標點
        cleaned_tokens = self._clean_tokens(tokens)
        
        # 分類術語
        categorized = {
            "all_tokens": cleaned_tokens,
            "syndrome": [],
            "zangfu": [],
            "symptom": [],
            "pulse": [],
            "tongue": [],
            "herb": [],
            "formula": [],
            "treatment": [],
        }
        
        for token in cleaned_tokens:
            for category, keywords in self.TERM_CATEGORIES.items():
                if any(kw in token for kw in keywords):
                    if token not in categorized[category]:
                        categorized[category].append(token)
        
        return categorized
    
    def _clean_tokens(self, tokens: List[str]) -> List[str]:
        """清理分詞結果"""
        stopwords = self._get_stopwords()
        cleaned = []
        
        for token in tokens:
            # 去除空白和單字符(除非是重要字符)
            token = token.strip()
            if not token or (len(token) == 1 and token not in "心肝脾肺腎胃"):
                continue
            
            # 去除停用詞
            if token in stopwords:
                continue
            
            # 去除純數字和純標點
            if token.isdigit() or not any(c.isalnum() for c in token):
                continue
            
            cleaned.append(token)
        
        return cleaned
    
    def _get_stopwords(self) -> Set[str]:
        """獲取停用詞集合"""
        return {
            "的", "了", "在", "是", "我", "有", "和", "就", "不", "人",
            "都", "一", "一個", "上", "也", "很", "到", "說", "要", "去",
            "你", "會", "著", "沒有", "看", "好", "自己", "這", "但", "這個",
            "個", "與", "或", "等", "及", "以", "為", "於", "之", "而",
        }
    
    def extract_keywords(self, text: str, topk: int = 20) -> List[tuple]:
        """
        提取關鍵詞 (使用 TF-IDF)
        
        Args:
            text: 輸入文本
            topk: 返回前 k 個關鍵詞
        
        Returns:
            [(詞彙, 權重), ...]
        """
        import jieba.analyse
        keywords = jieba.analyse.extract_tags(
            text,
            topK=topk,
            withWeight=True,
            allowPOS=('n', 'nr', 'ns', 'nt', 'nz', 'v', 'vn', 'a', 'ad')
        )
        return keywords


# ==================== 單例模式 ====================
_processor_instance = None

def get_jieba_processor(dict_path: Path = None) -> TCMJiebaProcessor:
    """獲取全局 Jieba 處理器實例"""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = TCMJiebaProcessor(dict_path)
    return _processor_instance