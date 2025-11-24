# s_cbr/utils/terminology_manager.py

'''
單例模式 (Singleton) 的管理器，負責維護熱更新的詞彙表。
'''

import os
import json
from typing import Set
from threading import Lock

class TerminologyManager:
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(TerminologyManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # 設定詞庫檔案路徑
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(os.path.dirname(__file__), "C:\work\系統-中醫\Pulse-project\Backend\s_cbr\data\dynamic_tcm_terms.json")
        self.terms: Set[str] = set()
        self._load_terms()
        self._initialized = True
    
    def _load_terms(self):
            """載入詞庫 (合併模式)"""
            if os.path.exists(self.db_path):
                try:
                    with open(self.db_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # [關鍵修改] 使用 update 而不是直接賦值，確保與記憶體現有數據合併
                        disk_terms = set(data.get("terms", []))
                        self.terms.update(disk_terms)
                except Exception as e:
                    print(f"載入詞庫失敗 (將使用現有記憶體數據): {e}")
            else:
                # 如果檔案不存在，建立空的或使用預設值
                if not self.terms:
                    self.terms = {"心悸", "氣短"} # 最小種子
                    self._save_terms()

    def _save_terms(self):
        """保存詞庫到硬碟 (原子寫入)"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # [修改] 讀取現有檔案，確保不覆蓋手動編輯
            current_disk_terms = set()
            if os.path.exists(self.db_path):
                try:
                    with open(self.db_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        current_disk_terms = set(data.get("terms", []))
                except:
                    pass
            
            # 合併記憶體與硬碟
            all_terms = self.terms.union(current_disk_terms)
            
            # 寫入
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump({"terms": list(all_terms), "count": len(all_terms)}, f, ensure_ascii=False, indent=2)
            
            # 更新記憶體
            self.terms = all_terms
            print(f"💾 [TerminologyManager] 已同步寫入 ({len(self.terms)} 詞)")
            
        except Exception as e:
            print(f"❌ 保存詞庫失敗: {e}")

    def is_term(self, word: str) -> bool:
        """檢查是否為標準術語 (O(1) 複雜度)"""
        return word in self.terms
        
    def add_term(self, word: str):
        """學習新詞彙"""
        if word and len(word) > 1:
            # 直接呼叫 save，讓 save 負責合併邏輯
            if word not in self.terms:
                self.terms.add(word)
                self._save_terms()
                print(f"📖 [TerminologyManager] 學習新詞: {word}")

    def get_density(self, word_list: list) -> float:
        """計算一組詞中有多少是標準術語"""
        if not word_list: return 0.0
        hits = sum(1 for w in word_list if w in self.terms)
        return hits / len(word_list)