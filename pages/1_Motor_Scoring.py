import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Motor de Scoring | SOFOM", page_icon="⚡", layout="wide")

# Inicializar memoria temporal si no hay conexión a base de datos aún
if 'cartera_temporal' not in st.session_state:
    st.session_state.cartera_temporal = []

st.title("⚡ Motor Cuantitativo de Admisión y Scoring")
st.markdown("Evaluación algorítmica para mitigar la selección adversa en créditos de $5,000 a $15,000 MXN.")
st.divider()

col_form, col_res = st.columns([1, 1.2])

with col_form:
    st.subheader("1. Parámetros del Solicitante")
    with st.form("form_admision"):
        nombre = st.text_input("Nombre Completo del Cliente:", value="Carlos Mendoza López")
        rfc = st.text_input("RFC con Homoclave (13 dígitos):", value="MELC950812H21", max_chars=13)
        
        st.markdown("---")
        st.markdown("#### Datos Financieros Mensuales")
        ingreso = st.number_input("Ingreso Neto Comprobado ($):", min_value=1000.0, value=18500.0, step=500.0)
        gastos = st.number_input("Gastos Fijos Estimados ($):", min_value=0.0, value=8200.0, step=500.0)
        deudas = st.number_input("Pago Mensual de Deudas en Buró ($):", min_value=0.0, value=2300.0, step=100.0)
        puntaje = st.slider("Puntaje en Buró de Crédito (Score):", min_value=400, max_value=850, value=680, step=10)
        
        st.markdown("---")
        st.markdown("#### Condiciones del Crédito")
        monto = st.number_input("Monto Solicitado ($):", min_value=3000.0, max_value=30000.0, value=15000.0, step=1000.0)
        plazo_quincenas = st.selectbox("Plazo de Pago (Quincenas):", options=[6, 12, 18, 24], index=1)
        tasa_mensual = st.number_input("Tasa de Interés Mensual (%):", min_value=1.0, max_value=15.0, value=6.0, step=0.5) / 100.0
        
        evaluar = st.form_submit_button("⚖️ Ejecutar Evaluación Algorítmica", use_container_width=True)

with col_res:
    st.subheader("2. Resultado del Algoritmo y Semáforo")
    
    # Cálculos matemáticos
    flujo_libre = ingreso - gastos - deudas
    capacidad_pago_quincenal = (flujo_libre * 0.30) / 2.0
    
    # Cálculo de cuota quincenal (Sistema Francés)
    tasa_quincenal = tasa_mensual / 2.0
    if tasa_quincenal > 0:
        cuota_quincenal = monto * (tasa_quincenal * (1 + tasa_quincenal)**plazo_quincenas) / ((1 + tasa_quincenal)**plazo_quincenas - 1)
    else:
        cuota_quincenal = monto / plazo_quincenas
        
    ratio_compromiso = cuota_quincenal / (flujo_libre / 2.0) if flujo_libre > 0 else 1.0
    
    # Mostrar métricas intermedias
    c1, c2, c3 = st.columns(3)
    c1.metric("Flujo Libre Real", f"${flujo_libre:,.2f} MXN")
    c2.metric("Capacidad Máx. (30%)", f"${capacidad_pago_quincenal:,.2f} MXN")
    c3.metric("Cuota Proyectada", f"${cuota_quincenal:,.2f} MXN")
    
    st.markdown("---")
    
    # Semáforo de Decisión
    if flujo_libre <= 0:
        st.error("🚨 **RECHAZADO — DÉFICIT DE FLUJO:** El solicitante no cuenta con liquidez para asumir nuevas deudas.")
        status_code = "RECHAZADO"
    elif ratio_compromiso <= 0.30 and puntaje >= 650:
        st.success(f"✅ **APROBADO — RIESGO BAJO:** El crédito compromete solo el **{ratio_compromiso*100:.1f}%** de su capacidad quincenal. Cumple con buró y liquidez.")
        status_code = "APROBADO"
    elif ratio_compromiso <= 0.40 and puntaje >= 600:
        st.warning(f"⚠️ **CONDICIONADO — RIESGO MEDIO:** Compromete el **{ratio_compromiso*100:.1f}%** de su capacidad. Requerir aval solidario o garantía prendaria para proceder.")
        status_code = "CONDICIONADO"
    else:
        st.error(f"❌ **RECHAZADO — ALTO RIESGO:** Compromiso excesivo ({ratio_compromiso*100:.1f}%) o historial en buró insuficiente ({puntaje} pts).")
        status_code = "RECHAZADO"
        
    st.divider()
    
    # Botón de Guardado
    if st.button("📁 Registrar Cliente en Cartera Operativa", type="primary", use_container_width=True):
        nuevo_registro = {
            "Cliente": nombre,
            "RFC": rfc,
            "Monto": f"${monto:,.2f}",
            "Cuota Quincenal": f"${cuota_quincenal:,.2f}",
            "Puntaje Buró": puntaje,
            "Estatus": status_code
        }
        st.session_state.cartera_temporal.append(nuevo_registro)
        st.toast("¡Cliente registrado exitosamente en memoria temporal! 🚀")

# Mostrar tabla inferior si hay clientes guardados
if st.session_state.cartera_temporal:
    st.markdown("### 📋 Historial de Evaluaciones de la Sesión")
    df_memoria = pd.DataFrame(st.session_state.cartera_temporal)
    st.dataframe(df_memoria, use_container_width=True)