"""
migrate_awards_category.py — додає колонку category до memorial_awards.
Запуск: python migrate_awards_category.py
"""
import pymysql, os
from dotenv import load_dotenv

load_dotenv()
conn = pymysql.connect(
    host=os.getenv('DB_HOST', '127.0.0.1'),
    port=int(os.getenv('DB_PORT', '3306')),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASS', 'root'),
    database=os.getenv('DB_NAME', 'zoryana_pamyat'),
    charset='utf8mb4'
)
cur = conn.cursor()

# Перевіряємо чи колонка вже існує
cur.execute("""
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'memorial_awards' AND COLUMN_NAME = 'category'
""", (os.getenv('DB_NAME', 'zoryana_pamyat'),))
exists = cur.fetchone()[0]

if exists:
    print("Колонка category вже існує — пропускаємо.")
else:
    cur.execute("ALTER TABLE memorial_awards ADD COLUMN category VARCHAR(30) NOT NULL DEFAULT '' AFTER img_file")
    conn.commit()
    print("OK: колонку category додано до memorial_awards.")

conn.close()
