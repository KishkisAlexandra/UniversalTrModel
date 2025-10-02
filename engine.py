# engine.py
from config import CITIES_DB, TARIFFS_DB, HOUSE_COEFS, REALISM_UPLIFT

# --- Расчет объемов (остается без изменений) ---
def calculate_volumes(city, area_m2, occupants, month, behavior_factor):
    volume_model = CITIES_DB.get(city, {}).get("volume_model", "")
    if volume_model == "standard_minsk": return _calculate_volumes_minsk(area_m2, occupants, month, behavior_factor)
    if volume_model == "standard_limassol": return _calculate_volumes_limassol(area_m2, occupants, behavior_factor)
    return {}

def _calculate_volumes_minsk(area_m2, occupants, month, behavior_factor):
    # ... (код без изменений)
    heating_months = CITIES_DB["Минск"]["heating_months"]
    elec = (60.0 + 75.0 * occupants + 0.5 * area_m2) * behavior_factor
    water = 4.5 * occupants * behavior_factor
    heat_monthly = (0.15 * area_m2) / len(heating_months) if month in heating_months else 0.0
    return {"Электроэнергия": elec, "Вода": water, "Канализация": water, "Отопление": heat_monthly}

def _calculate_volumes_limassol(area_m2, occupants, behavior_factor):
    # ... (код без изменений)
    elec = (3.0 * area_m2 + 150.0 * occupants) * behavior_factor
    water = (4.0 * occupants) * behavior_factor
    return {"Электроэнергия": elec, "Вода": water}

# --- Вспомогательные функции-операторы ---
def _apply_progressive_rate_op(volume, brackets):
    cost = 0; remaining_volume = volume
    for bracket in sorted(brackets, key=lambda x: x['from']):
        if remaining_volume <= 0: break
        vol_in_bracket = min(remaining_volume, bracket['to'] - bracket['from'] + 1)
        cost += vol_in_bracket * bracket['rate']
        remaining_volume -= vol_in_bracket
    return cost

def _minsk_fixed_fees_op(params, calc_params):
    area_m2, occupants = calc_params.get("area_m2", 0), calc_params.get("occupants", 0)
    # Здесь можно было бы получать ключи из params, но для простоты оставим так
    return (area_m2 * 0.0388 + area_m2 * 0.0249 + occupants * 0.2092 + area_m2 * 0.05 +
            (occupants * 0.88 if calc_params.get("floor", 1) >= 2 else 0.0))

# --- ГЛАВНЫЙ УНИВЕРСАЛЬНЫЙ КАЛЬКУЛЯТОР ---
def calculate_costs(city, volumes, calculation_params):
    costs = {}
    city_tariffs = TARIFFS_DB.get(city, {})

    for service, rule in city_tariffs.items():
        pipeline = rule.get("pipeline", [])
        params = rule.get("params", {})
        current_value = 0

        for step in pipeline:
            op = step["operator"]
            
            if op == "get_volume": current_value = volumes.get(step["source"], 0)
            elif op == "multiply_by_param": current_value *= params.get(step["param_key"], 1)
            elif op == "add_param": current_value += params.get(step["param_key"], 0)
            elif op == "get_fixed_amount": current_value = params.get(step["param_key"], 0)
            elif op == "apply_vat": current_value *= (1 + rule.get("vat", 0))
            elif op == "apply_progressive_rate": current_value = _apply_progressive_rate_op(current_value, params.get(step["param_key"]))
            elif op == "apply_subsidy_rate":
                s_rate, f_rate = params.get(step["params_keys"][0]), params.get(step["params_keys"][1])
                multiplier = calculation_params.get("subsidy_multiplier", 1.0)
                rate = s_rate * multiplier + f_rate * (1 - multiplier)
                current_value *= rate
            elif op == "calculate_minsk_fixed_fees": current_value = _minsk_fixed_fees_op(params, calculation_params)

        costs[service] = round(current_value, 2)

    costs["Итого"] = round(sum(v for k, v in costs.items() if k != "Итого"), 2)
    return costs

def apply_neighbor_adjustment(costs, house_category):
    # ... (код без изменений)
    adjusted_costs = costs.copy()
    house_coef = HOUSE_COEFS.get(house_category, {})
    if "Электроэнергия" in adjusted_costs: adjusted_costs["Электроэнергия"] *= house_coef.get("electricity", 1.0)
    if "Отопление" in adjusted_costs: adjusted_costs["Отопление"] *= house_coef.get("heating", 1.0)
    adjusted_costs = {k: v * REALISM_UPLIFT for k, v in adjusted_costs.items() if k != "Итого"}
    adjusted_costs["Итого"] = round(sum(adjusted_costs.values()), 2)
    return adjusted_costs
