# setup_db.py (Финальная версия для создания чистого фундамента)
import sqlite3
import json
import os

DB_FILE = "utilities.db"

CITIES_DATA = {
    "Минск": {"currency": "BYN", "volume_model": "standard_minsk", "recommendations": {"Электроэнергия": ["💡", "Используйте энергосберегающие лампы."], "Вода": ["🚰", "Установите аэраторы."], "Отопление": ["🔥", "Проверьте терморегуляторы."]}},
    "Лимасол": {"currency": "€", "volume_model": "standard_limassol", "recommendations": {"Электроэнергия": ["💡", "Используйте таймеры."], "Вода": ["🚰", "Контролируйте расход воды."]}}
}
SERVICES = ["Электроэнергия", "Вода", "Канализация", "Отопление", "Фикс. платежи", "Интернет", "Телефон", "Содержание дома", "Аренда", "Газ", "IPTV"]

def setup_database():
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Создаем таблицы
    cursor.execute("CREATE TABLE cities (id INTEGER PRIMARY KEY, name TEXT UNIQUE, currency TEXT, volume_model TEXT, recommendations TEXT, heating_months TEXT)")
    cursor.execute("CREATE TABLE services (id INTEGER PRIMARY KEY, name TEXT UNIQUE)")
    cursor.execute("CREATE TABLE tariffs (id INTEGER PRIMARY KEY, city_id INTEGER, service_id INTEGER, vat REAL DEFAULT 0.0, params TEXT, pipeline TEXT, FOREIGN KEY (city_id) REFERENCES cities (id), FOREIGN KEY (service_id) REFERENCES services (id))")

    # Наполняем города
    for name, data in CITIES_DATA.items():
        heating_months = [1, 2, 3, 4, 10, 11, 12] if name == "Минск" else []
        cursor.execute("INSERT INTO cities (name, currency, volume_model, recommendations, heating_months) VALUES (?, ?, ?, ?, ?)",
                       (name, data['currency'], data['volume_model'], json.dumps(data['recommendations']), json.dumps(heating_months)))

    # Наполняем услуги
    for service in SERVICES:
        cursor.execute("INSERT INTO services (name) VALUES (?)", (service,))

    conn.commit()
    conn.close()
    print(f"База данных '{DB_FILE}' успешно создана с базовой структурой.")

if __name__ == "__main__":
    setup_database()