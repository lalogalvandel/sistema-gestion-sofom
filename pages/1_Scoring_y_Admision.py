# =============================================================================
# Copyright (c) 2026 Eduardo Galván del Rio. Todos los derechos reservados.
# 
# Este código fuente es propiedad exclusiva y confidencial. Queda estrictamente
# prohibida su reproducción, distribución, comercialización o modificación
# sin autorización expresa y por escrito del autor.
# =============================================================================

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
verificar_acceso("COBRANZA")
# -----------------------------------

aplicar_identidad_visual()

# --- FIRMA VISUAL (SIGNATURE) ---
st.markdown("""
<style>
    [data-testid="stMetricValue"], .stDataFrame {
        font-family: 'JetBrains Mono', 'Courier New', monospace !important;
        letter-spacing: -0.5px;
    }
</style>
""", unsafe_allow_html=True)

encabezado_modulo(
    titulo="Motor Actuarial y Originación KYC",
    subtitulo="Evaluación de riesgo, verificación PLD estricta e inscripción en el ecosistema relacional.",
    nombre_icono="escudo",
    insignia="ORIGINACIÓN INSTITUCIONAL"
)

usuario_actual = st.session_state.get("user_email", "Usuario No Identificado")
rol_actual = st.session_state.get("user_role", "COBRANZA")

# -----------------------------------------------------------------------------
# 1. MOTOR DE MACHINE LEARNING (A futuro se entrenará con BD Real)
# -----------------------------------------------------------------------------
@st.cache_resource
def inicializar_motor_scoring():
    np.random.seed(108)
    n_muestras = 1000
    
    ratio_cobertura = np.random.normal(1.8, 0.6, n_muestras).clip(0.2, 5.0)
    antiguedad = np.random.exponential(3.5, n_muestras).clip(0.1, 25.0)
    apalancamiento = np.random.normal(0.45, 0.25, n_muestras).clip(0.05, 2.0)
    mora_previa = np.random.choice([0, 1, 2, 3], size=n_muestras, p=[0.68, 0.18, 0.09, 0.05])
    
    log_odds = (-2.2 * ratio_cobertura) - (0.35 * antiguedad) + (2.8 * apalancamiento) + (1.4 * mora_previa) + 0.8
    probabilidades = 1.0 / (1.0 + np.exp(-log_odds))
    
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
# 2. BÓVEDA DIGITAL Y ASISTENTE KYC
# -----------------------------------------------------------------------------
titulo_seccion("documento", "ASISTENTE DE DECISIÓN SIC Y BÓVEDA KYC")

st.markdown(f"**Oficial de Crédito / Evaluador:** `{usuario_actual}`")

with st.expander("Matriz Institucional de Consulta SIC (Buró vs Círculo)"):
    st.markdown("""
    * **Perfil Bancarizado (Nómina, Tarjetas Clásicas):** Consulte **Buró de Crédito**.
    * **Perfil FinTech / Retail (Nu, Elektra, Coppel):** Consulte **Círculo de Crédito**.
    * **Economía Informal:** Solicite Últimos 3 Estados de Cuenta Bancarios.
    """)

col_doc1, col_doc2 = st.columns([1, 1.2])

with col_doc1:
    archivo_kyc = st.file_uploader("Adjuntar Expediente (PDF / ZIP con Documentación):", type=["pdf", "zip"])

with col_doc2:
    st.markdown("**Validación Jurídica (Art. 28 LRSIC):**")
    declaracion_legal = st.checkbox("El solicitante autoriza expresamente la consulta de su historial crediticio y declara el origen lícito de sus recursos (PLD).")

st.divider()

# -----------------------------------------------------------------------------
# 3. PARAMÉTRICOS FINANCIEROS Y ESTRUCTURA DE CRÉDITO
# -----------------------------------------------------------------------------
titulo_seccion("personas", "PERFIL FINANCIERO Y ESTRUCTURA DEL CRÉDITO")

with st.form("form_evaluacion_crediticia"):
    c_gen1, c_gen2 = st.columns(2)
    with c_gen1:
        nombre_cliente = st.text_input("Acreditado Titular (Nombre Completo):")
    with c_gen2:
        rfc_cliente = st.text_input("RFC con Homoclave (ID Único):").upper()
        
    st.markdown("---")
    c_cred1, c_cred2 = st.columns(2)
    with c_cred1:
        monto_solicitado = st.number_input("Capital Solicitado ($ MXN):", min_value=1000.0, value=50000.0, step=5000.0)
    with c_cred2:
        # UNIFICACIÓN DE NOMENCLATURA: Usamos Quincenas para que cruce perfecto con Amortización
        plazo_quincenas = st.selectbox("Plazo Requerido (Quincenas):", [6, 12, 18, 24, 36, 48], index=1)
        
    st.markdown("---")
    c_var1, c_var2, c_var3, c_var4 = st.columns(4)
    with c_var1: ingreso_mensual = st.number_input("Ingreso Neto Mensual ($):", min_value=0.0, value=35000.0)
    with c_var2: gastos_fijos = st.number_input("Obligaciones Mensuales ($):", min_value=0.0, value=15000.0)
    with c_var3: antiguedad_anios = st.number_input("Antigüedad (Años):", min_value=0.1, value=3.0)
    with c_var4: patrimonio_garantia = st.number_input("Patrimonio / Garantía ($):", min_value=1.0, value=100000.0)
        
    c_mora1, c_mora2 = st.columns([1, 2])
    with c_mora1:
        mora_buro = st.selectbox("Clave MOP en SIC:", [
            (0, "0. Al corriente (MOP 01)"),
            (1, "1. Atraso leve (MOP 02)"),
            (2, "2. Atraso moderado (MOP 03)"),
            (3, "3. Marca negativa (MOP 04+)"),
        ], format_func=lambda x: x[1])[0]
    with c_mora2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Nota: La clave MOP debe coincidir con el reporte adjunto en la bóveda KYC.")

    ejecutar_evaluacion = st.form_submit_button("Ejecutar Modelo de Scoring Actuarial", width='stretch')

# -----------------------------------------------------------------------------
# 4. DICTAMEN DE RIESGO
# -----------------------------------------------------------------------------
if ejecutar_evaluacion:
    if not archivo_kyc:
        st.error("BLOQUEO DE AUDITORÍA: Adjunte el expediente en la Bóveda KYC.")
    elif not declaracion_legal:
        st.error("BLOQUEO LEGAL: Valide la autorización LRSIC.")
    elif not nombre_cliente or len(rfc_cliente) < 10:
        st.warning("Ingrese un Nombre y RFC válidos.")
    else:
        # Cálculo de métricas
        cuota_mensual_estimada = (monto_solicitado / (plazo_quincenas / 2.0)) * 1.06
        ingreso_disponible = max(ingreso_mensual - gastos_fijos, 0.01)
        ratio_cobertura_calc = round(ingreso_disponible / cuota_mensual_estimada, 2)
        ratio_apalancamiento_calc = round(monto_solicitado / max(patrimonio_garantia, 1.0), 2)
        
        # Inferencia ML
        vector_cliente = pd.DataFrame({"ratio_cobertura": [ratio_cobertura_calc], "antiguedad": [antiguedad_anios], "apalancamiento": [ratio_apalancamiento_calc], "mora_previa": [mora_buro]})
        vector_escalado = escalador_features.transform(vector_cliente)
        prob_default = float(modelo_scoring.predict_proba(vector_escalado)[:, 1][0])
        
        score_crediticio = max(min(int(850 - (prob_default * 550)), 850), 300)
        
        # Pricing Risk-Adjusted
        costo_capital_anual, gasto_operativo_anual = 0.12, 0.04
        if score_crediticio >= 750: prima_riesgo_anual, calificacion_grado = 0.02, "Grado de Inversión Superior (AAA)"
        elif score_crediticio >= 650: prima_riesgo_anual, calificacion_grado = 0.04, "Grado de Inversión Estándar (AA)"
        elif score_crediticio >= 550: prima_riesgo_anual, calificacion_grado = 0.08, "Grado Especulativo Moderado (A)"
        else: prima_riesgo_anual, calificacion_grado = 0.15, "Alto Riesgo de Incumplimiento (B)"
            
        numerador_tasa = costo_capital_anual + gasto_operativo_anual + prima_riesgo_anual
        denominador_tasa = 1.0 - prob_default
        
        if denominador_tasa <= 0 or prob_default > 0.22:
            estatus_dictamen = "RECHAZADO"
            tasa_mensual_asignada = 0.0
        else:
            tasa_mensual_asignada = round(((numerador_tasa / denominador_tasa) * 100.0) / 12.0, 2)
            estatus_dictamen = "APROBADO PREFERENCIAL" if score_crediticio >= 700 else "APROBADO CONDICIONADO"

        st.session_state["dictamen_evaluado"] = {
            "nombre_cliente": nombre_cliente,
            "rfc_cliente": rfc_cliente,
            "ingreso_neto_mensual": ingreso_mensual,
            "monto_solicitado": monto_solicitado,
            "plazo_quincenas": plazo_quincenas,
            "score_crediticio": score_crediticio,
            "prob_default": prob_default,
            "ratio_cobertura_calc": ratio_cobertura_calc,
            "tasa_mensual_asignada": tasa_mensual_asignada,
            "estatus_dictamen": estatus_dictamen,
            "calificacion_grado": calificacion_grado
        }

if "dictamen_evaluado" in st.session_state:
    datos = st.session_state["dictamen_evaluado"]
    
    st.divider()
    titulo_seccion("estadisticas", "DICTAMEN TÉCNICO Y PRICING")
    
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("Score Crediticio", f"{datos['score_crediticio']} pts")
    with k2: st.metric("Probabilidad de Default (PD)", f"{datos['prob_default']*100:.2f}%")
    with k3: st.metric("Ratio Cobertura", f"{datos['ratio_cobertura_calc']}x")
    with k4: 
        if datos['estatus_dictamen'] == "RECHAZADO": st.metric("Tasa de Indiferencia", "N/A")
        else: st.metric("Tasa de Indiferencia Asignada", f"{datos['tasa_mensual_asignada']}% mes")

    st.markdown("<br>", unsafe_allow_html=True)
    
    if datos['estatus_dictamen'] == "RECHAZADO":
        dictamen("peligro", "SOLICITUD RECHAZADA POR RIESGO", "El perfil no supera los parámetros de viabilidad de la SOFOM.")
    else:
        dictamen("exito", f"SOLICITUD {datos['estatus_dictamen']}", "El perfil acredita solvencia. Tasa calculada exitosamente.")
        
        st.markdown("<br>", unsafe_allow_html=True)
        titulo_seccion("documento_check", "FORMALIZACIÓN Y CHECKLIST PLD")
        
        with st.form("form_alta_credito"):
            st.markdown("**Checklist de Integración Normativa (Artículo 115 LVIC):**")
            chk_ine = st.checkbox("Identificación Oficial Vigente del Titular cotejada y validada.")
            chk_dom = st.checkbox("Comprobante de Domicilio legal no mayor a 3 meses validado.")
            chk_ingreso = st.checkbox("Comprobante de Ingresos / Estados de Cuenta cotejados.")
            
            # Botón final alineado con las observaciones del Auditor (Inserción Limpia)
            btn_guardar_prestamo = st.form_submit_button("Turnar Expediente a Mesa de Aprobación", type="primary", width="stretch")
            
            if btn_guardar_prestamo:
                if not (chk_ine and chk_dom and chk_ingreso):
                    st.error("BLOQUEO PLD: El Oficial de Crédito debe validar físicamente la existencia de todos los documentos del checklist normativo.")
                else:
                    with st.spinner("Creando Identidad de Cliente e Inscribiendo Crédito (Transacción ACID)..."):
                        try:
                            rfc_target = str(datos['rfc_cliente']).strip()
                            # 1. INSERCIÓN O ACTUALIZACIÓN EN TABLA CLIENTES (La fuente única de verdad del usuario)
                            payload_cliente = {
                                "rfc": rfc_target,
                                "nombre_completo": str(datos['nombre_cliente']).strip(),
                                "ingreso_neto_mensual": float(datos['ingreso_neto_mensual']),
                                "puntaje_buro": int(datos['score_crediticio']),
                                "estatus_admision": "VERIFICADO_PLD"
                            }
                            # Upsert: Si el RFC ya existe, actualiza los datos. Si no, lo crea.
                            res_cliente = supabase.table("clientes").upsert(payload_cliente, on_conflict="rfc").execute()
                            
                            # Intentamos obtener el id_cliente (UUID real). Si el upsert no lo devuelve, lo buscamos.
                            id_cliente_real = None
                            if res_cliente.data:
                                id_cliente_real = res_cliente.data[0].get("id_cliente")
                            if not id_cliente_real:
                                res_busq = supabase.table("clientes").select("id_cliente").eq("rfc", rfc_target).execute()
                                id_cliente_real = res_busq.data[0]["id_cliente"] if res_busq.data else None
                                
                            if not id_cliente_real:
                                st.error("Error crítico: No se pudo enlazar o crear el expediente del cliente en la base de datos principal.")
                            else:
                                # 2. INSERCIÓN EN TABLA PRESTAMOS (Súper limpia, sin duplicados)
                                payload_prestamo = {
                                    "id_cliente": str(id_cliente_real), # <--- LLAVE FORÁNEA PURA
                                    "monto_principal": float(datos['monto_solicitado']),
                                    "tasa_interes_mensual": float(datos['tasa_mensual_asignada']),
                                    "plazo_quincenas": int(datos['plazo_quincenas']),
                                    "estatus": "APROBADO", # Nace aprobado (o PENDIENTE_APROBACION en flujos más estrictos)
                                    "fecha_desembolso": None # Aún no hay dinero entregado
                                }
                                
                                supabase.table("prestamos").insert(payload_prestamo).execute()
                                
                                st.success("Expediente de Identidad Creado y Crédito Autorizado por el Comité.")
                                st.info("Siguiente Paso: Transición al Módulo 2 (Amortización) para formalizar el calendario.")
                                del st.session_state["dictamen_evaluado"]
                                
                        except Exception as e_sql:
                            st.error(f"Fallo en transacción de Base de Datos: {str(e_sql)}")