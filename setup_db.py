# setup_db.py
import sqlite3
import json
import os

DB_FILE = "utilities.db"

# --- ДАННЫЕ ИЗ ВАШЕГО СТАРОГО CONFIG.PY ---
# Мы используем их как источник для наполнения базы данных
CITIES_DB_OLD = {
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

TARIFFS_DB_OLD = {
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

# --- КОД ДЛЯ СОЗДАНИЯ И ЗАПОЛНЕНИЯ БАЗЫ ---
def setup_database():
    # Удаляем старый файл БД, если он существует, чтобы начать с чистого листа
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"Старый файл '{DB_FILE}' удален.")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # --- 1. Создаем структуру (схему) таблиц ---
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

    # --- 2. Переносим данные из словарей в таблицы ---
    # Сначала все города
    for name, data in CITIES_DB_OLD.items():
        cursor.execute(
            "INSERT INTO cities (name, currency, volume_model, recommendations) VALUES (?, ?, ?, ?)",
            (name, data['currency'], data['volume_model'], json.dumps(data['recommendations']))
        )
    print("Города добавлены.")

    # Потом все уникальные услуги
    all_services = set()
    for city_services in TARIFFS_DB_OLD.values():
        for service_name in city_services.keys():
            all_services.add(service_name)
    
    for service in all_services:
        cursor.execute("INSERT INTO services (name) VALUES (?)", (service,))
    print("Услуги добавлены.")
    
    # Теперь самое главное - тарифы
    # Для удобства сначала получим id городов и услуг
    cities_map = {row[1]: row[0] for row in cursor.execute("SELECT id, name FROM cities").fetchall()}
    services_map = {row[1]: row[0] for row in cursor.execute("SELECT id, name FROM services").fetchall()}

    for city_name, services_data in TARIFFS_DB_OLD.items():
        for service_name, tariff_data in services_data.items():
            city_id = cities_map[city_name]
            service_id = services_map[service_name]
            
            cursor.execute(
                "INSERT INTO tariffs (city_id, service_id, vat, params, pipeline) VALUES (?, ?, ?, ?, ?)",
                (
                    city_id,
                    service_id,
                    tariff_data.get('vat', 0.0),
                    json.dumps(tariff_data.get('params', {})),
                    json.dumps(tariff_data.get('pipeline', []))
                )
            )
    print("Тарифы и правила расчета добавлены.")

    conn.commit()
    conn.close()
    print(f"База данных '{DB_FILE}' успешно создана и заполнена.")

if __name__ == "__main__":
    setup_database()
