# engine.py
from config import CITIES_DB, TARIFFS_DB, HOUSE_COEFS, REALISM_UPLIFT

# --- Функции расчета объемов ---
def calculate_volumes(city, area_m2, occupants, month, behavior_factor):
    """Единая точка входа для расчета объемов потребления."""
    volume_model = CITIES_DB.get(city, {}).get("volume_model", "")

    if volume_model == "standard_minsk":
        return _calculate_volumes_minsk(area_m2, occupants, month, behavior_factor)
    elif volume_model == "standard_limassol":
        return _calculate_volumes_limassol(area_m2, occupants, behavior_factor)
    return {}

def _calculate_volumes_minsk(area_m2, occupants, month, behavior_factor):
    heating_months = CITIES_DB["Минск"]["heating_months"]
    elec = (60.0 + 75.0 * occupants + 0.5 * area_m2) * behavior_factor
    water = 4.5 * occupants * behavior_factor
    heat_monthly = 0.0
    if month in heating_months:
        heat_monthly = (0.15 * area_m2) / len(heating_months)
    return {
        "Электроэнергия": elec, "Вода": water, "Канализация": water,
        "Вода и канализация": water, "Отопление": heat_monthly
    }

def _calculate_volumes_limassol(area_m2, occupants, behavior_factor):
    elec = (3.0 * area_m2 + 150.0 * occupants) * behavior_factor
    water = (4.0 * occupants) * behavior_factor
    return {"Электроэнергия": elec, "Вода": water}


# --- Функции-исполнители для методов расчета ---
def _calculate_flat_rate(volume, params, **kwargs):
    rate = params.get("rate", 0)
    subsidy_multiplier = kwargs.get("subsidy_multiplier", 1.0)
    if subsidy_multiplier < 1.0:
        full_rate = params.get("subsidy_rate", rate)
        rate = rate * subsidy_multiplier + full_rate * (1 - subsidy_multiplier)
    return volume * rate

def _calculate_progressive_rate(volume, params, **kwargs):
    cost = params.get("base_fee", 0)
    brackets = sorted(params.get("brackets", []), key=lambda x: x['from'])
    remaining_volume = volume
    for bracket in brackets:
        if remaining_volume <= 0: break
        vol_in_bracket = min(remaining_volume, bracket['to'] - bracket['from'] + 1)
        cost += vol_in_bracket * bracket['rate']
        remaining_volume -= vol_in_bracket
    return cost

def _calculate_fixed_fee(volume, params, **kwargs):
    return params.get("amount", 0)

def _calculate_service_range(volume, params, **kwargs):
    return (params.get("min", 0) + params.get("max", 0)) / 2

def _calculate_minsk_fixed_fees(volume, params, **kwargs):
    area_m2, occupants = kwargs.get("area_m2", 0), kwargs.get("occupants", 0)
    return (area_m2 * params["maintenance_max"] + area_m2 * params["lighting_max"] +
            occupants * params["waste_norm"] + area_m2 * params["capital_repair_rate"] +
            (occupants * params["elevator_max"] if kwargs.get("floor", 1) >= 2 else 0.0))

# --- Главный калькулятор ---
def calculate_costs(city, volumes, calculation_params):
    costs = {}
    city_tariffs = TARIFFS_DB.get(city, {})
    calculation_methods = {
        "flat_rate": _calculate_flat_rate, "progressive_rate": _calculate_progressive_rate,
        "fixed_fee": _calculate_fixed_fee, "service_range": _calculate_service_range,
        "minsk_fixed_fees": _calculate_minsk_fixed_fees,
    }

    for service, rule in city_tariffs.items():
        method_func = calculation_methods.get(rule["method"])
        if not method_func: continue
            
        base_cost = method_func(volume=volumes.get(service, 0), params=rule["params"], **calculation_params)
        costs[service] = round(base_cost * (1 + rule["vat"]), 2)
    
    costs["Итого"] = round(sum(costs.values()), 2)
    return costs

def apply_neighbor_adjustment(costs, house_category):
    adjusted_costs = costs.copy()
    house_coef = HOUSE_COEFS.get(house_category, {})
    
    if "Электроэнергия" in adjusted_costs and "electricity" in house_coef:
        adjusted_costs["Электроэнергия"] *= house_coef["electricity"]
    if "Отопление" in adjusted_costs and "heating" in house_coef:
        adjusted_costs["Отопление"] *= house_coef["heating"]
        
    adjusted_costs = {k: v * REALISM_UPLIFT for k, v in adjusted_costs.items() if k != "Итого"}
    adjusted_costs["Итого"] = round(sum(adjusted_costs.values()), 2)
    return adjusted_costs
