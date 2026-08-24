import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Configuración de la página
st.set_page_config(page_title="Simulador de Flujo de Caja", layout="wide", page_icon="📊")

st.title("📊 Simulador de Flujo de Caja Proyectado")
st.markdown("Predecí el comportamiento de tu efectivo y descubrí la fecha límite de tu negocio (Runway).")

# --- BARRA LATERAL: ENTRADA DE DATOS ---
st.sidebar.header("⚙️ Parámetros Iniciales")

efectivo_inicial = st.sidebar.number_input(
    "Efectivo Inicial Disponible ($)", 
    min_value=0.0, 
    value=50000.0, 
    step=1000.0
)

dias_proyeccion = st.sidebar.slider(
    "Días a Proyectar", 
    min_value=30, 
    max_value=365, 
    value=180, 
    step=30
)

st.sidebar.header("📈 Ingresos Diarios Promedio")
ingresos_fijos = st.sidebar.number_input("Ventas / Ingresos Recurrentes ($)", min_value=0.0, value=1500.0)

st.sidebar.header("📉 Egresos Diarios Promedio")
costos_fijos = st.sidebar.number_input("Costos Fijos (Renta, Salarios, etc.) ($)", min_value=0.0, value=800.0)
costos_variables = st.sidebar.number_input("Costos Variables (Proveedores, Marketing) ($)", min_value=0.0, value=400.0)

st.sidebar.header("🔮 Escenario de Estrés")
factor_ingresos = st.sidebar.slider("Optimismo de Ventas (%)", min_value=0, max_value=200, value=100) / 100.0
factor_gastos = st.sidebar.slider("Incremento de Gastos (%)", min_value=100, max_value=200, value=100) / 100.0

# --- CÁLCULOS DEL FLUJO DE CAJA ---
fecha_inicio = datetime.today()
fechas = [fecha_inicio + timedelta(days=i) for i in range(dias_proyeccion)]

# Aplicar factores de escenario
ingresos_reales = ingresos_fijos * factor_ingresos
egresos_reales = (costos_fijos + costos_variables) * factor_gastos
flujo_neto_diario = ingresos_reales - egresos_reales

# Generar series de datos
saldos = []
saldo_actual = efectivo_inicial
fecha_quiebra = None

for i in range(dias_proyeccion):
    saldo_actual += flujo_neto_diario
    # Evitar saldos negativos en el histórico simulado para detectar el quiebre
    if saldo_actual <= 0 and fecha_quiebra is None:
        fecha_quiebra = fechas[i]
        saldo_actual = 0  # Se quedó sin caja
    elif saldo_actual < 0:
        saldo_actual = 0
        
    saldos.append(saldo_actual)

# Crear DataFrame
df = pd.DataFrame({
    "Fecha": fechas,
    "Saldo Efectivo": saldos
})

# --- SECCIÓN DE MÉTRICAS CLAVE ---
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="Flujo Neto Diario", 
        value=f"${flujo_neto_diario:,.2f}",
        delta=f"${flujo_neto_diario:,.2f}",
        delta_color="normal" if flujo_neto_diario >= 0 else "inverse"
    )

with col2:
    tasa_quema = abs(flujo_neto_diario) if flujo_neto_diario < 0 else 0
    st.metric(label="Tasa de Quema Diaria (Burn Rate)", value=f"${tasa_quema:,.2f}")

with col3:
    if fecha_quiebra:
        dias_restantes = (fecha_quiebra - fecha_inicio).days
        st.error(f"🚨 ¡Alerta de Runway!\n\nEfectivo agotado el: {fecha_quiebra.strftime('%d/%m/%Y')} ({dias_restantes} días de margen).")
    else:
        st.success("✅ Caja Saludable. No se detecta fecha de quiebre en el periodo proyectado.")

st.markdown("---")

# --- GRÁFICO INTERACTIVO ---
st.subheader("📈 Proyección Evolutiva del Efectivo")

fig = go.Figure()

# Línea de flujo de caja
fig.add_trace(go.Scatter(
    x=df["Fecha"], 
    y=df["Saldo Efectivo"], 
    mode='lines',
    name='Saldo de Caja',
    line=dict(color='#2ca02c' if flujo_neto_diario >= 0 else '#d62728', width=3),
    fill='tozeroy'
))

# Línea de peligro (Cero pesos)
fig.add_trace(go.Scatter(
    x=df["Fecha"],
    y=[0] * len(df),
    mode='lines',
    name='Límite Crítico ($0)',
    line=dict(color='black', width=1, dash='dash')
))

# Configuración de diseño del gráfico
fig.update_layout(
    xaxis_title="Fecha",
    yaxis_title="Efectivo Disponible ($)",
    hovermode="x unified",
    template="plotly_white",
    height=500,
    margin=dict(l=20, r=20, t=20, b=20)
)

st.plotly_chart(fig, use_container_width=True)

# --- DETALLE DE DATOS ---
with st.expander("👀 Ver tabla de datos proyectados día por día"):
    st.dataframe(df.style.format({"Saldo Efectivo": "${:,.2f}"}))
