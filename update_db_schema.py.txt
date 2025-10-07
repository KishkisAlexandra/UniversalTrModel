# update_db_schema.py
import sqlite3
import json

DB_FILE = "utilities.db"
print(f"Начинаем обновление схемы для '{DB_FILE}'...")

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

try:
    # 1. Добавляем новую колонку 'heating_months' в таблицу 'cities'
    cursor.execute("ALTER TABLE cities ADD COLUMN heating_months TEXT")
    print("Колонка 'heating_months' успешно добавлена в таблицу 'cities'.")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("Колонка 'heating_months' уже существует. Пропускаем...")
    else:
        raise e

# 2. Заполняем данными эту колонку для Минска
heating_months_for_minsk = json.dumps([1, 2, 3, 4, 10, 11, 12])
cursor.execute(
    "UPDATE cities SET heating_months = ? WHERE name = ?",
    (heating_months_for_minsk, "Минск")
)
print("Данные по отопительному сезону для Минска обновлены.")

# 3. Заполняем пустыми данными для других городов, чтобы избежать ошибок
cursor.execute(
    "UPDATE cities SET heating_months = '[]' WHERE heating_months IS NULL"
)
print("Пустые данные по отопительному сезону добавлены для остальных городов.")

conn.commit()
conn.close()

print("\nОбновление схемы базы данных успешно завершено!")