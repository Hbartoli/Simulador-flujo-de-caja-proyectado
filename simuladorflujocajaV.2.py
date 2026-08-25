import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import io

# Configuración de la página
st.set_page_config(page_title="Simulador de Flujo de Caja", layout="wide", page_icon="📊")

st.title("📊 Simulador Financiero Inteligente")
st.markdown("Predecí el efectivo, analizá costos con gráficos de distribución y activá alertas tempranas de riesgo.")

# --- BARRA LATERAL: ENTRADA DE DATOS ---
st.sidebar.header("⚙️ Parámetros Iniciales")

efectivo_inicial = st.sidebar.number_input(
    "Efectivo Inicial Disponible ($)", 
    min_value=0.0, 
    value=50000.0, 
    step=5000.0
)

dias_proyeccion = st.sidebar.slider(
    "Días a Proyectar", 
    min_value=60, 
    max_value=365, 
    value=180, 
    step=30
)

st.sidebar.header("📈 Ingresos Diarios Promedio")
ingresos_fijos = st.sidebar.number_input("Ventas / Ingresos Recurrentes ($)", min_value=0.0, value=2500.0)

# --- DESGLOSE DE GASTOS ---
st.sidebar.header("📉 Egresos Diarios por Categoría")
g_salarios = st.sidebar.number_input("🧑‍💻 Salarios y Nómina ($)", min_value=0.0, value=800.0)
g_marketing = st.sidebar.number_input("📣 Marketing y Pauta ($)", min_value=0.0, value=400.0)
g_software = st.sidebar.number_input("💻 Software y SaaS ($)", min_value=0.0, value=150.0)
g_proveedores = st.sidebar.number_input("📦 Proveedores y Stock ($)", min_value=0.0, value=500.0)
g_alquiler = st.sidebar.number_input("🏢 Alquiler y Servicios ($)", min_value=0.0, value=250.0)

st.sidebar.header("🔮 Escenario de Estrés")
factor_ingresos = st.sidebar.slider("Optimismo de Ventas (%)", min_value=0, max_value=200, value=100) / 100.0
factor_gastos = st.sidebar.slider("Incremento de Gastos (%)", min_value=100, max_value=200, value=100) / 100.0

# --- CÁLCULOS DEL FLUJO DE CAJA ---
fecha_inicio = datetime.today()
fechas = [fecha_inicio + timedelta(days=i) for i in range(dias_proyeccion)]

# Aplicar escenarios
ingresos_reales = ingresos_fijos * factor_ingresos

gastos_dict = {
    "Salarios": g_salarios * factor_gastos,
    "Marketing": g_marketing * factor_gastos,
    "Software/SaaS": g_software * factor_gastos,
    "Proveedores": g_proveedores * factor_gastos,
    "Alquiler/Servicios": g_alquiler * factor_gastos
}
egresos_totales_reales = sum(gastos_dict.values())
flujo_neto_diario = ingresos_reales - egresos_totales_reales

# Generar series temporales
saldos = []
saldo_actual = efectivo_inicial
fecha_quiebra = None

for i in range(dias_proyeccion):
    saldo_actual += flujo_neto_diario
    if saldo_actual <= 0 and fecha_quiebra is None:
        fecha_quiebra = fechas[i]
        saldo_actual = 0  
    elif saldo_actual < 0:
        saldo_actual = 0
        
    saldos.append(saldo_actual)

df_diario = pd.DataFrame({
    "Fecha": fechas,
    "Ingresos": [ingresos_reales] * dias_proyeccion,
    "Egresos Totales": [egresos_totales_reales] * dias_proyeccion,
    "Saldo Efectivo": saldos
})

for cat, valor in gastos_dict.items():
    df_diario[f"Gasto: {cat}"] = valor

# --- SECCIÓN 1: MÉTRICAS CLAVE ---
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

# --- SECCIÓN 2: ALERTAS TEMPRANAS DE SALUD FINANCIERA ---
st.subheader("⚠️ Panel de Alertas Tempranas")
col_al1, col_al2, col_al3 = st.columns(3)

# Alerta 1: Ratio de Costos Operativos sobre Ingresos
with col_al1:
    if ingresos_reales > 0:
        ratio_costos = (egresos_totales_reales / ingresos_reales) * 100
        if ratio_costos > 100:
            st.error(f"❌ **Déficit Estructural**: Los gastos superan a los ingresos en un {ratio_costos-100:.1f}%. El modelo no es sostenible sin financiamiento externo.")
        elif ratio_costos > 80:
            st.warning(f"⚠️ **Margen Ajustado**: Los costos absorben el {ratio_costos:.1f}% de tus ingresos. Estás vulnerable ante imprevistos.")
        else:
            st.success(f"💚 **Eficiencia Operativa**: Tus gastos representan solo el {ratio_costos:.1f}% de lo que ingresa.")
    else:
        st.error("❌ **Sin Ingresos**: Dependencia total de la caja inicial.")

# Alerta 2: Concentración en Marketing/Adquisición
with col_al2:
    if egresos_totales_reales > 0:
        pct_mkt = (gastos_dict["Marketing"] / egresos_totales_reales) * 100
        if pct_mkt > 35:
            st.warning(f"⚠️ **Alto Gasto en Marketing**: El {pct_mkt:.1f}% de tus egresos va a pauta comercial. Cuidado con la dependencia publicitaria.")
        else:
            st.success(f"💚 **Inversión de Marketing Equilibrada**: Representa el {pct_mkt:.1f}% del presupuesto total.")

# Alerta 3: Tiempo de Cobertura de Caja
with col_al3:
    if egresos_totales_reales > 0:
        meses_cobertura = (efectivo_inicial) / (egresos_totales_reales * 30)
        if meses_cobertura < 2:
            st.error(f"❌ **Liquidez Crítica**: Tu caja inicial cubre menos de {meses_cobertura:.1f} meses de operación fija sin contar ventas.")
        elif meses_cobertura < 6:
            st.warning(f"⚠️ **Liquidez Moderada**: Disponés de {meses_cobertura:.1f} meses de oxígeno operativo base.")
        else:
            st.success(f"💚 **Excelente Respaldo**: Tenés {meses_cobertura:.1f} meses de colchón financiero libre de riesgo inmediato.")

st.markdown("---")

# --- SECCIÓN 3: GRÁFICOS EVOLUTIVOS ---
st.subheader("📈 Proyecciones del Efectivo e Ingresos vs Gastos")
col_graf1, col_graf2 = st.columns(2)

with col_graf1:
    fig_linea = go.Figure()
    fig_linea.add_trace(go.Scatter(
        x=df_diario["Fecha"], y=df_diario["Saldo Efectivo"], mode='lines', name='Saldo en Caja',
        line=dict(color='#2ca02c' if flujo_neto_diario >= 0 else '#d62728', width=3), fill='tozeroy'
    ))
    fig_linea.add_trace(go.Scatter(x=df_diario["Fecha"], y=[0]*len(df_diario), mode='lines', name='Límite Crítico ($0)', line=dict(color='black', width=1, dash='dash')))
    fig_linea.update_layout(title="Evolución Diaria del Efectivo ($)", xaxis_title="Fecha", yaxis_title="Efectivo", template="plotly_white", margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_linea, use_container_width=True)

with col_graf2:
    df_mensual = df_diario.copy()
    df_mensual["Mes"] = df_mensual["Fecha"].dt.strftime('%b %Y')
    df_mes_agrupado = df_mensual.groupby("Mes", sort=False).agg({"Ingresos": "sum", "Egresos Totales": "sum"}).reset_index()
    
    fig_barra = go.Figure()
    fig_barra.add_trace(go.Bar(x=df_mes_agrupado["Mes"], y=df_mes_agrupado["Ingresos"], name="Ingresos Totales", marker_color='#1f77b4'))
    fig_barra.add_trace(go.Bar(x=df_mes_agrupado["Mes"], y=df_mes_agrupado["Egresos Totales"], name="Gastos Totales", marker_color='#ff7f0e'))
    fig_barra.update_layout(title="Comparativa Mensual Consolidada", barmode='group', xaxis_title="Mes", yaxis_title="Monto ($)", template="plotly_white", margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_barra, use_container_width=True)

st.markdown("---")

# --- SECCIÓN 4: DISTRIBUCIÓN DE COSTOS (NUEVO GRÁFICO DE TORTA) ---
st.subheader("🍰 Estructura Interna de Gastos")
col_torta, col_info_torta = st.columns([2, 1])

with col_torta:
    # Preparar el dataframe para el gráfico de torta
    df_torta = pd.DataFrame({
        "Categoría": list(gastos_dict.keys()),
        "Costo Diario": list(gastos_dict.values())
    })
    
    fig_torta = px.pie(
        df_torta, 
        values='Costo Diario', 
        names='Categoría', 
        hole=0.4, # Estilo Donut elegante
        color_discrete_sequence=px.colors.qualitative.Safe
    )
    fig_torta.update_traces(textposition='inside', textinfo='percent+label')
    fig_torta.update_layout(margin=dict(l=10, r=10, t=10, b=10), showlegend=True)
    st.plotly_chart(fig_torta, use_container_width=True)

with col_info_torta:
    st.markdown("#### 💡 Insights de Distribución")
    categoria_max = max(gastos_dict, key=gastos_dict.get)
    monto_max = gastos_dict[categoria_max]
    st.info(f"Tu principal centro de costo operativo es **{categoria_max}** con un consumo diario simulado de **${monto_max:,.2f}**.")

st.markdown("---")

# --- DETALLE DE DATOS Y EXPORTACIÓN ---
with st.expander("👀 Ver matriz detallada de datos y descargar"):
    df_exportar = df_diario.copy()
    df_exportar["Fecha"] = df_exportar["Fecha"].dt.strftime('%Y-%m-%d')
    st.dataframe(df_exportar.style.format({col: "${:,.2f}" for col in df_exportar.columns if col != "Fecha"}))
    
    def convertir_a_excel(dataframe):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            dataframe.to_excel(writer, index=False, sheet_name='Flujo Diario Avanzado')
            df_mes_agrupado.to_excel(writer, index=False, sheet_name='Resumen Mensual')
        return output.getvalue()

    excel_data = convertir_a_excel(df_exportar)
    st.download_button(
        label="📥 Descargar Reporte Financiero Completo en Excel (.xlsx)",
        data=excel_data,
        file_name=f"reporte_cashflow_inteligente_{datetime.today().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
