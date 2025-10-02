# streamlit_app.py
import streamlit as st
import pandas as pd
import plotly.express as px

# Импортируем данные и логику из наших модулей
# Убедитесь, что файлы config.py и engine.py находятся в той же папке!
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
    # Этот виджет специфичен для Минска, поэтому его логика остается в UI
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
st.dataframe(detail_df, use_container_width=True)

# --- График ---
# Преобразуем данные для удобного построения графика в Plotly
plot_df = detail_df.melt(id_vars="Категория", var_name="Тип", value_name="Сумма")

fig = px.bar(plot_df, x="Категория", y="Сумма", color="Тип", barmode="group",
             color_discrete_map={
                 f"Идеальный расчёт ({currency_label})": "#636EFA",
                 f"Ваши реальные данные ({currency_label})": "#00CC96",
                 f"Средний сосед ({currency_label})": "#EF553B"
             },
             text="Сумма")
fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
fig.update_layout(yaxis_title=f"{currency_label} / месяц", legend_title_text="Показатель", uniformtext_minsize=8)
st.plotly_chart(fig, use_container_width=True)

# --- Умные рекомендации ---
st.header("💡 Рекомендации")
recommendations = city_config.get("recommendations", {})

def get_color(diff):
    if diff > 1: return "#FFCDD2"  # Перерасход (разница больше 1 денежной единицы) — красный
    else: return "#C8E6C9"         # В норме — зелёный

# Создаем столько колонок, сколько есть рекомендаций
cols = st.columns(len(recommendations))
for i, (cat, (emoji, tip)) in enumerate(recommendations.items()):
    ideal_val = ideal_costs.get(cat, 0)
    user_val = user_real.get(cat, 0)
    diff = user_val - ideal_val
    
    if ideal_val > 0:
        percent_over = round(diff / ideal_val * 100, 1)
        msg = f"Перерасход {percent_over}% — {tip}" if diff > 1 else "Расход в норме"
    else:
        msg = f"Расход: {user_val:.2f}" if user_val > 0 else "Расход в норме"
    
    with cols[i]:
        st.markdown(f"""
            <div style='padding:12px; border-radius:10px; background-color:{get_color(diff)};
                        font-size:0.9em; text-align:center; min-height:150px; 
                        display: flex; flex-direction: column; justify-content: center;'>
                <div style='font-size:1.5em'>{emoji}</div>
                <strong>{cat}</strong>
                <div style='margin-top:6px'>{msg}</div>
            </div>
        """, unsafe_allow_html=True)
