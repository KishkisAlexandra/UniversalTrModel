# config.py (фрагмент новой структуры)

TARIFFS_DB = {
    "Минск": {
        "Электроэнергия": {
            "vat": 0.0,
            "params": {"rate": 0.2412},
            "pipeline": [
                # Универсальная формула: Стоимость = Объем * Тариф
                {"operator": "get_volume", "source": "Электроэнергия"},
                {"operator": "multiply_by_param", "param_key": "rate"}
            ]
        },
        "Фикс. платежи": {
            "vat": 0.0,
            "params": { ... },
            "pipeline": [
                # Универсальная формула: Стоимость = (Площадь*Т1) + (Жильцы*Т2) + ...
                {"operator": "calculate_minsk_fixed_fees"} # Для особо сложных случаев можно оставить кастомный оператор
            ]
        }
    },
    "Лимасол": {
        "Вода": {
            "vat": 0.05,
            "params": {"base_fee": 22.0, "brackets": [...]},
            "pipeline": [
                # Универсальная формула: Стоимость = (f(Объем) + База) * (1+НДС)
                {"operator": "get_volume", "source": "Вода"},
                {"operator": "apply_progressive_rate", "param_key": "brackets"},
                {"operator": "add_param", "param_key": "base_fee"},
                {"operator": "apply_vat"} # НДС применяется как отдельный шаг
            ]
        },
        "Интернет": {
            "vat": 0.19,
            "params": {"amount": 20},
            "pipeline": [
                # Универсальная формула: Стоимость = Константа * (1+НДС)
                {"operator": "get_fixed_amount", "param_key": "amount"},
                {"operator": "apply_vat"}
            ]
        }
    }
}
