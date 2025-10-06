# config.py

# 1. Глобальные константы, которые не хранятся в БД
SCENARIOS = {"Экономный": 0.85, "Средний": 1.0, "Расточительный": 1.25}
HOUSE_COEFS = {"Новый": {"heating": 1.0, "electricity": 1.0}, "Средний": {"heating": 1.05, "electricity": 1.05}, "Старый": {"heating": 1.1, "electricity": 1.05}}
REALISM_UPLIFT = 1.07


# 2. Импортируем и вызываем наш загрузчик из БД
from db_connector import load_config_from_db

try:
    # Главное действие: загружаем конфигурацию из базы данных
    CITIES_DB, TARIFFS_DB = load_config_from_db()
except Exception as e:
    # Если БД не найдена или произошла ошибка, создаем пустые словари,
    # чтобы приложение не "упало" при запуске.
    print(f"ОШИБКА: Не удалось загрузить конфигурацию из БД. {e}")
    print("Убедитесь, что вы создали и заполнили базу данных 'utilities.db'.")
    CITIES_DB, TARIFFS_DB = {}, {}
