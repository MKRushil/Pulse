"""
診斷 MonitoringAgent 導入問題
"""

import sys
import os

# 添加當前目錄到 Python 路徑
sys.path.insert(0, os.getcwd())

print("=== 診斷開始 ===")

# 1. 檢查文件是否存在
file_path = r's_cbr/agents/monitoring_agent.py'
print(f"檢查文件: {file_path}")
if os.path.exists(file_path):
    print("✅ 文件存在")
    
    # 2. 檢查文件內容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"文件大小: {len(content)} 字符")
    print("文件前100字符:")
    print(repr(content[:100]))
    
    # 3. 檢查語法
    try:
        compile(content, file_path, 'exec')
        print("✅ 語法檢查通過")
    except SyntaxError as e:
        print(f"❌ 語法錯誤: {e}")
        print(f"錯誤位置: 第{e.lineno}行, 第{e.offset}列")
        
    
    # 4. 測試執行
    try:
        namespace = {}
        exec(content, namespace)
        if 'MonitoringAgent' in namespace:
            print("✅ MonitoringAgent 類定義成功")
        else:
            print("❌ MonitoringAgent 類未定義")
            print(f"可用名稱: {list(namespace.keys())}")
    except Exception as e:
        print(f"❌ 執行錯誤: {e}")

else:
    print("❌ 文件不存在")

print("=== 診斷結束 ===")
