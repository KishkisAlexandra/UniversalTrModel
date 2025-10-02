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
        "currency": "BYN",
        "services": ["Электроэнергия", "Вода", "Канализация", "Отопление", "Фикс. платежи"],
        "heating_months": [1, 2, 3, 4, 10, 11, 12],
        "volume_model": "standard_minsk",
        # ИСПРАВЛЕНО: Добавлены все рекомендации
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
        "services": ["Электроэнергия", "Вода", "Интернет", "Телефон", "Обслуживание"],
        "heating_months": [],
        "volume_model": "standard_limassol",
        # ИСПРАВЛЕНО: Добавлены все рекомендации
        "recommendations": {
            "Электроэнергия": ("💡", "используйте таймеры и энергосберегающие приборы."),
            "Вода": ("🚰", "установите аэраторы и контролируйте расход воды."),
            "Интернет": ("🌐", "сравните тарифы и отключите неиспользуемые услуги."),
            "Телефон": ("📞", "оптимизируйте пакеты звонков и мобильный трафик."),
            "Обслуживание": ("🏢", "проверяйте счета за общие услуги и коммунальные платежи.")
        }
    }
}

# ======================================================================================
# 3. Тарифы и "Программы" расчетов (Конвейеры)
# ======================================================================================
TARIFFS_DB = {
    "Минск": {
        "Электроэнергия": {
            "params": {"subsidy_rate": 0.2412, "full_rate": 0.2969},
            "pipeline": [{"operator": "get_volume", "source": "Электроэнергия"}, {"operator": "apply_subsidy", "params_keys": ["subsidy_rate", "full_rate"]}]
        },
        "Вода": {
            "params": {"rate": 1.7858},
            "pipeline": [{"operator": "get_volume", "source": "Вода"}, {"operator": "multiply_by_param", "param_key": "rate"}]
        },
        "Канализация": {
            "params": {"rate": 0.9586},
            "pipeline": [{"operator": "get_volume", "source": "Канализация"}, {"operator": "multiply_by_param", "param_key": "rate"}]
        },
        "Отопление": {
            "params": {"subsidy_rate": 24.7187, "full_rate": 134.94},
            "pipeline": [{"operator": "get_volume", "source": "Отопление"}, {"operator": "apply_subsidy", "params_keys": ["subsidy_rate", "full_rate"]}]
        },
        # ИСПРАВЛЕНО: Полностью переписан конвейер для корректного расчета
        "Фикс. платежи": {
            "params": {"maintenance": 0.0388, "lighting": 0.0249, "waste": 0.2092, "repair": 0.05, "elevator_rate": 0.88, "zero": 0},
            "pipeline": [
                {"operator": "sum_of_steps", "pipelines": [
                    [{"operator": "get_param", "param_key": "area_m2"}, {"operator": "multiply_by_param", "param_key": "maintenance"}],
                    [{"operator": "get_param", "param_key": "area_m2"}, {"operator": "multiply_by_param", "param_key": "lighting"}],
                    [{"operator": "get_param", "param_key": "occupants"}, {"operator": "multiply_by_param", "param_key": "waste"}],
                    [{"operator": "get_param", "param_key": "area_m2"}, {"operator": "multiply_by_param", "param_key": "repair"}],
                    [
                        {"operator": "apply_conditional_value", "check_param": "floor", "condition": "gt", "threshold": 1, "value_if_true": "elevator_rate", "value_if_false": "zero"},
                        {"operator": "multiply_by_context", "param_key": "occupants"}
                    ]
                ]}
            ]
        }
    },
    "Лимасол": {
        "Электроэнергия": {
            "vat": 0.19, "params": {"rate": 0.2661},
            "pipeline": [{"operator": "get_volume", "source": "Электроэнергия"}, {"operator": "multiply_by_param", "param_key": "rate"}, {"operator": "apply_vat"}]
        },
        "Вода": {
            "vat": 0.05,
            "params": {"base_fee": 22.0, "brackets": [{"from": 1, "to": 40, "rate": 0.9}, {"from": 41, "to": 80, "rate": 1.43}]},
            "pipeline": [{"operator": "get_volume", "source": "Вода"}, {"operator": "apply_progressive_rate", "param_key": "brackets"}, {"operator": "add_param", "param_key": "base_fee"}, {"operator": "apply_vat"}]
        },
        "Интернет": {
            "vat": 0.19, "params": {"amount": 20},
            "pipeline": [{"operator": "get_fixed_amount", "param_key": "amount"}, {"operator": "apply_vat"}]
        },
        "Телефон": {
            "vat": 0.19, "params": {"amount": 20},
            "pipeline": [{"operator": "get_fixed_amount", "param_key": "amount"}, {"operator": "apply_vat"}]
        },
        "Обслуживание": {
            "vat": 0.19, "params": {"min": 45, "max": 125, "avg_coeff": 0.5},
            "pipeline": [
                {"operator": "sum_of_steps", "pipelines": [[{"operator": "get_fixed_amount", "param_key": "min"}], [{"operator": "get_fixed_amount", "param_key": "max"}]]},
                {"operator": "multiply_by_param", "param_key": "avg_coeff"},
                {"operator": "apply_vat"}
            ]
        }
    }
}
