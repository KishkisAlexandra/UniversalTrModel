# engine.py
from config import TARIFFS_DB, HOUSE_COEFS, REALISM_UPLIFT, CITIES_DB

# ======================================================================================
# 1. ЛОГИКА РАСЧЕТА ОБЪЕМОВ ПОТРЕБЛЕНИЯ (ПАТТЕРН "СТРАТЕГИЯ")
# ======================================================================================

# --- КОНКРЕТНЫЕ СТРАТЕГИИ (МАТЕМАТИЧЕСКИЕ МОДЕЛИ) ---
def _calculate_volumes_minsk_model(area_m2, occupants, month, behavior_factor, config):
    heating_months = config.get("heating_months", [])
    elec = (60.0 + 75.0 * occupants + 0.5 * area_m2) * behavior_factor
    water = 4.5 * occupants * behavior_factor
    heat_monthly = (0.15 * area_m2) / len(heating_months) if month in heating_months and heating_months else 0.0
    return {"Электроэнергия": elec, "Вода": water, "Канализация": water, "Отопление": heat_monthly}

def _calculate_volumes_limassol_model(area_m2, occupants, month, behavior_factor, config):
    elec = (3.0 * area_m2 + 150.0 * occupants) * behavior_factor
    water = (4.0 * occupants) * behavior_factor
    return {"Электроэнергия": elec, "Вода": water}

# --- РЕЕСТР ДОСТУПНЫХ СТРАТЕГИЙ ---
VOLUME_CALCULATION_STRATEGIES = {
    "standard_minsk": _calculate_volumes_minsk_model,
    "standard_limassol": _calculate_volumes_limassol_model,
}

# --- УНИВЕРСАЛЬНЫЙ ДВИЖОК РАСЧЕТА ОБЪЕМОВ ---
def calculate_volumes(city, area_m2, occupants, month, behavior_factor):
    city_config = CITIES_DB.get(city, {})
    model_name = city_config.get("volume_model", "")
    strategy_function = VOLUME_CALCULATION_STRATEGIES.get(model_name)
    if strategy_function:
        return strategy_function(area_m2, occupants, month, behavior_factor, city_config)
    return {}

# ======================================================================================
# 2. ЛОГИКА РАСЧЕТА СТОИМОСТИ (ПАТТЕРН "КОНВЕЙЕР")
# ======================================================================================

def _apply_progressive_rate_op(volume, brackets):
    cost = 0; remaining_volume = volume
    for bracket in sorted(brackets, key=lambda x: x.get('from', 0)):
        if remaining_volume <= 0: break
        vol_in_bracket = min(remaining_volume, bracket.get('to', float('inf')) - bracket.get('from', 0) + 1)
        cost += vol_in_bracket * bracket.get('rate', 0)
        remaining_volume -= vol_in_bracket
    return cost

def _execute_pipeline(pipeline, rule, volumes, calculation_params):
    current_value = 0
    params = rule.get("params", {})

    for step in pipeline:
        op = step.get("operator")
        
        if op == "get_volume": current_value = volumes.get(step["source"], 0)
        elif op == "get_param": current_value = calculation_params.get(step["param_key"], 0)
        elif op == "get_fixed_amount": current_value = params.get(step["param_key"], 0)
        
        elif op == "add_param": current_value += params.get(step["param_key"], 0)
        # ИЗМЕНЕНО: Оператор multiply разделен на два для ясности и исправления ошибки
        elif op == "multiply_by_param": current_value *= params.get(step["param_key"], 1)
        elif op == "multiply_by_context": current_value *= calculation_params.get(step["param_key"], 1)

        elif op == "apply_progressive_rate": current_value = _apply_progressive_rate_op(current_value, params.get(step["param_key"], []))
        
        elif op == "apply_conditional_value":
            param_to_check = calculation_params.get(step["check_param"], 0)
            threshold = step["threshold"]
            condition = step["condition"]
            is_true = (condition == "gt" and param_to_check > threshold) or \
                      (condition == "lt" and param_to_check < threshold) or \
                      (condition == "eq" and param_to_check == threshold)
            key_to_use = step["value_if_true"] if is_true else step["value_if_false"]
            current_value = params.get(key_to_use, 0)

        elif op == "sum_of_steps":
            current_value = sum(_execute_pipeline(sub_pipeline, rule, volumes, calculation_params) for sub_pipeline in step.get("pipelines", []))

        elif op == "apply_vat": current_value *= (1 + rule.get("vat", 0))
        elif op == "apply_subsidy":
            keys = step.get("params_keys", [])
            s_rate, f_rate = params.get(keys[0], 0), params.get(keys[1], 0)
            multiplier = calculation_params.get("subsidy_multiplier", 1.0)
            rate = s_rate * multiplier + f_rate * (1 - multiplier)
            current_value *= rate
            
    return current_value

def calculate_costs(city, volumes, calculation_params):
    costs = {service: round(_execute_pipeline(rule.get("pipeline", []), rule, volumes, calculation_params), 2)
             for service, rule in TARIFFS_DB.get(city, {}).items()}
    costs["Итого"] = round(sum(v for k, v in costs.items() if k != "Итого"), 2)
    return costs

# ======================================================================================
# 3. ЛОГИКА КОРРЕКТИРОВОК
# ======================================================================================
    
def apply_neighbor_adjustment(costs, house_category):
    adjusted_costs = costs.copy()
    house_coef = HOUSE_COEFS.get(house_category, {})
    if "Электроэнергия" in adjusted_costs: adjusted_costs["Электроэнергия"] *= house_coef.get("electricity", 1.0)
    if "Отопление" in adjusted_costs: adjusted_costs["Отопление"] *= house_coef.get("heating", 1.0)
    
    final_costs = {k: v * REALISM_UPLIFT for k, v in adjusted_costs.items() if k != "Итого"}
    final_costs["Итого"] = round(sum(final_costs.values()), 2)
    return final_costs
