# setup_db.py
import sqlite3
import json
import os

DB_FILE = "utilities.db"

# --- ДАННЫЕ ИЗ ВАШЕГО СТАРОГО CONFIG.PY ---
# Мы используем их как источник для наполнения базы данных
CITIES_DATA = {
    "Минск": {
        "currency": "BYN",
        "volume_model": "standard_minsk",
        "recommendations": {
            "Электроэнергия": ("💡", "используйте энергосберегающие лампы и бытовую технику класса A++."),
            "Вода": ("🚰", "установите аэраторы и проверьте трубы на протечки."),
            "Канализация": ("💧", "контролируйте расход воды и исправность сантехники."),
            "Отопление": ("🔥", "закрывайте окна и проверьте терморегуляторы."),
            "Фикс. платежи": ("🏢", "уточните в ЖЭС структуру начислений за техобслуживание.")
        }
    },
    "Лимасол": {
        "currency": "€",
        "volume_model": "standard_limassol",
        "recommendations": {
            "Электроэнергия": ("💡", "используйте таймеры и энергосберегающие приборы."),
            "Вода": ("🚰", "установите аэраторы и контролируйте расход воды."),
            "Интернет": ("🌐", "сравните тарифы и отключите неиспользуемые услуги."),
            "Телефон": ("📞", "оптимизируйте пакеты звонков и мобильный трафик."),
            "Обслуживание": ("🏢", "проверяйте счета за общие услуги и коммунальные платежи.")
        }
    }
}

TARIFFS_DATA = {
    "Минск": {
        "Электроэнергия": {"params": {"subsidy_rate": 0.2412, "full_rate": 0.2969}, "pipeline": [{"operator": "get_volume", "source": "Электроэнергия"}, {"operator": "apply_subsidy", "params_keys": ["subsidy_rate", "full_rate"]}]},
        "Вода": {"params": {"rate": 1.7858}, "pipeline": [{"operator": "get_volume", "source": "Вода"}, {"operator": "multiply_by_param", "param_key": "rate"}]},
        "Канализация": {"params": {"rate": 0.9586}, "pipeline": [{"operator": "get_volume", "source": "Канализация"}, {"operator": "multiply_by_param", "param_key": "rate"}]},
        "Отопление": {"params": {"subsidy_rate": 24.7187, "full_rate": 134.94}, "pipeline": [{"operator": "get_volume", "source": "Отопление"}, {"operator": "apply_subsidy", "params_keys": ["subsidy_rate", "full_rate"]}]},
        "Фикс. платежи": {"params": {"maintenance": 0.0388, "lighting": 0.0249, "waste": 0.2092, "repair": 0.05, "elevator_rate": 0.88, "zero": 0}, "pipeline": [{"operator": "sum_of_steps", "pipelines": [[{"operator": "get_param", "param_key": "area_m2"}, {"operator": "multiply_by_param", "param_key": "maintenance"}], [{"operator": "get_param", "param_key": "area_m2"}, {"operator": "multiply_by_param", "param_key": "lighting"}], [{"operator": "get_param", "param_key": "occupants"}, {"operator": "multiply_by_param", "param_key": "waste"}], [{"operator": "get_param", "param_key": "area_m2"}, {"operator": "multiply_by_param", "param_key": "repair"}], [{"operator": "apply_conditional_value", "check_param": "floor", "condition": "gt", "threshold": 1, "value_if_true": "elevator_rate", "value_if_false": "zero"}, {"operator": "multiply_by_context", "param_key": "occupants"}]]}]}
    },
    "Лимасол": {
        "Электроэнергия": {"vat": 0.19, "params": {"rate": 0.2661}, "pipeline": [{"operator": "get_volume", "source": "Электроэнергия"}, {"operator": "multiply_by_param", "param_key": "rate"}, {"operator": "apply_vat"}]},
        "Вода": {"vat": 0.05, "params": {"base_fee": 22.0, "brackets": [{"from": 1, "to": 40, "rate": 0.9}, {"from": 41, "to": 80, "rate": 1.43}]}, "pipeline": [{"operator": "get_volume", "source": "Вода"}, {"operator": "apply_progressive_rate", "param_key": "brackets"}, {"operator": "add_param", "param_key": "base_fee"}, {"operator": "apply_vat"}]},
        "Интернет": {"vat": 0.19, "params": {"amount": 20}, "pipeline": [{"operator": "get_fixed_amount", "param_key": "amount"}, {"operator": "apply_vat"}]},
        "Телефон": {"vat": 0.19, "params": {"amount": 20}, "pipeline": [{"operator": "get_fixed_amount", "param_key": "amount"}, {"operator": "apply_vat"}]},
        "Обслуживание": {"vat": 0.19, "params": {"min": 45, "max": 125, "avg_coeff": 0.5}, "pipeline": [{"operator": "sum_of_steps", "pipelines": [[{"operator": "get_fixed_amount", "param_key": "min"}], [{"operator": "get_fixed_amount", "param_key": "max"}]]}, {"operator": "multiply_by_param", "param_key": "avg_coeff"}, {"operator": "apply_vat"}]}
    }
}

def setup_database():
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"Старый файл '{DB_FILE}' удален.")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # --- ВОТ ВАШИ "ЧЕРТЕЖИ" (SQL-КОД), ВСТРОЕННЫЕ В СКРИПТ ---
    # Мы используем тройные кавычки """ для удобного написания многострочных команд
    print("Создание таблиц...")
    cursor.execute("""
        CREATE TABLE cities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            currency TEXT NOT NULL,
            volume_model TEXT NOT NULL,
            recommendations TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)
    cursor.execute("""
        CREATE TABLE tariffs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city_id INTEGER NOT NULL,
            service_id INTEGER NOT NULL,
            vat REAL DEFAULT 0.0,
            params TEXT,
            pipeline TEXT,
            FOREIGN KEY (city_id) REFERENCES cities (id),
            FOREIGN KEY (service_id) REFERENCES services (id)
        )
    """)
    print("Таблицы успешно созданы.")

    # --- Дальше идет код для заполнения этих таблиц данными ---
    print("Добавление городов...")
    for name, data in CITIES_DATA.items():
        cursor.execute(
            "INSERT INTO cities (name, currency, volume_model, recommendations) VALUES (?, ?, ?, ?)",
            (name, data['currency'], data['volume_model'], json.dumps(data['recommendations']))
        )
    
    print("Добавление услуг...")
    all_services = set(service for city in TARIFFS_DATA.values() for service in city.keys())
    for service in all_services:
        cursor.execute("INSERT INTO services (name) VALUES (?)", (service,))
    
    print("Добавление тарифов и правил расчета...")
    cities_map = {row[1]: row[0] for row in cursor.execute("SELECT id, name FROM cities").fetchall()}
    services_map = {row[1]: row[0] for row in cursor.execute("SELECT id, name FROM services").fetchall()}

    for city_name, services_data in TARIFFS_DATA.items():
        for service_name, tariff_data in services_data.items():
            cursor.execute(
                "INSERT INTO tariffs (city_id, service_id, vat, params, pipeline) VALUES (?, ?, ?, ?, ?)",
                (cities_map[city_name], services_map[service_name], tariff_data.get('vat', 0.0),
                 json.dumps(tariff_data.get('params', {})), json.dumps(tariff_data.get('pipeline', [])))
            )

    conn.commit()
    conn.close()
    print(f"\nБаза данных '{DB_FILE}' успешно создана и заполнена. Этот скрипт больше не нужен.")

# Эта строка позволяет запустить скрипт из командной строки
if __name__ == "__main__":
    setup_database()
