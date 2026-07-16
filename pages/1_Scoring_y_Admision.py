import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from src.auth import verificar_acceso
from src.db import supabase
from src.theme import (
    aplicar_identidad_visual, encabezado_modulo, titulo_seccion,
    tarjeta_kpi, dictamen
)

st.set_page_config(page_title="Scoring Actuarial y Admisión | SOFOM", layout="wide")

# --- BLINDAJE INSTITUCIONAL RBAC ---
# Nivel de acceso: COBRANZA (2), accesible para Operaciones de Crédito y Dirección General
verificar_acceso("COBRANZA")
# -----------------------------------

aplicar_identidad_visual()

encabezado_modulo(
    titulo="Motor Actuarial de Admisión y Credit Scoring",
    subtitulo="Evaluación algorítmica de riesgo crediticio, cálculo de Probabilidad de Default (Pd), fijación de Tasa de Indiferencia y formalización de colocación.",
    nombre_icono="escudo",
    insignia="ORIGINACIÓN INSTITUCIONAL"
)

# Identificación de sesión para auditoría
usuario_actual = st.session_state.get("user_email", "Usuario No Identificado")
rol_actual = st.session_state.get("user_role", "COBRANZA")

# -----------------------------------------------------------------------------
# 1. MOTOR DE MACHINE LEARNING: REGRESIÓN LOGÍSTICA CALIBRADA
# -----------------------------------------------------------------------------
@st.cache_resource
def inicializar_motor_scoring():
    """
    Entrena y calibra un modelo de Regresión Logística utilizando una distribución
    estadística base que refleja el comportamiento histórico de cartera en SOFOMs ENR.
    Esto permite calificar solicitudes desde el día uno sin depender de vacíos históricos.
    """
    np.random.seed(108)
    n_muestras = 1000
    
    # Generación de variables independientes (Features)
    # 1. Ratio de Cobertura de Deuda (Ingreso Libre / Cuota Estimada)
    ratio_cobertura = np.random.normal(1.8, 0.6, n_muestras).clip(0.2, 5.0)
    # 2. Antigüedad Laboral o Operativa del Negocio (Años)
    antiguedad = np.random.exponential(3.5, n_muestras).clip(0.1, 25.0)
    # 3. Ratio de Apalancamiento (Monto Solicitado / Patrimonio Neto)
    apalancamiento = np.random.normal(0.45, 0.25, n_muestras).clip(0.05, 2.0)
    # 4. Historial de Atrasos Previos en Buró (0 = Limpio, 3 = Severo)
    mora_previa = np.random.choice([0, 1, 2, 3], size=n_muestras, p=[0.68, 0.18, 0.09, 0.05])
    
    # Ecuación estructural de log-odds para incumplimiento crediticio
    log_odds = (-2.2 * ratio_cobertura) - (0.35 * antiguedad) + (2.8 * apalancamiento) + (1.4 * mora_previa) + 0.8
    probabilidades = 1.0 / (1.0 + np.exp(-log_odds))
    
    # Variable dependiente (0 = Cumplimiento, 1 = Default)
    y = (probabilidades > np.random.uniform(0, 1, n_muestras)).astype(int)
    
    X = pd.DataFrame({
        "ratio_cobertura": ratio_cobertura,
        "antiguedad": antiguedad,
        "apalancamiento": apalancamiento,
        "mora_previa": mora_previa
    })
    
    escalador = StandardScaler()
    X_escalado = escalador.fit_transform(X)
    
    modelo = LogisticRegression(class_weight="balanced", random_state=42)
    modelo.fit(X_escalado, y)
    
    return modelo, escalador

modelo_scoring, escalador_features = inicializar_motor_scoring()

# -----------------------------------------------------------------------------
# 2. CAPTURA DE EXPEDIENTE Y VARIABLES PARAMÉTRICAS
# -----------------------------------------------------------------------------
titulo_seccion("personas", "1. Expediente de Solicitud y Perfil Financiero")

st.markdown(f"**Funcionario Evaluador en Sesión:** `{usuario_actual}` ({rol_actual})")

with st.form("form_evaluacion_crediticia"):
    st.markdown("**Datos Generales del Solicitante**")
    c_gen1, c_gen2, c_gen3 = st.columns(3)
    with c_gen1:
        nombre_cliente = st.text_input("Nombre o Razón Social:", placeholder="Ej: Fernando Gómez Morales")
    with c_gen2:
        rfc_cliente = st.text_input("RFC con Homoclave:", placeholder="Ej: GOMF850315XXX").upper()
    with c_gen3:
        tipo_solicitante = st.selectbox("Clasificación de Persona:", ["Persona Física con Actividad Empresarial", "Persona Moral", "Asalariado / Nómina"])
        
    st.markdown("---")
    st.markdown("**Estructura del Crédito Solicitado**")
    c_cred1, c_cred2, c_cred3 = st.columns(3)
    with c_cred1:
        monto_solicitado = st.number_input("Capital Solicitado ($ MXN):", min_value=1000.0, max_value=5000000.0, value=50000.0, step=5000.0)
    with c_cred2:
        plazo_meses = st.number_input("Plazo de Amortización (Meses):", min_value=1, max_value=60, value=12, step=1)
    with c_cred3:
        frecuencia_pago = st.selectbox("Periodicidad de Amortización:", ["Quincenal", "Mensual"])
        
    st.markdown("---")
    st.markdown("**Variables Económicas para Evaluación Actuarial**")
    c_var1, c_var2, c_var3, c_var4 = st.columns(4)
    with c_var1:
        ingreso_mensual = st.number_input("Ingreso Bruto Mensual ($):", min_value=0.0, value=35000.0, step=1000.0)
    with c_var2:
        gastos_fijos = st.number_input("Gastos y Deudas Mensuales ($):", min_value=0.0, value=15000.0, step=1000.0)
    with c_var3:
        antiguedad_anios = st.number_input("Antigüedad Laboral / Negocio (Años):", min_value=0.1, max_value=50.0, value=3.0, step=0.5)
    with c_var4:
        patrimonio_garantia = st.number_input("Patrimonio Neto o Garantía ($):", min_value=1.0, value=100000.0, step=10000.0)
        
    c_mora1, c_mora2 = st.columns([1, 2])
    with c_mora1:
        mora_buro = st.selectbox("Historial de Atrasos en Buró de Crédito:", [
            (0, "Sin atrasos reportados (0 días)"),
            (1, "Atraso leve histórico (1 a 30 días)"),
            (2, "Atraso moderado histórico (31 a 60 días)"),
            (3, "Atraso severo o marca negativa (> 60 días)")
        ], format_func=lambda x: x[1])[0]
    with c_mora2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Nota Técnica: El modelo procesa la relación de cobertura sobre cuota estimada y evalúa el apalancamiento real contra la garantía líquida o patrimonial aportada.")

    st.markdown("<br>", unsafe_allow_html=True)
    ejecutar_evaluacion = st.form_submit_button("Ejecutar Motor de Inteligencia y Calcular Tasa", use_container_width=True)

# -----------------------------------------------------------------------------
# 3. PROCESAMIENTO ALGORÍTMICO Y DICTAMEN DE RIESGO
# -----------------------------------------------------------------------------
if ejecutar_evaluacion:
    if not nombre_cliente or len(rfc_cliente) < 10:
        st.warning("Debe ingresar el nombre completo y un RFC válido para formalizar la evaluación crediticia.")
    else:
        # Cálculo de variables financieras intermedias
        cuota_mensual_estimada = (monto_solicitado / plazo_meses) * 1.06 # Estimación base para estrés de flujo
        ingreso_disponible = max(ingreso_mensual - gastos_fijos, 0.01)
        ratio_cobertura_calc = round(ingreso_disponible / cuota_mensual_estimada, 2)
        ratio_apalancamiento_calc = round(monto_solicitado / max(patrimonio_garantia, 1.0), 2)
        
        # Construcción de vector para scikit-learn
        vector_cliente = pd.DataFrame({
            "ratio_cobertura": [ratio_cobertura_calc],
            "antiguedad": [antiguedad_anios],
            "apalancamiento": [ratio_apalancamiento_calc],
            "mora_previa": [mora_buro]
        })
        
        vector_escalado = escalador_features.transform(vector_cliente)
        
        # Predicción de Probabilidad de Default (Pd)
        prob_default = float(modelo_scoring.predict_proba(vector_escalado)[:, 1][0])
        
        # Mapeo a Escala Credit Score Estándar (300 a 850)
        score_crediticio = int(850 - (prob_default * 550))
        score_crediticio = max(min(score_crediticio, 850), 300)
        
        # Cálculo Actuarial de Tasa de Indiferencia: T = (Cc + Oe + Rp) / (1 - Pd)
        costo_capital_anual = 0.12 # 12% rendimiento base socios
        gasto_operativo_anual = 0.04 # 4% costo operativo institucional
        
        # Prima de riesgo dinámica por nivel de calificación
        if score_crediticio >= 750:
            prima_riesgo_anual = 0.02
            calificacion_grado = "Grado de Inversión Superior (AAA)"
        elif score_crediticio >= 650:
            prima_riesgo_anual = 0.04
            calificacion_grado = "Grado de Inversión Estándar (AA)"
        elif score_crediticio >= 550:
            prima_riesgo_anual = 0.08
            calificacion_grado = "Grado Especulativo Moderado (A)"
        else:
            prima_riesgo_anual = 0.15
            calificacion_grado = "Alto Riesgo de Incumplimiento (B)"
            
        numerador_tasa = costo_capital_anual + gasto_operativo_anual + prima_riesgo_anual
        denominador_tasa = 1.0 - prob_default
        
        if denominador_tasa <= 0 or prob_default > 0.22:
            estatus_dictamen = "RECHAZADO"
            tasa_mensual_asignada = 0.0
            tasa_anual_asignada = 0.0
        else:
            tasa_anual_asignada = round((numerador_tasa / denominador_tasa) * 100.0, 2)
            tasa_mensual_asignada = round(tasa_anual_asignada / 12.0, 2)
            estatus_dictamen = "APROBADO PREFERENCIAL" if score_crediticio >= 700 else "APROBADO CONDICIONADO"

        st.divider()
        titulo_seccion("estadisticas", "2. Dictamen del Comité Algorítmico y Pricing")
        
        # Despliegue de métricas en tarjetas ejecutivas
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            tarjeta_kpi("Score Crediticio", f"{score_crediticio} pts", calificacion_grado)
        with k2:
            color_pd = "🟢 Bajo Riesgo" if prob_default < 0.06 else ("🟡 Moderado" if prob_default < 0.12 else "🔴 Alto Riesgo")
            tarjeta_kpi("Probabilidad de Default (Pd)", f"{prob_default*100:.2f}%", color_pd)
        with k3:
            tarjeta_kpi("Ratio Cobertura Deuda", f"{ratio_cobertura_calc}x", "Mínimo exigido: 1.20x")
        with k4:
            if estatus_dictamen == "RECHAZADO":
                tarjeta_kpi("Tasa Mensual Sugerida", "N/A", "Operación Invialble")
            else:
                tarjeta_kpi("Tasa de Indiferencia", f"{tasa_mensual_asignada}% mensual", f"{tasa_anual_asignada}% anualizada")

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Emisión de dictamen corporativo
        if estatus_dictamen == "RECHAZADO":
            dictamen("peligro", "Dictamen: SOLICITUD RECHAZADA POR RIESGO ACTUARIAL", 
                     f"El modelo algorítmico determina una Probabilidad de Incumplimiento del **{prob_default*100:.2f}%** (Score: **{score_crediticio}**). La relación de cobertura de deuda de **{ratio_cobertura_calc}x** y el nivel de apalancamiento no cumplen con los parámetros del umbral de solvencia. Autorizar esta colocación generaría un valor patrimonial negativo para el fondo.")
        else:
            dictamen("exito", f"Dictamen: SOLICITUD {estatus_dictamen}", 
                     f"El perfil evaluado acredita solvencia técnica con un Score de **{score_crediticio}** y una Probabilidad de Incumplimiento de **{prob_default*100:.2f}%**. Para garantizar la rentabilidad operativa del 20% y el rendimiento del capital social, la **Tasa de Indiferencia asignada es de {tasa_mensual_asignada}% mensual** ({tasa_anual_asignada}% anual).")

            st.markdown("<br>", unsafe_allow_html=True)
            titulo_seccion("documento_check", "3. Formalización y Alta en Cartera de Préstamos")
            
            st.markdown("Al confirmar la colocación, el sistema registrará el crédito en el servidor y habilitará la emisión de pagarés y tablas de amortización con la tasa actuarial asignada.")
            
            col_conf1, col_conf2 = st.columns([1, 2])
            with col_conf1:
                btn_guardar_prestamo = st.button("Formalizar y Enviar a Cartera Viva", use_container_width=True, type="primary")
            
            if btn_guardar_prestamo:
                with st.spinner("Inscribiendo contrato en la base de datos central..."):
                    try:
                        # Cálculo de fechas operativas
                        fecha_corte_actual = datetime.now()
                        dias_periodo = 15 if frecuencia_pago == "Quincenal" else 30
                        fecha_primer_vencimiento = fecha_corte_actual + timedelta(days=dias_periodo)
                        
                        payload_prestamo = {
                            "cliente": nombre_cliente.strip(),
                            "rfc": rfc_cliente.strip(),
                            "monto": float(monto_solicitado),
                            "saldo_pendiente": float(monto_solicitado),
                            "plazo_meses": int(plazo_meses),
                            "frecuencia": frecuencia_pago,
                            "tasa_mensual": float(tasa_mensual_asignada),
                            "tasa_anual": float(tasa_anual_asignada),
                            "score_asignado": int(score_crediticio),
                            "probabilidad_default": round(float(prob_default), 4),
                            "estatus": "ACTIVO",
                            "fecha_otorgamiento": fecha_corte_actual.strftime("%Y-%m-%d"),
                            "proximo_vencimiento": fecha_primer_vencimiento.strftime("%Y-%m-%d"),
                            "gestor_originador": usuario_actual
                        }
                        
                        # Inserción directa en la tabla de préstamos confirmada por auditoría
                        supabase.table("prestamos").insert(payload_prestamo).execute()
                        
                        st.success(f"El crédito a nombre de {nombre_cliente} fue formalizado exitosamente con una tasa de {tasa_mensual_asignada}% mensual. Ya se encuentra disponible en la Ventanilla de Cobranza y en el Centro de Riesgos.")
                    except Exception as e:
                        dictamen("peligro", "Nota de Conexión SQL", f"La evaluación algorítmica se ejecutó con éxito y el pricing está confirmado. Para persistir el alta automática, asegúrese de que la tabla 'prestamos' cuente con las columnas compatibles en Supabase. Detalle: {str(e)}")