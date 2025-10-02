# engine.py
from config import TARIFFS_DB, HOUSE_COEFS, REALISM_UPLIFT, CITIES_DB

# --- КОНКРЕТНЫЕ СТРАТЕГИИ РАСЧЕТА ОБЪЕМОВ ---
# Вся специфичная математика живет здесь, в изолированных функциях.
def _calculate_volumes_minsk(area_m2, occupants, month, behavior_factor, config):
    heating_months = config.get("heating_months", [])
    elec = (60.0 + 75.0 * occupants + 0.5 * area_m2) * behavior_factor
    water = 4.5 * occupants * behavior_factor
    heat_monthly = (0.15 * area_m2) / len(heating_months) if month in heating_months and heating_months else 0.0
    return {"Электроэнергия": elec, "Вода": water, "Канализация": water, "Отопление": heat_monthly}

def _calculate_volumes_limassol(area_m2, occupants, month, behavior_factor, config):
    elec = (3.0 * area_m2 + 150.0 * occupants) * behavior_factor
    water = (4.0 * occupants) * behavior_factor
    return {"Электроэнергия": elec, "Вода": water}

# --- РЕЕСТР ДОСТУПНЫХ СТРАТЕГИЙ ---
# Движок будет обращаться к этому словарю по имени стратегии из config.py
VOLUME_CALCULATION_STRATEGIES = {
    "standard_minsk": _calculate_volumes_minsk,
    "standard_limassol": _calculate_volumes_limassol,
}

# --- УНИВЕРСАЛЬНЫЙ ДВИЖОК РАСЧЕТА ОБЪЕМОВ ---
# Этот движок больше не содержит if/elif и не знает о существовании "Минска".
def calculate_volumes(city, area_m2, occupants, month, behavior_factor):
    city_config = CITIES_DB.get(city, {})
    model_name = city_config.get("volume_model", "")
    
    # Выбираем нужную функцию-стратегию из реестра
    strategy_function = VOLUME_CALCULATION_STRATEGIES.get(model_name)
    
    if strategy_function:
        # Если стратегия найдена, вызываем ее
        return strategy_function(area_m2, occupants, month, behavior_factor, city_config)
    else:
        # Если для города не указана модель, или модель не найдена, возвращаем пустоту
        return {}

# ... (остальная часть engine.py с calculate_costs и т.д. остается без изменений) ...
