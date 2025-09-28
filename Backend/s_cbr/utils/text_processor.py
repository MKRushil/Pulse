# s_cbr/utils/text_processor.py

import jieba
import os
from ..config import TextProcessorConfig

class TextProcessor:
    def __init__(self, cfg: TextProcessorConfig):
        dict_path = cfg.jieba_dict_path
        if dict_path and os.path.exists(dict_path):
            with open(dict_path, 'r', encoding='utf-8') as f:
                lines = f.read().splitlines()
            for w in lines:
                jieba.add_word(w.strip())
            print(f"✅ 已手動載入 jieba 詞典，共 {len(lines)} 行")
        else:
            print(f"⚠️ jieba 詞典路徑無效或不存在: {dict_path}")
        self.stopwords = set(cfg.stopwords)

    def segment_text(self, text: str) -> str:
        if not text:
            return ""
        tokens = [w for w in jieba.cut(text) if w.strip() and w not in self.stopwords]
        return " ".join(tokens)
