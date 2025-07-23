import mysql.connector
import os

# 建立連線，從環境變數讀取資料庫設定
conn = mysql.connector.connect(
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "patient"),
)

cursor = conn.cursor()
cursor.execute("SELECT VERSION()")
result = cursor.fetchone()
print("資料庫版本：", result)

cursor.close()
conn.close()
