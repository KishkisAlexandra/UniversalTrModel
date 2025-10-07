# db_connector.py
import sqlite3
import json
import os

_BASEDIR = os.path.dirname(__file__)
DB_FILE = os.path.join(_BASEDIR, "utilities.db")

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def load_config_from_db():
    if not os.path.exists(DB_FILE):
        raise FileNotFoundError(f"База данных не найдена по пути: {DB_FILE}")

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    # --- ИЗМЕНЕНИЕ: Добавляем heating_months в запрос ---
    CITIES_DB = {}
    cursor.execute("SELECT id, name, currency, volume_model, recommendations, heating_months FROM cities")
    cities_data = cursor.fetchall()
    for city in cities_data:
        city_name = city['name']
        CITIES_DB[city_name] = {
            'currency': city['currency'],
            'volume_model': city['volume_model'],
            'recommendations': json.loads(city['recommendations']),
            # --- ИЗМЕНЕНИЕ: Читаем и преобразуем heating_months ---
            'heating_months': json.loads(city.get('heating_months') or '[]'),
            'services': []
        }

    # Блок загрузки TARIFFS_DB остается без изменений
    TARIFFS_DB = {}
    query = "SELECT c.name as city_name, s.name as service_name, t.vat, t.params, t.pipeline FROM tariffs t JOIN cities c ON t.city_id = c.id JOIN services s ON t.service_id = s.id"
    cursor.execute(query)
    tariffs_data = cursor.fetchall()

    for tariff in tariffs_data:
        city_name = tariff['city_name']
        service_name = tariff['service_name']
        if city_name not in TARIFFS_DB:
            TARIFFS_DB[city_name] = {}
        if service_name not in CITIES_DB[city_name]['services']:
            CITIES_DB[city_name]['services'].append(service_name)
        TARIFFS_DB[city_name][service_name] = {
            'vat': tariff['vat'],
            'params': json.loads(tariff['params']),
            'pipeline': json.loads(tariff['pipeline'])
        }

    conn.close()
    return CITIES_DB, TARIFFS_DB