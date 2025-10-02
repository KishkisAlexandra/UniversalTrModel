# config.py

# ======================================================================================
# 1. Глобальные константы
# ======================================================================================
SCENARIOS = {"Экономный": 0.85, "Средний": 1.0, "Расточительный": 1.25}
HOUSE_COEFS = {"Новый": {"heating": 1.0, "electricity": 1.0}, "Средний": {"heating": 1.05, "electricity": 1.05}, "Старый": {"heating": 1.1, "electricity": 1.05}}
REALISM_UPLIFT = 1.07

# ======================================================================================
# 2. Информация о городах
# ======================================================================================
CITIES_DB = {
    "Минск": {
        "currency": "BYN", "services": ["Электроэнергия", "Вода", "Канализация", "Отопление", "Фикс. платежи"],
        "heating_months": [1, 2, 3, 4, 10, 11, 12], "volume_model": "standard_minsk",
        "recommendations": { "Электроэнергия": ("💡", "..."), "Вода": ("🚰", "...") }
    },
    "Лимасол": {
        "currency": "€", "services": ["Электроэнергия", "Вода", "Интернет", "Телефон", "IPTV", "Обслуживание"],
        "heating_months": [], "volume_model": "standard_limassol",
        "recommendations": { "Электроэнергия": ("💡", "..."), "Вода": ("🚰", "...") }
    }
}

# ======================================================================================
# 3. Тарифы и КОНВЕЙЕРЫ ВЫЧИСЛЕНИЙ
# ======================================================================================
TARIFFS_DB = {
    "Минск": {
        "Электроэнергия": {
            "params": {"subsidy_rate": 0.2412, "full_rate": 0.2969},
            "pipeline": [
                {"operator": "get_volume", "source": "Электроэнергия"},
                {"operator": "apply_subsidy_rate", "params_keys": ["subsidy_rate", "full_rate"]},
            ]
        },
        "Вода": {
            "params": {"rate": 1.7858},
            "pipeline": [
                {"operator": "get_volume", "source": "Вода"},
                {"operator": "multiply_by_param", "param_key": "rate"}
            ]
        },
        "Канализация": {
            "params": {"rate": 0.9586},
            "pipeline": [
                {"operator": "get_volume", "source": "Канализация"},
                {"operator": "multiply_by_param", "param_key": "rate"}
            ]
        },
        "Фикс. платежи": {
            # Для очень сложных, уникальных формул оставляем один специальный оператор.
            # Это разумный компромисс, чтобы не описывать 5 сложений в конвейере.
            "pipeline": [{"operator": "calculate_minsk_fixed_fees"}]
        }
    },
    "Лимасол": {
        "Электроэнергия": {
            "vat": 0.19, "params": {"rate": 0.2661},
            "pipeline": [
                {"operator": "get_volume", "source": "Электроэнергия"},
                {"operator": "multiply_by_param", "param_key": "rate"},
                {"operator": "apply_vat"}
            ]
        },
        "Вода": {
            "vat": 0.05,
            "params": {
                "base_fee": 22.0,
                "brackets": [
                    {"from": 1, "to": 40, "rate": 0.9}, {"from": 41, "to": 80, "rate": 1.43},
                    {"from": 81, "to": 120, "rate": 2.45}, {"from": 121, "to": float('inf'), "rate": 5.0}
                ]
            },
            "pipeline": [
                {"operator": "get_volume", "source": "Вода"},
                {"operator": "apply_progressive_rate", "param_key": "brackets"},
                {"operator": "add_param", "param_key": "base_fee"},
                {"operator": "apply_vat"}
            ]
        },
        "Интернет": {
            "vat": 0.19, "params": {"amount": 20},
            "pipeline": [
                {"operator": "get_fixed_amount", "param_key": "amount"},
                {"operator": "apply_vat"}
            ]
        }
    }
}
# Копируем правила для услуг, которые считаются одинаково
TARIFFS_DB["Минск"]["Отопление"] = TARIFFS_DB["Минск"]["Электроэнергия"]
TARIFFS_DB["Лимасол"]["Телефон"] = TARIFFS_DB["Лимасол"]["Интернет"]
TARIFFS_DB["Лимасол"]["IPTV"] = TARIFFS_DB["Лимасол"]["Интернет"]
