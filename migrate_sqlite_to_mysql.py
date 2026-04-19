"""
Міграція даних з SQLite → MySQL для проєкту "Зоряна Пам'ять"

Запуск:
    python migrate_sqlite_to_mysql.py

Передумови:
    - MySQL/MariaDB запущений (у OpenServer)
    - Налаштовано .env з DB_HOST, DB_USER, DB_PASS, DB_NAME
    - pip install pymysql python-dotenv
    - Файл memorial.db існує у поточній папці
"""
import os
import sys
import sqlite3
import pymysql
import pymysql.cursors
from dotenv import load_dotenv

load_dotenv()

SQLITE_PATH = os.getenv("SQLITE_PATH", "memorial.db")
DB_NAME     = os.getenv("DB_NAME", "zoryana_pamyat")

MYSQL_CFG = {
    "host":        os.getenv("DB_HOST", "127.0.0.1"),
    "port":        int(os.getenv("DB_PORT", "3306")),
    "user":        os.getenv("DB_USER", "root"),
    "password":    os.getenv("DB_PASS", ""),
    "charset":     "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}


def get_sqlite():
    if not os.path.exists(SQLITE_PATH):
        print(f"[ERROR] SQLite файл не знайдено: {SQLITE_PATH}")
        sys.exit(1)
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_mysql():
    try:
        conn = pymysql.connect(**{**MYSQL_CFG, "database": DB_NAME})
        return conn
    except pymysql.err.OperationalError as e:
        print(f"[ERROR] Неможливо підключитись до MySQL: {e}")
        print("  → Перевірте що MariaDB/MySQL запущений у OpenServer")
        print("  → Перевірте .env (DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME)")
        sys.exit(1)


def migrate_table(sqlite_conn, mysql_conn, table: str, pk: str = "id"):
    """Мігрує таблицю з SQLite у MySQL, пропускаючи дублікати."""
    rows = sqlite_conn.execute(f"SELECT * FROM {table}").fetchall()
    if not rows:
        print(f"  [{table}] — порожня, пропущено")
        return 0

    sample = dict(rows[0])
    cols   = list(sample.keys())
    placeholders = ", ".join(["%s"] * len(cols))
    col_names    = ", ".join([f"`{c}`" for c in cols])

    inserted = 0
    skipped  = 0
    with mysql_conn.cursor() as c:
        for row in rows:
            vals = [row[col] for col in cols]
            try:
                c.execute(
                    f"INSERT IGNORE INTO `{table}` ({col_names}) VALUES ({placeholders})",
                    vals
                )
                if c.rowcount > 0:
                    inserted += 1
                else:
                    skipped += 1
            except pymysql.err.IntegrityError:
                skipped += 1
            except Exception as e:
                print(f"  [WARN] Рядок пропущено ({e}): {dict(row)}")
                skipped += 1

    mysql_conn.commit()
    print(f"  [{table}] → {inserted} додано, {skipped} пропущено")
    return inserted


def main():
    print("=" * 55)
    print("  Міграція SQLite → MySQL: Зоряна Пам'ять")
    print("=" * 55)
    print(f"\nДжерело:  {SQLITE_PATH}")
    print(f"Ціль:     MySQL [{MYSQL_CFG['host']}:{MYSQL_CFG['port']}] / {DB_NAME}\n")

    sqlite_conn = get_sqlite()
    mysql_conn  = get_mysql()

    # Перевіряємо наявність таблиць у MySQL
    with mysql_conn.cursor() as c:
        c.execute("SHOW TABLES")
        tables_in_mysql = {row[f"Tables_in_{DB_NAME}"] for row in c.fetchall()}

    required_tables = ["memorials", "likes_log", "users", "colors", "map_labels", "search_logs"]
    missing = [t for t in required_tables if t not in tables_in_mysql]
    if missing:
        print(f"[ERROR] Таблиці відсутні в MySQL: {missing}")
        print("  → Спочатку запустіть сервер (uvicorn Paskal:app) щоб створити структуру БД")
        sys.exit(1)

    print("Міграція таблиць:")
    for table in required_tables:
        migrate_table(sqlite_conn, mysql_conn, table)

    sqlite_conn.close()
    mysql_conn.close()

    print("\n✓ Міграцію завершено!")
    print("  Перезапустіть uvicorn і перевірте http://localhost:8000/")


if __name__ == "__main__":
    main()
