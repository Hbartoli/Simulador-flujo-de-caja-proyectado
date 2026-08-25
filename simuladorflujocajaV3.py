import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import io

# Configuración de la página
st.set_page_config(page_title="Simulador de Flujo de Caja", layout="wide", page_icon="📊")

st.title("📊 Simulador Financiero de Alta Precisión")
st.markdown("Proyectá el efectivo con crecimiento compuesto mensual de ventas y programación de gastos extraordinarios únicos.")

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

st.sidebar.header("📈 Ingresos y Crecimiento")
ingresos_fijos = st.sidebar.number_input("Ventas Diarias Iniciales ($)", min_value=0.0, value=2500.0)
crecimiento_mensual = st.sidebar.slider("Crecimiento de Ventas Mensual Compuesto (%)", min_value=0.0, max_value=30.0, value=5.0, step=0.5) / 100.0

# --- GASTOS OPERATIVOS DIARIOS ---
st.sidebar.header("📉 Egresos Diarios Operativos")
g_salarios = st.sidebar.number_input("🧑‍💻 Salarios y Nómina ($)", min_value=0.0, value=800.0)
g_marketing = st.sidebar.number_input("📣 Marketing y Pauta ($)", min_value=0.0, value=400.0)
g_software = st.sidebar.number_input("💻 Software y SaaS ($)", min_value=0.0, value=150.0)
g_proveedores = st.sidebar.number_input("📦 Proveedores y Stock ($)", min_value=0.0, value=500.0)
g_alquiler = st.sidebar.number_input("🏢 Alquiler y Servicios ($)", min_value=0.0, value=250.0)

# --- NUEVA SECCIÓN: GASTOS EXTRAORDINARIOS ÚNICOS ---
st.sidebar.header("🗓️ Gastos Extraordinarios ÚNICOS")
activar_extraordinario = st.sidebar.checkbox("Programar gasto extraordinario", value=True)

if activar_extraordinario:
    nombre_gasto = st.sidebar.text_input("Concepto del Gasto", value="Impuesto Anual / Aguinaldos")
    monto_gasto = st.sidebar.number_input("Monto del Gasto ($)", min_value=0.0, value=15000.0, step=1000.0)
    dias_para_gasto = st.sidebar.slider("¿En cuántos días ocurrirá este pago?", min_value=1, max_value=dias_proyeccion, value=45)
    fecha_extraordinaria = datetime.today().date() + timedelta(days=dias_para_gasto)
    st.sidebar.info(f"📅 Programado para el: {fecha_extraordinaria.strftime('%d/%m/%Y')}")
else:
    monto_gasto = 0.0
    fecha_extraordinaria = None
    nombre_gasto = ""

st.sidebar.header("🔮 Escenario de Estrés Global")
factor_ingresos = st.sidebar.slider("Optimismo de Ventas (%)", min_value=0, max_value=200, value=100) / 100.0
factor_gastos = st.sidebar.slider("Incremento de Gastos Fijos (%)", min_value=100, max_value=200, value=100) / 100.0

# --- CÁLCULOS CRONOLÓGICOS DEL FLUJO DE CAJA ---
fecha_inicio = datetime.today().date()

# Calcular base de egresos diarios recurrentes con estrés
gastos_operativos_dict = {
    "Salarios": g_salarios * factor_gastos,
    "Marketing": g_marketing * factor_gastos,
    "Software/SaaS": g_software * factor_gastos,
    "Proveedores": g_proveedores * factor_gastos,
    "Alquiler/Servicios": g_alquiler * factor_gastos
}
egresos_operativos_diarios = sum(gastos_operativos_dict.values())

# Listas para compilar el DataFrame final
fechas_lista = []
ingresos_lista = []
egresos_lista = []
saldos_lista = []
gasto_extra_lista = []

saldo_actual = efectivo_inicial
fecha_quiebra = None

# Simulación iterativa día por día
for i in range(dias_proyeccion):
    fecha_actual = fecha_inicio + timedelta(days=i)
    
    # Cálculo de crecimiento compuesto: cada 30 días se aplica la tasa de interés compuesto
    meses_transcurridos = i // 30
    ventas_del_dia = ingresos_fijos * ((1 + crecimiento_mensual) ** meses_transcurridos) * factor_ingresos
    
    # Evaluar si hoy aplica el gasto extraordinario programado
    egreso_extra_hoy = 0.0
    if activar_extraordinario and fecha_actual == fecha_extraordinaria:
        egreso_extra_hoy = monto_gasto
        
    egresos_del_dia = egresos_operativos_diarios + egreso_extra_hoy
    
    # Actualización del saldo de caja
    saldo_actual += (ventas_del_dia - egresos_del_dia)
    
    if saldo_actual <= 0 and fecha_quiebra is None:
        fecha_quiebra = fecha_actual
        saldo_actual = 0  
    elif saldo_actual < 0:
        saldo_actual = 0
        
    # Guardar registros de la simulación
    fechas_lista.append(fecha_actual)
    ingresos_lista.append(ventas_del_dia)
    egresos_lista.append(egresos_del_dia)
    saldos_lista.append(saldo_actual)
    gasto_extra_lista.append(egreso_extra_hoy)

# Construcción de DataFrames de análisis
df_diario = pd.DataFrame({
    "Fecha": pd.to_datetime(fechas_lista),
    "Ingresos": ingresos_lista,
    "Egresos Totales": egresos_lista,
    "Gasto Extraordinario": gasto_extra_lista,
    "Saldo Efectivo": saldos_lista
})

# Agregar columnas de gastos fijos individuales para desglose en exportación
for cat, valor in gastos_operativos_dict.items():
    df_diario[f"Gasto: {cat}"] = valor

# --- SECCIÓN 1: MÉTRICAS CLAVE ---
col1, col2, col3 = st.columns(3)

with col1:
    ingreso_medio = df_diario["Ingresos"].mean()
    st.metric(label="Ingreso Diario Promedio (Con Crecimiento)", value=f"${ingreso_medio:,.2f}")

with col2:
    egreso_medio = df_diario["Egresos Totales"].mean()
    st.metric(label="Egreso Diario Promedio (Incluye Extras)", value=f"${egreso_medio:,.2f}")

with col3:
    if fecha_quiebra:
        dias_restantes = (fecha_quiebra - fecha_inicio).days
        st.error(f"🚨 ¡Alerta de Runway!\n\nEfectivo agotado el: {fecha_quiebra.strftime('%d/%m/%Y')} ({dias_restantes} días de margen).")
    else:
        st.success("✅ Caja Saludable. La aceleración de ventas compensa tus egresos en el periodo proyectado.")

# --- SECCIÓN 2: PANEL DE ALERTAS FINANCIERAS ---
st.subheader("⚠️ Panel de Alertas Tempranas")
col_al1, col_al2, col_al3 = st.columns(3)

with col_al1:
    # Comparar el último mes vs el primero para verificar tracción financiera
    ventas_iniciales_total = df_diario["Ingresos"].iloc[0]
    ventas_finales_total = df_diario["Ingresos"].iloc[-1]
    incremento_real_ventas = ((ventas_finales_total - ventas_iniciales_total) / ventas_iniciales_total) * 100
    st.info(f"📈 **Efecto Compuesto**: Tus ventas diarias pasarán de **${ventas_iniciales_total:,.2f}** a **${ventas_finales_total:,.2f}** al final del período (+{incremento_real_ventas:.1f}%).")

with col_al2:
    # Impacto del gasto extraordinario sobre la caja inicial
    if activar_extraordinario and efectivo_inicial > 0:
        peso_extraordinario = (monto_gasto / efectivo_inicial) * 100
        if peso_extraordinario > 50:
            st.error(f"❌ **Riesgo por Evento Único**: El gasto de '{nombre_gasto}' drena el {peso_extraordinario:.1f}% de tu efectivo inicial de forma inmediata.")
        elif peso_extraordinario > 20:
            st.warning(f"⚠️ **Impacto Moderado**: El gasto de '{nombre_gasto}' consume el {peso_extraordinario:.1f}% de tu liquidez inicial.")
        else:
            st.success(f"💚 **Gasto Extra Absorbible**: Representa solo el {peso_extraordinario:.1f}% de la caja de inicio.")

with col_al3:
    # Margen operativo final neto diario (sin contar gastos extraordinarios puntuales)
    ultimo_ingreso = df_diario["Ingresos"].iloc[-1]
    if ultimo_ingreso > egresos_operativos_diarios:
        st.success(f"💚 **Punto de Equilibrio Logrado**: Hacia el final de la proyección tu negocio genera ganancias operativas diarias netas.")
    else:
        st.warning(f"⚠️ **Dependencia de Capital**: Al final del periodo, el crecimiento aún no cubre tus gastos fijos diarios.")

st.markdown("---")

# --- SECCIÓN 3: GRÁFICOS EVOLUTIVOS ---
st.subheader("📈 Proyecciones del Efectivo e Ingresos vs Gastos")
col_graf1, col_graf2 = st.columns(2)

with col_graf1:
    fig_linea = go.Figure()
    fig_linea.add_trace(go.Scatter(
        x=df_diario["Fecha"], y=df_diario["Saldo Efectivo"], mode='lines', name='Saldo en Caja',
        line=dict(color='#2ca02c' if (df_diario["Saldo Efectivo"].iloc[-1] > 0) else '#d62728', width=3), fill='tozeroy'
    ))
    fig_linea.add_trace(go.Scatter(x=df_diario["Fecha"], y=[0]*len(df_diario), mode='lines', name='Límite Crítico ($0)', line=dict(color='black', width=1, dash='dash')))
    
    # Marcar el evento extraordinario en la gráfica lineal si existe
    if activar_extraordinario:
        fig_linea.add_vline(x=pd.to_datetime(fecha_extraordinaria), line_width=2, line_dash="dash", line_color="orange", annotation_text=f"Impacto: {nombre_gasto}")
        
    fig_linea.update_layout(title="Evolución Diaria del Efectivo ($)", xaxis_title="Fecha", yaxis_title="Efectivo", template="plotly_white", margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_linea, use_container_width=True)

with col_graf2:
    df_mensual = df_diario.copy()
    df_mensual["Mes"] = df_mensual["Fecha"].dt.strftime('%b %Y')
    df_mes_agrupado = df_mensual.groupby("Mes", sort=False).agg({"Ingresos": "sum", "Egresos Totales": "sum"}).reset_index()
    
    fig_barra = go.Figure()
    fig_barra.add_trace(go.Bar(x=df_mes_agrupado["Mes"], y=df_mes_agrupado["Ingresos"], name="Ingresos Totales", marker_color='#1f77b4'))
    fig_barra.add_trace(go.Bar(x=df_mes_agrupado["Mes"], y=df_mes_agrupado["Egresos Totales"], name="Gastos Totales", marker_color='#ff7f0e'))
    fig_barra.update_layout(title="Comparativa Mensual Consolidada (Crecimiento vs Egresos)", barmode='group', xaxis_title="Mes", yaxis_title="Monto ($)", template="plotly_white", margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_barra, use_container_width=True)

st.markdown("---")

# --- SECCIÓN 4: DISTRIBUCIÓN DE COSTOS OPERATIVOS ---
st.subheader("🍰 Distribución de Costos Fijos Recurrentes (Estructura Base)")
col_torta, col_info_torta = st.columns(2)

with col_torta:
    df_torta = pd.DataFrame({"Categoría": list(gastos_operativos_dict.keys()), "Costo Diario": list(gastos_operativos_dict.values())})
    # Línea unificada en una sola línea para evitar errores de sangría
    fig_torta = px.pie(df_torta, values='Costo Diario', names='Categoría', hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe)
    fig_torta.update_traces(textposition='inside', textinfo='percent+label')
    fig_torta.update_layout(margin=dict(l=10, r=10, t=10, b=10), showlegend=True)
    st.plotly_chart(fig_torta, use_container_width=True)

with col_info_torta:
    st.markdown("#### 💡 Análisis de Crecimiento vs Estructura")
    categoria_max = max(gastos_operativos_dict, key=gastos_operativos_dict.get)
    st.info(f"Tu principal centro de costo operativo base es **{categoria_max}**.")
    st.markdown("""
    Al incorporar un **crecimiento compuesto**, vas a notar cómo el gráfico de barras mensual empieza a mostrar barras azules más altas con el paso del tiempo. 
    
    Si tu curva de efectivo cae bruscamente en un punto medio y luego se estabiliza, se debe al impacto directo del **Gasto Extraordinario** programado en la barra lateral.
    """)

# --- DETALLE DE DATOS Y EXPORTACIÓN ---
with st.expander("👀 Ver matriz detallada de datos y descargar"):
  df_exportar = df_diario.copy()
  df_exportar["Fecha"] = df_exportar["Fecha"].dt.strftime('%Y-%m-%d')
  st.dataframe(df_exportar.style.format({col: "${:,.2f}" for col in 
                                         df_exportar.columns if col != "Fecha"}))

def convertir_a_excel(dataframe):
  output = io.BytesIO()
  with pd.ExcelWriter(output, engine='openpyxl') as writer:
    dataframe.to_excel(writer, index=False, sheet_name='Flujo Dinámico Diario')
    df_mes_agrupado.to_excel(writer, index=False, sheet_name='Resumen Mensual Compuesto')
    return output.getvalue()

excel_data = convertir_a_excel(df_exportar)
st.download_button(
  label="📥 Descargar Reporte Financiero Avanzado en Excel (.xlsx)",
  data=excel_data,
  file_name=f"cashflow_precision_{datetime.today().strftime('%Y%m%d')}.xlsx",
  mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
