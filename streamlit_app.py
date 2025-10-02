# app.py
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Utility Benchmark — дашборд", page_icon="🏠", layout="wide")

# ======================================================================================
# 1. БАЗА ДАННЫХ (DB Simulation)
# Все тарифы, правила и специфичные для городов данные хранятся здесь.
# Чтобы добавить новый город или изменить тариф, нужно редактировать только этот блок.
# ======================================================================================

CITIES_DB = {
    "Минск": {
        "currency": "BYN",
        "services": ["Электроэнергия", "Вода", "Канализация", "Отопление", "Фикс. платежи"],
        "heating_months": [1, 2, 3, 4, 10, 11, 12],
        "volume_model": "standard_minsk",
        "recommendations": {
            "Электроэнергия": ("💡", "используйте энергосберегающие лампы и бытовую технику класса A++."),
            "Вода": ("🚰", "установите аэраторы и проверьте трубы на протечки."),
            "Отопление": ("🔥", "закрывайте окна и проверьте терморегуляторы."),
            "Канализация": ("💧", "контролируйте расход воды и исправность сантехники.")
        }
    },
    "Лимасол": {
        "currency": "€",
        "services": ["Электроэнергия", "Вода", "Интернет", "Телефон", "IPTV", "Обслуживание"],
        "heating_months": [],
        "volume_model": "standard_limassol",
        "recommendations": {
            "Электроэнергия": ("💡", "используйте таймеры и энергосберегающие приборы."),
            "Вода": ("🚰", "установите аэраторы и контролируйте расход воды."),
            "Интернет": ("🌐", "сравните тарифы и отключите неиспользуемые услуги."),
            "Телефон": ("📞", "оптимизируйте пакеты звонков и мобильный трафик."),
            "IPTV": ("📺", "отключите лишние каналы или подписки."),
            "Обслуживание": ("🏢", "проверяйте счета за общие услуги и коммунальные платежи.")
        }
    }
}

TARIFFS_DB = {
    "Минск": {
        "Электроэнергия": {"method": "flat_rate", "vat": 0.0, "params": {"rate": 0.2412, "subsidy_rate": 0.2969}},
        "Вода": {"method": "flat_rate", "vat": 0.0, "params": {"rate": 1.7858}},
        "Канализация": {"method": "flat_rate", "vat": 0.0, "params": {"rate": 0.9586}},
        "Отопление": {"method": "flat_rate", "vat": 0.0, "params": {"rate": 24.7187, "subsidy_rate": 134.94}},
        "Фикс. платежи": {"method": "minsk_fixed_fees", "vat": 0.0, "params": {
            "maintenance_max": 0.0388, "lighting_max": 0.0249, "waste_norm": 0.2092,
            "elevator_max": 0.88, "capital_repair_rate": 0.05
        }},
    },
    "Лимасол": {
        "Электроэнергия": {"method": "flat_rate", "vat": 0.19, "params": {"rate": 0.2661}},
        "Вода": {"method": "progressive_rate", "vat": 0.05, "params": {
            "base_fee": 22.0,
            "brackets": [
                {"from": 1, "to": 40, "rate": 0.9},
                {"from": 41, "to": 80, "rate": 1.43},
                {"from": 81, "to": 120, "rate": 2.45},
                {"from": 121, "to": float('inf'), "rate": 5.0}
            ]
        }},
        "Интернет": {"method": "fixed_fee", "vat": 0.19, "params": {"amount": 20}},
        "Телефон": {"method": "fixed_fee", "vat": 0.19, "params": {"amount": 20}},
        "IPTV": {"method": "fixed_fee", "vat": 0.19, "params": {"amount": 10}},
        "Обслуживание": {"method": "service_range", "vat": 0.19, "params": {"min": 45, "max": 125}},
    }
}

# ------------------------
# Глобальные константы (не зависят от города)
# ------------------------
SCENARIOS = {"Экономный": 0.85, "Средний": 1.0, "Расточительный": 1.25}
HOUSE_COEFS = {"Новый": {"heating": 1.0, "electricity": 1.0}, "Средний": {"heating": 1.05, "electricity": 1.05}, "Старый": {"heating": 1.1, "electricity": 1.05}}
REALISM_UPLIFT = 1.07


# ======================================================================================
# 2. РАСЧЕТНЫЙ ДВИЖОК (Calculation Engine)
# Универсальные функции, которые используют "Базу данных" для расчетов.
# ======================================================================================

# --- Функции расчета объемов ---
def calculate_volumes(city, area_m2, occupants, month, behavior_factor):
    """Единая точка входа для расчета объемов потребления."""
    volume_model = CITIES_DB[city]["volume_model"]

    if volume_model == "standard_minsk":
        return _calculate_volumes_minsk(area_m2, occupants, month, behavior_factor)
    elif volume_model == "standard_limassol":
        return _calculate_volumes_limassol(area_m2, occupants, behavior_factor)
    else:
        return {}

def _calculate_volumes_minsk(area_m2, occupants, month, behavior_factor):
    heating_months = CITIES_DB["Минск"]["heating_months"]
    elec = (60.0 + 75.0 * occupants + 0.5 * area_m2) * behavior_factor
    water = 4.5 * occupants * behavior_factor
    heat_monthly = 0.0
    if month in heating_months:
        heat_monthly = (0.15 * area_m2) / len(heating_months)
    return {
        "Электроэнергия": elec, "Вода": water, "Канализация": water, "Отопление": heat_monthly
    }

def _calculate_volumes_limassol(area_m2, occupants, behavior_factor):
    elec = (3.0 * area_m2 + 150.0 * occupants) * behavior_factor
    water = (4.0 * occupants) * behavior_factor
    return {"Электроэнергия": elec, "Вода": water}


# --- Функции-исполнители для методов расчета ---
def _calculate_flat_rate(volume, params, **kwargs):
    rate = params.get("rate", 0)
    # Обработка льготных тарифов, если применимо
    subsidy_multiplier = kwargs.get("subsidy_multiplier", 1.0)
    if subsidy_multiplier < 1.0:
        full_rate = params.get("subsidy_rate", rate)
        rate = rate * subsidy_multiplier + full_rate * (1 - subsidy_multiplier)
    return volume * rate

def _calculate_progressive_rate(volume, params, **kwargs):
    cost = params.get("base_fee", 0)
    brackets = params.get("brackets", [])
    remaining_volume = volume
    
    # Сортируем пороги на всякий случай
    sorted_brackets = sorted(brackets, key=lambda x: x['from'])
    
    last_upper_bound = 0
    for bracket in sorted_brackets:
        if remaining_volume <= 0:
            break
        
        bracket_width = bracket['to'] - bracket['from'] + 1
        volume_in_bracket = min(remaining_volume, bracket_width)
        cost += volume_in_bracket * bracket['rate']
        remaining_volume -= volume_in_bracket
        
    return cost

def _calculate_fixed_fee(volume, params, **kwargs):
    return params.get("amount", 0)

def _calculate_service_range(volume, params, **kwargs):
    return (params.get("min", 0) + params.get("max", 0)) / 2

def _calculate_minsk_fixed_fees(volume, params, **kwargs):
    area_m2 = kwargs.get("area_m2", 0)
    occupants = kwargs.get("occupants", 0)
    maintenance = area_m2 * params["maintenance_max"]
    lighting = area_m2 * params["lighting_max"]
    waste = occupants * params["waste_norm"]
    capital_repair = area_m2 * params["capital_repair_rate"]
    elevator = occupants * params["elevator_max"] if kwargs.get("floor", 1) >= 2 and kwargs.get("has_elevator", True) else 0.0
    return maintenance + lighting + waste + capital_repair + elevator

# --- Главный калькулятор ---
def calculate_costs(city, volumes, calculation_params):
    """
    Универсальный калькулятор стоимости. Итерирует по услугам города и применяет
    соответствующий метод расчета из TARIFFS_DB.
    """
    costs = {}
    city_tariffs = TARIFFS_DB.get(city, {})
    
    # Словарь методов, чтобы избежать `if/elif`
    calculation_methods = {
        "flat_rate": _calculate_flat_rate,
        "progressive_rate": _calculate_progressive_rate,
        "fixed_fee": _calculate_fixed_fee,
        "service_range": _calculate_service_range,
        "minsk_fixed_fees": _calculate_minsk_fixed_fees,
    }

    for service, rule in city_tariffs.items():
        method_func = calculation_methods.get(rule["method"])
        if not method_func:
            continue
            
        volume = volumes.get(service, 0)
        base_cost = method_func(volume=volume, params=rule["params"], **calculation_params)
        final_cost = base_cost * (1 + rule["vat"])
        costs[service] = round(final_cost, 2)
    
    costs["Итого"] = round(sum(costs.values()), 2)
    return costs

def apply_neighbor_adjustment(costs, volumes, city, house_category):
    """Применяет коэффициенты 'соседа'."""
    # Создаем копию, чтобы не изменять оригинальные словари
    adjusted_costs = costs.copy()
    
    # В этой модели мы корректируем уже рассчитанные стоимости, а не объемы, что проще.
    # Если нужно корректировать объемы, логику нужно будет перенести до вызова calculate_costs
    house_coef = HOUSE_COEFS.get(house_category, {})
    if "Электроэнергия" in adjusted_costs and "electricity" in house_coef:
         adjusted_costs["Электроэнергия"] *= house_coef["electricity"]
    if "Отопление" in adjusted_costs and "heating" in house_coef:
        adjusted_costs["Отопление"] *= house_coef["heating"]
        
    # Применяем общий "коэффициент реализма" и пересчитываем итог
    adjusted_costs = {k: v * REALISM_UPLIFT for k, v in adjusted_costs.items() if k != "Итого"}
    adjusted_costs["Итого"] = round(sum(adjusted_costs.values()), 2)
    return adjusted_costs


# ======================================================================================
# 3. ИНТЕРФЕЙС (Streamlit UI)
# Эта часть почти не изменилась, она просто вызывает новый универсальный движок.
# ======================================================================================

# --- Sidebar: параметры семьи ---
st.sidebar.header("Параметры")
city = st.sidebar.selectbox("Город", list(CITIES_DB.keys()))
city_config = CITIES_DB[city]
currency_label = city_config["currency"]

month = st.sidebar.selectbox("Месяц", list(range(1,13)),
                             format_func=lambda x: ["Янв","Фев","Мар","Апр","Май","Июн","Июл","Авг","Сен","Окт","Ноя","Дек"][x-1])
area_m2 = st.sidebar.number_input("Площадь, м²", 10.0, 500.0, 90.0)
adults = st.sidebar.number_input("Взрослые", 0, 10, 2)
children = st.sidebar.number_input("Дети", 0, 10, 2)
occupants = adults + children
scenario = st.sidebar.selectbox("Сценарий поведения", list(SCENARIOS.keys()), index=1)
behavior_factor = SCENARIOS[scenario]
house_category = st.sidebar.selectbox("Категория дома", list(HOUSE_COEFS.keys()), index=1)
subsidy_multiplier = 1.0
if city == "Минск": # Параметр специфичный для Минска
    use_subsidy = st.sidebar.checkbox("Использовать льготный тариф", value=True)
    if not use_subsidy:
        subsidy_multiplier = 0.0 # 0% льготы = 100% полного тарифа

# --- Универсальный блок расчетов ---
calculation_params = {
    "area_m2": area_m2,
    "occupants": occupants,
    "floor": 5, # Пример, можно добавить в UI
    "has_elevator": True, # Пример
    "subsidy_multiplier": subsidy_multiplier
}

# Идеальный расчет
ideal_volumes = calculate_volumes(city, area_m2, occupants, month, behavior_factor=1.0)
ideal_costs = calculate_costs(city, ideal_volumes, calculation_params)

# Расчет "соседа"
neighbor_volumes = calculate_volumes(city, area_m2, occupants, month, behavior_factor)
neighbor_base_costs = calculate_costs(city, neighbor_volumes, calculation_params)
neighbor_costs = apply_neighbor_adjustment(neighbor_base_costs, neighbor_volumes, city, house_category)


# --- Ввод реальных расходов ---
st.header(f"📊 Введите ваши реальные расходы за месяц ({currency_label})")
CATEGORIES = city_config["services"]
extra_categories = ["Аренда"] if city == "Лимасол" else []

with st.expander("Показать поля для ручного ввода"):
    user_real = {k: st.number_input(f"{k} {currency_label}", 0.0, value=0.0, step=0.1) for k in CATEGORIES + extra_categories}
    
    # Исключаем доп. категории из "Итого"
    total_keys = [k for k in user_real.keys() if k not in extra_categories]
    user_real["Итого"] = round(sum(user_real[k] for k in total_keys), 2)


# --- Метрики ---
st.header(f"🏠 Сравнение расходов ({currency_label})")
col1, col2 = st.columns([2,1])
with col1:
    st.metric(f"Идеальный расчёт по нормативам, {currency_label}", f"{ideal_costs.get('Итого', 0):.2f}")
    st.metric(f"Ваши реальные расходы, {currency_label}", f"{user_real.get('Итого', 0):.2f}")
    st.metric(f"Средний сосед, {currency_label}", f"{neighbor_costs.get('Итого', 0):.2f}")

# --- Таблица расходов ---
detail_df = pd.DataFrame({
    "Категория": CATEGORIES,
    f"Идеальный расчёт ({currency_label})": [ideal_costs.get(c, 0) for c in CATEGORIES],
    f"Ваши реальные данные ({currency_label})": [user_real.get(c, 0) for c in CATEGORIES],
    f"Средний сосед ({currency_label})": [neighbor_costs.get(c, 0) for c in CATEGORIES],
})
st.dataframe(detail_df, height=len(CATEGORIES)*35 + 38) # Автоматическая высота таблицы

# --- График ---
plot_df_data = []
for cat in CATEGORIES:
    plot_df_data.append({"Категория": cat, "Тип": "Идеальный расчёт", "Сумма": ideal_costs.get(cat, 0)})
    plot_df_data.append({"Категория": cat, "Тип": "Ваши реальные данные", "Сумма": user_real.get(cat, 0)})
    plot_df_data.append({"Категория": cat, "Тип": "Средний сосед", "Сумма": neighbor_costs.get(cat, 0)})

plot_df = pd.DataFrame(plot_df_data)

fig = px.bar(plot_df, x="Категория", y="Сумма", color="Тип", barmode="group",
             color_discrete_map={"Идеальный расчёт":"#636EFA","Ваши реальные данные":"#00CC96","Средний сосед":"#EF553B"},
             text="Сумма")
fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
fig.update_layout(yaxis_title=f"{currency_label} / месяц", legend_title_text="Показатель", uniformtext_minsize=8)
st.plotly_chart(fig, use_container_width=True)

# --- Умные рекомендации ---
st.header("💡 Рекомендации")
recommendations = city_config["recommendations"]

def get_color(diff):
    if diff > 1: return "#FFCDD2"  # перерасход — красный
    else: return "#C8E6C9"         # в норме — зелёный

cols = st.columns(len(recommendations))
for i, (cat, (emoji, tip)) in enumerate(recommendations.items()):
    ideal_val = ideal_costs.get(cat, 0)
    user_val = user_real.get(cat, 0)
    diff = user_val - ideal_val
    
    if ideal_val > 0:
        percent_over = round(diff / ideal_val * 100, 1)
        msg = f"Перерасход {percent_over}% — {tip}" if diff > 1 else "Расход в норме"
    else:
        msg = "Расход в норме" if user_val == 0 else f"Расход: {user_val:.2f}"
    
    with cols[i]:
        st.markdown(f"""
            <div style='padding:12px; border-radius:10px; background-color:{get_color(diff)};
                        font-size:0.9em; text-align:center; min-height:130px; display: flex; flex-direction: column; justify-content: center;'>
                <div style='font-size:1.5em'>{emoji}</div>
                <strong>{cat}</strong>
                <div style='margin-top:6px'>{msg}</div>
            </div>
        """, unsafe_allow_html=True)
