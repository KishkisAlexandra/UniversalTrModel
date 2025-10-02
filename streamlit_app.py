# streamlit_app.py
import streamlit as st
import pandas as pd
import plotly.express as px

# Импортируем данные и логику из наших модулей
from config import CITIES_DB, SCENARIOS, HOUSE_COEFS
from engine import calculate_volumes, calculate_costs, apply_neighbor_adjustment

st.set_page_config(page_title="Utility Benchmark — дашборд", page_icon="🏠", layout="wide")

# --- Sidebar: параметры семьи ---
st.sidebar.header("Параметры")
city = st.sidebar.selectbox("Город", list(CITIES_DB.keys()))
city_config = CITIES_DB[city]
currency_label = city_config["currency"]

month = st.sidebar.selectbox("Месяц", list(range(1, 13)),
                             format_func=lambda x: ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"][x-1])
area_m2 = st.sidebar.number_input("Площадь, м²", 10.0, 500.0, 90.0)
occupants = st.sidebar.number_input("Количество жильцов", 1, 20, 3)
scenario = st.sidebar.selectbox("Сценарий поведения", list(SCENARIOS.keys()), index=1)
behavior_factor = SCENARIOS[scenario]
house_category = st.sidebar.selectbox("Категория дома", list(HOUSE_COEFS.keys()), index=1)

subsidy_multiplier = 1.0
if city == "Минск":
    if not st.sidebar.checkbox("Использовать льготный тариф", value=True):
        subsidy_multiplier = 0.0

# --- Универсальный блок расчетов ---
calculation_params = {
    "area_m2": area_m2, "occupants": occupants, "floor": 5, "subsidy_multiplier": subsidy_multiplier
}
ideal_volumes = calculate_volumes(city, area_m2, occupants, month, behavior_factor=1.0)
ideal_costs = calculate_costs(city, ideal_volumes, calculation_params)

neighbor_volumes = calculate_volumes(city, area_m2, occupants, month, behavior_factor)
neighbor_base_costs = calculate_costs(city, neighbor_volumes, calculation_params)
neighbor_costs = apply_neighbor_adjustment(neighbor_base_costs, house_category)

# --- Остальная часть UI (без изменений) ---
# ... (скопируйте сюда всю оставшуюся часть вашего UI из предыдущей версии) ...
st.header(f"📊 Введите ваши реальные расходы за месяц ({currency_label})")
CATEGORIES = city_config["services"]
# ... и так далее
