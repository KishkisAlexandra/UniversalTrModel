# db_connector.py
import sqlite3
import json

DB_FILE = "utilities.db" # Имя файла нашей базы данных

def dict_factory(cursor, row):
    """Преобразует строки из БД в словари."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def load_config_from_db():
    """
    Основная функция. Подключается к БД и формирует словари CITIES_DB и TARIFFS_DB.
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    # 1. Загружаем CITIES_DB
    CITIES_DB = {}
    cursor.execute("SELECT * FROM cities")
    cities_data = cursor.fetchall()
    for city in cities_data:
        city_name = city['name']
        CITIES_DB[city_name] = {
            'currency': city['currency'],
            'volume_model': city['volume_model'],
            # JSON-строку из БД преобразуем обратно в Python-объект
            'recommendations': json.loads(city['recommendations']),
            'services': [] # Заполним на следующем шаге
        }

    # 2. Загружаем TARIFFS_DB и попутно заполняем 'services' в CITIES_DB
    TARIFFS_DB = {}
    # Используем JOIN, чтобы сразу получить имена города и услуги
    query = """
        SELECT
            c.name as city_name,
            s.name as service_name,
            t.vat,
            t.params,
            t.pipeline
        FROM tariffs t
        JOIN cities c ON t.city_id = c.id
        JOIN services s ON t.service_id = s.id
    """
    cursor.execute(query)
    tariffs_data = cursor.fetchall()

    for tariff in tariffs_data:
        city_name = tariff['city_name']
        service_name = tariff['service_name']

        # Инициализируем словарь для города, если его еще нет
        if city_name not in TARIFFS_DB:
            TARIFFS_DB[city_name] = {}
        
        # Добавляем услугу в список услуг города
        if service_name not in CITIES_DB[city_name]['services']:
            CITIES_DB[city_name]['services'].append(service_name)

        # Собираем правило тарификации
        TARIFFS_DB[city_name][service_name] = {
            'vat': tariff['vat'],
            'params': json.loads(tariff['params']),
            'pipeline': json.loads(tariff['pipeline'])
        }

    conn.close()
    
    # Возвращаем два готовых словаря, которые ожидает остальная часть приложения
    return CITIES_DB, TARIFFS_DB
