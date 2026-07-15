import streamlit as st
import pandas as pd
import plotly.express as px
from src.db import supabase

st.set_page_config(
    page_title="Sistema de Gestión SOFOM - Core Engine",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos corporativos limpios y formales
st.markdown("""
    <style>
    .main-header {font-size: 26px; font-weight: bold; color: #1A365D; margin-bottom: 0px;}
    .sub-header {font-size: 15px; color: #4A5568; font-style: italic; margin-top: 0px;}
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">Suite Operativa y Gestión de Crédito (SOFOM E.N.R.)</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Fase de Validación — Control Institucional en Tiempo Real</p>', unsafe_allow_html=True)
st.divider()

# Consulta transaccional en tiempo real para calcular KPIs
@st.cache_data(ttl=30)
def obtener_kpis_cartera():
    try:
        res_prestamos = supabase.table("prestamos").select("monto_principal, tasa_interes_mensual, estatus_credito").execute()
        res_clientes = supabase.table("clientes").select("id_cliente", count="exact").execute()
        
        total_clientes = res_clientes.count if res_clientes.count is not None else 0
        
        if res_prestamos.data:
            df_p = pd.DataFrame(res_prestamos.data)
            capital_colocado = float(df_p["monto_principal"].sum())
            prestamos_activos = len(df_p[df_p["estatus_credito"] == "VIGENTE"])
            interes_mensual_proyectado = float((df_p["monto_principal"] * df_p["tasa_interes_mensual"]).sum())
        else:
            capital_colocado = 0.0
            prestamos_activos = 0
            interes_mensual_proyectado = 0.0
            
        return total_clientes, capital_colocado, prestamos_activos, interes_mensual_proyectado
    except Exception:
        return 0, 0.0, 0, 0.0

total_cli, cap_colocado, prest_activos, int_proyectado = obtener_kpis_cartera()
fondo_prueba_total = 150000.0
capital_disponible = fondo_prueba_total - cap_colocado

st.subheader("Estado General del Fondo y Métricas de Cartera")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(label="Capital Colocado (Activo)", value=f"${cap_colocado:,.2f}", delta=f"Disponible: ${capital_disponible:,.2f}")
with col2:
    st.metric(label="Créditos Formalizados", value=f"{prest_activos} contratos", delta=f"{total_cli} clientes en base")
with col3:
    st.metric(label="Interés Bruto Proyectado / Mes", value=f"${int_proyectado:,.2f}", delta="Rotación continua")
with col4:
    comision_proyectada = int_proyectado * 0.20
    st.metric(label="Comisión Operativa Proyectada (20%)", value=f"${comision_proyectada:,.2f}", delta="Ingreso Administrador")

st.divider()

# Sección de Protocolos y Distribución de Capital
col_left, col_right = st.columns([1, 1])

with col_left:
    st.markdown("### Protocolo Institucional y Cumplimiento")
    st.info("""
    **1. Evaluación Paramétrica:** Todo crédito otorgado pasó estrictamente por el filtro algorítmico de liquidez (Regla del 30%) en el Módulo de Admisión.
    
    **2. Conciliación Matemáticamente Exacta:** Los calendarios de amortización se calculan con ajuste de cierre, eliminando descuadres contables de centavos.
    
    **3. Trazabilidad Inmutable:** Cada pagaré y contrato legal emitido se respalda en una transacción única dentro del servidor PostgreSQL.
    """)

with col_right:
    st.markdown("### Distribución del Retorno por Intereses")
    labels = ['Dividendos Socios Capitalistas (65%)', 'Comisión Operadora (20%)', 'Reserva de Morosidad (15%)']
    values = [65, 20, 15]
    fig = px.pie(names=labels, values=values, color_discrete_sequence=['#1A365D', '#2B6CB0', '#81E6D9'])
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=220, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)