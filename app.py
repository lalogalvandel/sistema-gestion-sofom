import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración general de la página
st.set_page_config(
    page_title="Sistema de Gestión SOFOM - Core Engine",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos personalizados (Azul marino corporativo y Turquesa)
st.markdown("""
    <style>
    .main-header {font-size: 28px; font-weight: bold; color: #1A365D; margin-bottom: 0px;}
    .sub-header {font-size: 16px; color: #4A5568; font-style: italic; margin-top: 0px;}
    .kpi-card {background-color: #F7FAFC; padding: 20px; border-radius: 10px; border-left: 5px solid #2B6CB0;}
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">🏛️ Suite Operativa y Gestión de Crédito (SOFOM E.N.R.)</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Fase de Validación y Prueba — Fondo Inicial $150,000 MXN</p>', unsafe_allow_html=True)
st.divider()

# Sección 1: KPIs en Tiempo Real (Portafolio de Prueba)
st.subheader("📊 Estado del Fondo y Métricas Operativas")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(label="💰 Capital de Colocación", value="$150,000 MXN", delta="100% Disponible")
with col2:
    st.metric(label="🎯 Tasa de Interés Meta", value="6.00% mensual", delta="Amortización Quincenal")
with col3:
    st.metric(label="🛡️ Límite por Crédito", value="$15,000 MXN", delta="Máx. 10% del fondo")
with col4:
    st.metric(label="⚙️ Tu Comisión Operativa", value="20.00%", delta="Sobre interés cobrado")

st.divider()

# Sección 2: Explicación del Modelo para Socios
col_left, col_right = st.columns([1, 1])

with col_left:
    st.markdown("### 🔒 Protocolo de Mitigación de Riesgo")
    st.info("""
    **1. Cero intuición:** Todo préstamo requiere evaluación matemática en el *Motor de Scoring*.
    
    **2. Regla del 30%:** Ninguna cuota quincenal puede superar el 30% del flujo libre comprobado del cliente.
    
    **3. Respaldo Legal:** Todo crédito aprobado genera un contrato de adhesión y pagaré ejecutivo listo para firma legal.
    """)

with col_right:
    st.markdown("### 💼 Distribución de Utilidades del Fondo")
    # Gráfica ilustrativa del reparto
    labels = ['Dividendos Socios Capitalistas (65%)', 'Tu Comisión Operativa (20%)', 'Reserva de Morosidad (15%)']
    values = [65, 20, 15]
    fig = px.pie(names=labels, values=values, color_discrete_sequence=['#1A365D', '#2B6CB0', '#81E6D9'])
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=220, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

st.sidebar.success("👈 Selecciona una opción en el menú superior para operar el sistema.")