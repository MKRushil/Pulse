import mysql.connector

# 建立連線
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="0970571228",
    database="patient"
)

cursor = conn.cursor()
cursor.execute("SELECT VERSION()")
result = cursor.fetchone()
print("資料庫版本：", result)

cursor.close()
conn.close()
