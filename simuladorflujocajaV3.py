import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import io

# Configuración de la página
st.set_page_config(page_title="Simulador de Flujo de Caja", layout="wide", page_icon="📊")

st.title("📊 Simulador Financiero Profesional con Estacionalidad")
st.markdown("Proyectá tu caja controlando picos estacionales de ventas y cargando múltiples gastos extraordinarios en una tabla interactiva.")

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

st.sidebar.header("📉 Egresos Diarios Operativos")
g_salarios = st.sidebar.number_input("🧑‍💻 Salarios y Nómina ($)", min_value=0.0, value=800.0)
g_marketing = st.sidebar.number_input("📣 Marketing y Pauta ($)", min_value=0.0, value=400.0)
g_software = st.sidebar.number_input("💻 Software y SaaS ($)", min_value=0.0, value=150.0)
g_proveedores = st.sidebar.number_input("📦 Proveedores y Stock ($)", min_value=0.0, value=500.0)
g_alquiler = st.sidebar.number_input("🏢 Alquiler y Servicios ($)", min_value=0.0, value=250.0)

st.sidebar.header("🔮 Escenario de Estrés Global")
factor_ingresos = st.sidebar.slider("Optimismo de Ventas (%)", min_value=0, max_value=200, value=100) / 100.0
factor_gastos = st.sidebar.slider("Incremento de Gastos Fijos (%)", min_value=100, max_value=200, value=100) / 100.0

# --- SECCIÓN CENTRAL PRINCIPAL: CONFIGURACIONES AVANZADAS ---
st.subheader("🛠️ Configuraciones Avanzadas del Modelo")
col_config1, col_config2 = st.columns(2)

with col_config1:
    st.markdown("##### 🍂 Estacionalidad Mensual de Ventas")
    st.caption("Ajustá el rendimiento esperado de cada mes (100% = Normal, 50% = Caída a la mitad, 150% = Temporada Alta).")
    
    # Generar dinámicamente los meses a proyectar para el selector
    fecha_inicio = datetime.today().date()
    meses_indices = [(fecha_inicio + timedelta(days=x)).strftime('%B %Y') for x in range(0, dias_proyeccion, 30)]
    meses_unicos = list(dict.fromkeys(meses_indices)) # Remover duplicados manteniendo el orden
    
    # Crear un diccionario para almacenar los factores estacionales por mes
    dict_estacionalidad = {}
    col_mes1, col_mes2 = st.columns(2)
    for idx, mes in enumerate(meses_unicos):
        target_col = col_mes1 if idx % 2 == 0 else col_mes2
        with target_col:
            val_estacional = st.slider(f"{mes} (%)", min_value=10, max_value=200, value=100, key=f"est_{mes}")
            dict_estacionalidad[mes] = val_estacional / 100.0

with col_config2:
    st.markdown("##### 🗓️ Tabla de Múltiples Gastos Extraordinarios")
    st.caption("Hacé clic en las celdas para editar o agregar filas al final de la tabla para programar impuestos, aguinaldos o compras de activos.")
    
    # DataFrame por defecto para guiar al usuario
    df_extras_plantilla = pd.DataFrame([
        {"Concepto": "Impuesto Anual", "Monto ($)": 12000.0, "Día de Impacto (1 al 365)": 45},
        {"Concepto": "Renovación Licencias", "Monto ($)": 5000.0, "Día de Impacto (1 al 365)": 90}
    ])
    
    # Editor interactivo con tipado estricto para evitar fallos de simulación con celdas vacías
    config_columnas = {
        "Concepto": st.column_config.TextColumn("Concepto", default="Gasto Extra", required=True),
        "Monto ($)": st.column_config.NumberColumn("Monto ($)", default=0.0, min_value=0.0, required=True),
        "Día de Impacto (1 al 365)": st.column_config.NumberColumn("Día de Impacto", default=1, min_value=1, max_value=365, required=True)
    }
    
    df_extras_usuario = st.data_editor(df_extras_plantilla, num_rows="dynamic", key="tabla_gastos_extra", column_config=config_columnas)

# --- CÁLCULOS CRONOLÓGICOS DEL FLUJO DE CAJA ---
gastos_operativos_dict = {
    "Salarios": g_salarios * factor_gastos,
    "Marketing": g_marketing * factor_gastos,
    "Software/SaaS": g_software * factor_gastos,
    "Proveedores": g_proveedores * factor_gastos,
    "Alquiler/Servicios": g_alquiler * factor_gastos
}
egresos_operativos_diarios = sum(gastos_operativos_dict.values())

fechas_lista, ingresos_lista, egresos_lista, saldos_lista, gasto_extra_lista, nombres_extra_lista = [], [], [], [], [], []
saldo_actual = efectivo_inicial
fecha_quiebra = None

# Procesar la tabla de gastos extraordinarios del usuario en un diccionario indexado por el número de día
dict_gastos_por_dia = {}
if df_extras_usuario is not None and not df_extras_usuario.empty:
    for _, fila in df_extras_usuario.iterrows():
        try:
            dia_num = int(fila["Día de Impacto (1 al 365)"])
            monto_ex = float(fila["Monto ($)"])
            concepto_ex = str(fila["Concepto"])
            if dia_num in dict_gastos_por_dia:
                dict_gastos_por_dia[dia_num]["monto"] += monto_ex
                dict_gastos_por_dia[dia_num]["concepto"] += f", {concepto_ex}"
            else:
                dict_gastos_por_dia[dia_num] = {"monto": monto_ex, "concepto": concepto_ex}
        except:
            pass # Prevenir errores si el usuario deja filas incompletas en la tabla

# Simulación iterativa día por día
for i in range(dias_proyeccion):
    fecha_actual = fecha_inicio + timedelta(days=i)
    nombre_mes_actual = fecha_actual.strftime('%B %Y')
    
    # Factor estacional correspondiente a este mes
    factor_estacional_hoy = dict_estacionalidad.get(nombre_mes_actual, 1.0)
    
    # Crecimiento compuesto mensual + Escenario + Estacionalidad
    meses_transcurridos = i // 30
    ventas_del_dia = ingresos_fijos * ((1 + crecimiento_mensual) ** meses_transcurridos) * factor_ingresos * factor_estacional_hoy
    
    # Verificar si hoy cae un gasto extraordinario (el día 1 de la simulación corresponde a i=0, mapeado al día número 1)
    dia_actual_simulado = i + 1
    egreso_extra_hoy = 0.0
    concepto_extra_hoy = ""
    if dia_actual_simulado in dict_gastos_por_dia:
        egreso_extra_hoy = dict_gastos_por_dia[dia_actual_simulado]["monto"]
        concepto_extra_hoy = dict_gastos_por_dia[dia_actual_simulado]["concepto"]
        
    egresos_del_dia = egresos_operativos_diarios + egreso_extra_hoy
    saldo_actual += (ventas_del_dia - egresos_del_dia)
    
    if saldo_actual <= 0 and fecha_quiebra is None:
        fecha_quiebra = fecha_actual
        saldo_actual = 0  
    elif saldo_actual < 0:
        saldo_actual = 0
        
    fechas_lista.append(fecha_actual)
    ingresos_lista.append(ventas_del_dia)
    egresos_lista.append(egresos_del_dia)
    saldos_lista.append(saldo_actual)
    gasto_extra_lista.append(egreso_extra_hoy)
    nombres_extra_lista.append(concepto_extra_hoy)

df_diario = pd.DataFrame({
    "Fecha": pd.to_datetime(fechas_lista),
    "Ingresos": ingresos_lista,
    "Egresos Totales": egresos_lista,
    "Gasto Extraordinario": gasto_extra_lista,
    "Detalle Gasto Extra": nombres_extra_lista,
    "Saldo Efectivo": saldos_lista
})

for cat, valor in gastos_operativos_dict.items():
    df_diario[f"Gasto Fijo: {cat}"] = valor

# --- SECCIÓN: MÉTRICAS CLAVE ---
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Ingreso Diario Promedio", value=f"${df_diario['Ingresos'].mean():,.2f}")
with col2:
    st.metric(label="Egreso Diario Promedio (Fijos + Extras)", value=f"${df_diario['Egresos Totales'].mean():,.2f}")
with col3:
    if fecha_quiebra:
        st.error(f"🚨 ¡Runway Agotado!\n\nEfectivo en $0 el: {fecha_quiebra.strftime('%d/%m/%Y')}")
    else:
        st.success("✅ Caja Saludable. El negocio resiste el periodo simulado.")

# --- SECCIÓN: GRÁFICOS EVOLUTIVOS ---
st.subheader("📈 Proyecciones del Efectivo e Ingresos vs Gastos")
col_graf1, col_graf2 = st.columns(2)

with col_graf1:
    fig_linea = go.Figure()
    fig_linea.add_trace(go.Scatter(
        x=df_diario["Fecha"], y=df_diario["Saldo Efectivo"], mode='lines', name='Saldo en Caja',
        line=dict(color='#2ca02c' if (df_diario["Saldo Efectivo"].iloc[-1] > 0) else '#d62728', width=3), fill='tozeroy'
    ))
    fig_linea.add_trace(go.Scatter(x=df_diario["Fecha"], y=np.zeros(len(df_diario)), mode='lines', name='Límite Crítico ($0)', line=dict(color='black', width=1, dash='dash')))
    
    # Dibujar líneas verticales automáticas para cada gasto extraordinario detectado
    df_hitosextra = df_diario[df_diario["Gasto Extraordinario"] > 0]
    for _, hito in df_hitosextra.iterrows():
        fig_linea.add_vline(x=hito["Fecha"], line_width=1.5, line_dash="dash", line_color="orange")
        
    fig_linea.update_layout(title="Evolución Diaria del Efectivo ($)", xaxis_title="Fecha", yaxis_title="Efectivo", template="plotly_white", margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_linea, use_container_width=True)

with col_graf2:
    df_mensual = df_diario.copy()
    df_mensual["Mes"] = df_mensual["Fecha"].dt.strftime('%b %Y')
    df_mes_agrupado = df_mensual.groupby("Mes", sort=False).agg({"Ingresos": "sum", "Egresos Totales": "sum"}).reset_index()
    
    fig_barra = go.Figure()
    fig_barra.add_trace(go.Bar(x=df_mes_agrupado["Mes"], y=df_mes_agrupado["Ingresos"], name="Ingresos Totales", marker_color='#1f77b4'))
    fig_barra.add_trace(go.Bar(x=df_mes_agrupado["Mes"], y=df_mes_agrupado["Egresos Totales"], name="Gastos Totales", marker_color='#ff7f0e'))
    fig_barra.update_layout(title="Comparativa Mensual Consolidada (Con Estacionalidad)", barmode='group', xaxis_title="Mes", yaxis_title="Monto ($)", template="plotly_white", margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_barra, use_container_width=True)

# --- SECCIÓN: DISTRIBUCIÓN DE COSTOS OPERATIVOS ---
st.subheader("🍰 Estructura Involucrada en Costos Fijos Recurrentes")
col_torta, col_info_torta = st.columns(2)

with col_torta:
    df_torta = pd.DataFrame({"Categoría": list(gastos_operativos_dict.keys()), "Costo Diario": list(gastos_operativos_dict.values())})
fig_torta = px.pie(df_torta, values='Costo Diario', names='Categoría', 
                   hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe)
fig_torta.update_traces(textposition='inside', textinfo='percent+label')
fig_torta.update_layout(margin=dict(l=10, r=10, t=10, b=10), 
                        showlegend=True)
st.plotly_chart(fig_torta, use_container_width=True)

with col_info_torta:
    st.markdown("#### 💡 Comportamiento del Modelo Dinámico")
    monto_total_extras = df_diario["Gasto Extraordinario"].sum()
    st.info(f"Suma acumulada de impactos extraordinarios programados en la simulación: ${monto_total_extras:,.2f}.")
    st.markdown("""
    Al manipular los deslizadores de Estacionalidad Mensual, alterarás directamente el volumen de las barras azules de ingresos del gráfico superior.

    Esto te permite ensayar escenarios complejos como: ¿Qué pasa si mis ventas caen al 40% en los meses de vacaciones y simultáneamente tengo que pagar los impuestos cargados en la tabla de la derecha?
    """)

st.markdown("---")

# --- DETALLE DE DATOS Y EXPORTACIÓN ---
with st.expander("👀 Ver matriz detallada de datos y descargar"):
    df_exportar = df_diario.copy()
    df_exportar["Fecha"] = df_exportar["Fecha"].dt.strftime('%Y-%m-%d')
    st.dataframe(df_exportar.style.format({col: "${:,.2f}" for col in df_exportar.columns if col not in ["Fecha", "Detalle Gasto Extra"]}))
    
    # Función interna de empaquetado Excel en memoria
    def convertir_a_excel(dataframe):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            dataframe.to_excel(writer, index=False, sheet_name='Flujo Dinámico Diario')
            df_mes_agrupado.to_excel(writer, index=False, sheet_name='Resumen Mensual Compuesto')
        return output.getvalue()

    excel_data = convertir_a_excel(df_exportar)
    nombre_archivo = f"cashflow_estacionalidad_{datetime.today().strftime('%Y%m%d')}.xlsx"

    # Botón en una sola línea continua para evitar errores de sintaxis
    st.download_button(label="📥 Descargar Reporte Financiero Completo en Excel (.xlsx)", data=excel_data, file_name=nombre_archivo, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
