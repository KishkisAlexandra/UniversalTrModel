# app.py
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

# --- Ввод реальных расходов ---
st.header(f"📊 Введите ваши реальные расходы за месяц ({currency_label})")
CATEGORIES = city_config["services"]
extra_categories = ["Аренда"] if city == "Лимасол" else []
with st.expander("Показать поля для ручного ввода"):
    user_real = {k: st.number_input(f"{k} {currency_label}", 0.0, value=0.0, step=0.1) for k in CATEGORIES + extra_categories}
    total_keys = [k for k, v in user_real.items() if k not in extra_categories]
    user_real["Итого"] = round(sum(user_real[k] for k in total_keys), 2)

# --- Отображение результатов (Метрики, Таблицы, Графики, Рекомендации) ---
st.header(f"🏠 Сравнение расходов ({currency_label})")
col1, col2 = st.columns([2,1])
with col1:
    st.metric(f"Идеальный расчёт, {currency_label}", f"{ideal_costs.get('Итого', 0):.2f}")
    st.metric(f"Ваши реальные расходы, {currency_label}", f"{user_real.get('Итого', 0):.2f}")
    st.metric(f"Средний сосед, {currency_label}", f"{neighbor_costs.get('Итого', 0):.2f}")

detail_df = pd.DataFrame({
    "Категория": CATEGORIES,
    f"Идеальный ({currency_label})": [ideal_costs.get(c, 0) for c in CATEGORIES],
    f"Ваш ({currency_label})": [user_real.get(c, 0) for c in CATEGORIES],
    f"Сосед ({currency_label})": [neighbor_costs.get(c, 0) for c in CATEGORIES],
}).set_index("Категория")
st.dataframe(detail_df)

plot_df = detail_df.reset_index().melt(id_vars="Категория", var_name="Тип", value_name="Сумма")
fig = px.bar(plot_df, x="Категория", y="Сумма", color="Тип", barmode="group", text="Сумма")
fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
st.plotly_chart(fig, use_container_width=True)

st.header("💡 Рекомендации")
recommendations = city_config["recommendations"]
cols = st.columns(len(recommendations))
for i, (cat, (emoji, tip)) in enumerate(recommendations.items()):
    diff = user_real.get(cat, 0) - ideal_costs.get(cat, 0)
    msg = "Расход в норме"
    if diff > 1 and ideal_costs.get(cat, 0) > 0:
        msg = f"Перерасход {diff/ideal_costs[cat]:.0%} — {tip}"
    color = "#FFCDD2" if diff > 1 else "#C8E6C9"
    with cols[i]:
        st.markdown(f"<div style='padding:12px; border-radius:10px; background-color:{color}; text-align:center; min-height:130px; display: flex; flex-direction: column; justify-content: center;'><div style='font-size:1.5em'>{emoji}</div><strong>{cat}</strong><div style='margin-top:6px'>{msg}</div></div>", unsafe_allow_html=True)
