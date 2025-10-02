# engine.py (новый, полностью универсальный)

from config import TARIFFS_DB

def calculate_costs(city, volumes, calculation_params):
    """
    Универсальный калькулятор, исполняющий конвейер операций из config.py.
    """
    costs = {}
    city_tariffs = TARIFFS_DB.get(city, {})

    for service, rule in city_tariffs.items():
        pipeline = rule.get("pipeline", [])
        params = rule.get("params", {})
        current_value = 0  # Начальное значение для каждой услуги

        # Цикл-исполнитель конвейера
        for step in pipeline:
            op = step["operator"]
            
            # --- Набор универсальных математических операций ---
            if op == "get_volume":
                current_value = volumes.get(step["source"], 0)
            
            elif op == "multiply_by_param":
                current_value *= params.get(step["param_key"], 1)
            
            elif op == "add_param":
                current_value += params.get(step["param_key"], 0)
                
            elif op == "get_fixed_amount":
                current_value = params.get(step["param_key"], 0)

            elif op == "apply_progressive_rate":
                # Здесь живет логика прогрессивной шкалы, одна на всех
                current_value = _calculate_progressive_logic(current_value, params.get(step["param_key"]))

            elif op == "apply_vat":
                current_value *= (1 + rule.get("vat", 0))

            # ... можно добавлять другие универсальные операторы ...

        costs[service] = round(current_value, 2)

    costs["Итого"] = round(sum(costs.values()), 2)
    return costs

# Вспомогательная функция, которая больше не привязана к городу
def _calculate_progressive_logic(volume, brackets):
    # ... здесь логика расчета по порогам ...
    cost = 0 
    # ... implementation ...
    return cost

# Расчет объемов остается пока без изменений, но его тоже можно сделать по такому же принципу
# ...
