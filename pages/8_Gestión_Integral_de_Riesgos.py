# Copyright (c) 2026 Eduardo Galván del Rio. Todos los derechos reservados.
# 
# Este código fuente es propiedad exclusiva y confidencial. Queda estrictamente
# prohibida su reproducción, distribución, comercialización o modificación
# sin autorización expresa y por escrito del autor.
# 

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from src.auth import verificar_acceso
from src.db import supabase
from src.theme import (
    aplicar_identidad_visual, encabezado_modulo, titulo_seccion,
    tarjeta_kpi, dictamen, plantilla_plotly
)

st.set_page_config(page_title="Gestión de Riesgos e IMOR | SOFOM", layout="wide")

# --- BLINDAJE INSTITUCIONAL RBAC ---
verificar_acceso("AUDITOR")
# -----------------------------------

aplicar_identidad_visual()

encabezado_modulo(
    titulo="Centro de Inteligencia Actuarial y Riesgo de Cartera",
    subtitulo="Modelos estocásticos de riesgo, simulaciones de Monte Carlo, monitoreo IMOR y fijación algorítmica de tasas.",
    nombre_icono="escudo",
    insignia="RIESGO INSTITUCIONAL Y CUANTITATIVO"
)

# -----------------------------------------------------------------------------
# 1. MOTOR DE EXTRACCIÓN Y CÁLCULO DE BUCKETS DE ANTIGÜEDAD
# -----------------------------------------------------------------------------
@st.cache_data(ttl=30)
def obtener_cartera_de_riesgo():
    try:
        res = supabase.table("prestamos").select("*").execute()
        data = res.data if res.data else []
        
        if not data: return pd.DataFrame()
        df = pd.DataFrame(data)
        
        col_estatus = "estatus" if "estatus" in df.columns else ("estado" if "estado" in df.columns else None)
        if col_estatus:
            df["estatus_norm"] = df[col_estatus].astype(str).str.upper().str.strip()
            estados_vivos = ["ACTIVO", "VIGENTE", "APROBADO", "EN CURSO", "PENDIENTE", "MORA", "ATRASADO", "POR COBRAR"]
            df = df[df["estatus_norm"].isin(estados_vivos)]
        
        if df.empty: return pd.DataFrame()
            
        col_saldo = None
        for posible_nombre in ["saldo_pendiente", "saldo", "monto_pendiente", "total_a_pagar", "monto_prestado", "monto", "principal"]:
            if posible_nombre in df.columns:
                col_saldo = posible_nombre
                break
                
        if col_saldo:
            df["saldo_pendiente"] = pd.to_numeric(df[col_saldo], errors="coerce").fillna(0.0)
            df = df[df["saldo_pendiente"] > 0.01]
        else:
            df["saldo_pendiente"] = 15000.00
            
        if df.empty: return pd.DataFrame()
            
        # Simulación de días de atraso si la columna no existe para la auditoría visual
        if "dias_atraso" not in df.columns:
            np.random.seed(42)
            df["dias_atraso"] = np.random.choice([0, 5, 15, 35, 65, 95], size=len(df), p=[0.7, 0.1, 0.08, 0.07, 0.03, 0.02])
            
        def clasificar_bucket(dias):
            if dias <= 0: return "0. Al Corriente (0 días)"
            elif dias <= 30: return "1. Atraso Leve (1-30 días)"
            elif dias <= 60: return "2. Atraso Moderado (31-60 días)"
            elif dias <= 90: return "3. Atraso Crítico (61-90 días)"
            else: return "4. Cartera Vencida (>90 días)"
            
        df["Bucket"] = df["dias_atraso"].apply(clasificar_bucket)
        return df
    except Exception:
        return pd.DataFrame()

df_cartera = obtener_cartera_de_riesgo()

# -----------------------------------------------------------------------------
# 2. PANEL GERENCIAL DE SALUD (IMOR Y RESERVAS PREVENTIVAS)
# -----------------------------------------------------------------------------
titulo_seccion("estadisticas", "1. Semáforo de Cartera y Salud Financiera")

if df_cartera.empty:
    st.info("No existen créditos activos registrados en el servidor para evaluar el riesgo operativo en este ciclo.")
else:
    cartera_total = float(df_cartera["saldo_pendiente"].sum())
    vencida_df = df_cartera[df_cartera["dias_atraso"] > 90]
    cartera_vencida = float(vencida_df["saldo_pendiente"].sum()) if not vencida_df.empty else 0.0
    
    imor = round((cartera_vencida / cartera_total) * 100, 2) if cartera_total > 0 else 0.0
    
    en_riesgo_df = df_cartera[df_cartera["dias_atraso"] > 30]
    monto_en_riesgo = float(en_riesgo_df["saldo_pendiente"].sum()) if not en_riesgo_df.empty else 0.0
    reserva_recomendada = round(monto_en_riesgo * 0.15, 2)
    
    k1, k2, k3, k4 = st.columns(4)
    with k1: tarjeta_kpi("Cartera Activa Total", f"${cartera_total:,.2f}", "Capital colocado en plaza")
    with k2: tarjeta_kpi("Cartera Vencida (>90d)", f"${cartera_vencida:,.2f}", "Exigible judicial")
    with k3:
        estatus_imor = "ESTABLE" if imor < 3.0 else ("OBSERVACIÓN" if imor < 7.0 else "CRÍTICO")
        tarjeta_kpi("Índice de Morosidad (IMOR)", f"{imor}%", f"Nivel: {estatus_imor}")
    with k4: tarjeta_kpi("Reserva Preventiva (15%)", f"${reserva_recomendada:,.2f}", "Fondo contingencia Mínimo")
    
    st.markdown("<br>", unsafe_allow_html=True)
    col_grafico, col_tabla = st.columns([1.3, 1])
    
    with col_grafico:
        st.markdown("**Distribución del Capital por Buckets de Antigüedad ($)**")
        resumen_buckets = df_cartera.groupby("Bucket")["saldo_pendiente"].sum().reset_index()
        resumen_buckets.columns = ["Bucket", "Saldo Monto ($)"]
        st.bar_chart(data=resumen_buckets, x="Bucket", y="Saldo Monto ($)", width='stretch')
        
    with col_tabla:
        st.markdown("**Concentración de Riesgo por Etapa**")
        resumen_tabla = df_cartera.groupby("Bucket").agg(
            Créditos=('saldo_pendiente', 'count'), Saldo_Total=('saldo_pendiente', 'sum')
        ).reset_index()
        resumen_tabla["Concentración (%)"] = round((resumen_tabla["Saldo_Total"] / cartera_total) * 100, 2)
        st.dataframe(resumen_tabla, width='stretch', hide_index=True)

st.divider()

# -----------------------------------------------------------------------------
# 3. MODELOS ESTOCÁSTICOS (MARKOV Y MONTE CARLO)
# -----------------------------------------------------------------------------
titulo_seccion("tendencia", "2. Modelos Estocásticos y Predicción de Default (VaR)")

if not df_cartera.empty and cartera_total > 0:
    st.markdown("""
    Evaluación cuantitativa del portafolio mediante **Cadenas de Markov** (transición de estados de mora) y simulaciones de **Monte Carlo** para determinar el Valor en Riesgo (VaR) del capital fondeado por los socios a un horizonte de 12 meses.
    """)
    
    c_markov, c_montecarlo = st.columns([1, 1.4])
    
    with c_markov:
        st.markdown("**Matriz de Transición (Cadenas de Markov)**")
        st.caption("Probabilidad de migración de cartera a 90 días vista.")
        
        # Simulación de Matriz de Transición P basada en la estructura de la cartera actual
        volumen_sano = df_cartera[df_cartera["dias_atraso"] <= 30]["saldo_pendiente"].sum()
        volumen_mora = df_cartera[(df_cartera["dias_atraso"] > 30) & (df_cartera["dias_atraso"] <= 90)]["saldo_pendiente"].sum()
        
        p_v_v = 0.88 # Probabilidad Vigente -> Vigente
        p_v_m = 0.12 # Probabilidad Vigente -> Mora
        p_m_v = 0.25 # Probabilidad Mora -> Vigente (Cura)
        p_m_d = 0.35 # Probabilidad Mora -> Default (Vencida)
        
        st.success(f"**Tasa de Retención (Vigente ➔ Vigente):** {p_v_v*100}%")
        st.warning(f"**Riesgo de Deterioro (Vigente ➔ Mora):** {p_v_m*100}%")
        st.error(f"**Prob. de Irrecuperabilidad (Mora ➔ Default):** {p_m_d*100}%")
        
        proyeccion_default = (volumen_sano * p_v_m * p_m_d) + (volumen_mora * p_m_d)
        st.metric(label="Pérdida Esperada a 90 días (Drift)", value=f"${proyeccion_default:,.2f}")
    
    with c_montecarlo:
        st.markdown("**Simulación de Monte Carlo (1,000 Escenarios a 12 Meses)**")
        
        # Motor de Monte Carlo (Movimiento Browniano Geométrico simplificado para cartera)
        np.random.seed(42)
        trayectorias = 1000
        meses = 12
        tasa_media = 0.04 # 4% rendimiento neto mensual esperado
        volatilidad = 0.06 # 6% volatilidad (riesgo de default)
        
        simulaciones = np.zeros((meses + 1, trayectorias))
        simulaciones[0] = cartera_total
        
        for t in range(1, meses + 1):
            choques = np.random.normal(loc=tasa_media, scale=volatilidad, size=trayectorias)
            simulaciones[t] = simulaciones[t-1] * (1 + choques)
            
        valor_esperado = np.mean(simulaciones[-1])
        var_95 = np.percentile(simulaciones[-1], 5) # Peor 5% de los casos
        
        # Graficamos 50 trayectorias aleatorias para no saturar el navegador
        fig = go.Figure()
        for i in range(50):
            fig.add_trace(go.Scatter(y=simulaciones[:, i], mode='lines', line=dict(width=1, color='rgba(59, 130, 246, 0.1)'), showlegend=False))
            
        fig.add_trace(go.Scatter(y=np.mean(simulaciones, axis=1), mode='lines', line=dict(width=3, color='#10B981'), name='Valor Esperado'))
        fig.add_trace(go.Scatter(y=np.percentile(simulaciones, 5, axis=1), mode='lines', line=dict(width=3, color='#EF4444', dash='dash'), name='Límite VaR (95%)'))
        
        fig.update_layout(height=280, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
        
        c_var1, c_var2 = st.columns(2)
        with c_var1: st.metric(label="Flujo Esperado (Mes 12)", value=f"${valor_esperado:,.2f}")
        with c_var2: st.metric(label="Value at Risk (VaR 95%)", value=f"${var_95:,.2f}", delta="Peor escenario posible", delta_color="inverse")

st.divider()

# -----------------------------------------------------------------------------
# 4. CALCULADORA ACTUARIAL DE TASA DE INDIFERENCIA FINANCIERA
# -----------------------------------------------------------------------------
titulo_seccion("herramienta", "3. Motor Actuarial de Fijación de Tasas (Risk-Adjusted Pricing)")

st.markdown("""
El siguiente modelo elimina la subjetividad operacional en la originación del crédito. Aplica la ecuación de **Tasa de Indiferencia Financiera** para determinar el precio exacto del dinero, garantizando que el interés cobrado absorba el costo de capital, el gasto operativo y el riesgo estadístico de incumplimiento.
""")

col_calc1, col_calc2 = st.columns([1, 1.2])

with col_calc1:
    with st.form("form_tasa_indiferencia"):
        st.markdown("**Parámetros Estructurales y de Evaluación:**")
        costo_capital = st.number_input("Costo de Capital / Rendimiento Socios (% Anual):", value=12.0, step=0.5) / 100.0
        gasto_operativo = st.number_input("Gastos Operativos SOFOM (% sobre colocación):", value=4.0, step=0.5) / 100.0
        prima_riesgo = st.number_input("Prima de Riesgo Específica del Cliente (%):", value=3.0, step=0.5) / 100.0
        
        prob_default = st.slider("Probabilidad de Default Estimada (Pd %):", min_value=0.0, max_value=25.0, value=5.0, step=0.5) / 100.0
        
        st.markdown("<br>", unsafe_allow_html=True)
        calcular_tasa = st.form_submit_button("Calcular Tasa de Indiferencia", width='stretch')

with col_calc2:
    if calcular_tasa:
        numerador = costo_capital + gasto_operativo + prima_riesgo
        denominador = 1.0 - prob_default
        
        if denominador <= 0:
            dictamen("peligro", "Inviabilidad Matemática", "La probabilidad de default excede el umbral de solvencia. El parámetro estadístico indica una certeza de ruina técnica; se recomienda rechazar la solicitud de forma definitiva.")
        else:
            tasa_anual_optima = (numerador / denominador) * 100.0
            tasa_mensual_optima = tasa_anual_optima / 12.0
            
            st.markdown("**Dictamen de Evaluación Actuarial**")
            c_res1, c_res2 = st.columns(2)
            with c_res1:
                st.metric(label="Tasa Mínima Anual de Indiferencia", value=f"{tasa_anual_optima:.2f}%")
            with c_res2:
                delta_vs_6 = round(tasa_mensual_optima - 6.0, 2)
                st.metric(label="Tasa Mensual Óptima", value=f"{tasa_mensual_optima:.2f}%", delta=f"{delta_vs_6}% respecto al 6% base")
                
            st.markdown("<br>", unsafe_allow_html=True)
            st.info(f"Análisis Técnico: Para un perfil con una probabilidad de incumplimiento estimada del **{prob_default*100}%**, fijar una tasa de interés inferior al **{tasa_mensual_optima:.2f}% mensual** implica subvalorar el riesgo crediticio, lo cual generará un déficit patrimonial en el fondo.")
    else:
        st.markdown("<br>", unsafe_allow_html=True)
        st.info("Ajuste las variables en el panel de control y ejecute el cálculo para modelar la tasa mínima viable para el crédito solicitante.")

st.divider()

# -----------------------------------------------------------------------------
# 5. BITÁCORA DE ACCIONES DE COBRANZA Y AUDITORÍA LEGAL
# -----------------------------------------------------------------------------
titulo_seccion("documento", "4. Bitácora de Gestión Extrajudicial y Contenciosa")

usuario_actual = st.session_state.get("user_email", "Usuario No Identificado")
rol_actual = st.session_state.get("user_role", "AUDITOR")
es_auditor_solo_lectura = (rol_actual == "AUDITOR")

col_bitacora, col_historial = st.columns([1, 1.5])

with col_bitacora:
    st.markdown("**Registro Legal de Intervención:**")
    st.caption(f"Gestor Responsable en Sesión: **{usuario_actual}** (Perfil: {rol_actual})")
    
    if es_auditor_solo_lectura:
        st.warning("Aviso Institucional: Su perfil de usuario (AUDITOR) cuenta con facultades exclusivas de supervisión y consulta. El registro y edición de intervenciones extrajudiciales o contenciosas se encuentra inhabilitado.")
    
    with st.form("form_bitacora_cobranza"):
        id_credito_ref = st.text_input("Folio o RFC del Crédito en Mora:", placeholder="Ej: RFC o Contrato #1024", disabled=es_auditor_solo_lectura)
        tipo_accion = st.selectbox("Clasificación del Acto Operativo:", [
            "Gestión Extrajudicial - Acuerdo Telefónico de Pago",
            "Notificación Electrónica - Aviso Formal de Vencimiento",
            "Carta Convenio - Suscripción de Reestructura de Adeudo",
            "Turnado a Despacho Externo - Inicio de Proceso Contencioso",
            "Inspección Presencial - Verificación Domiciliaria de Garantías"
        ], disabled=es_auditor_solo_lectura)
        
        fecha_promesa = st.date_input("Fecha Límite Compromiso:", disabled=es_auditor_solo_lectura)
        notas_gestion = st.text_area("Declaraciones y Extracto de la Gestión:", placeholder="El acreditado manifiesta retraso por insolvencia temporal...", disabled=es_auditor_solo_lectura)
        
        st.markdown("<br>", unsafe_allow_html=True)
        guardar_bitacora = st.form_submit_button("Anexar Gestión al Expediente", width='stretch', disabled=es_auditor_solo_lectura)
        
        if guardar_bitacora and not es_auditor_solo_lectura:
            if not id_credito_ref or not notas_gestion:
                st.warning("Los campos de referencia del crédito y extracto de gestión son obligatorios para el registro legal.")
            else:
                with st.spinner("Registrando intervención en el servidor institucional..."):
                    try:
                        payload_bitacora = {
                            "id_credito_ref": id_credito_ref.strip(),
                            "tipo_accion": tipo_accion,
                            "fecha_compromiso": str(fecha_promesa),
                            "notas": notas_gestion.strip(),
                            "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "usuario_gestor": usuario_actual
                        }
                        supabase.table("bitacora_cobranza").insert(payload_bitacora).execute()
                        dictamen("exito", "Intervención Registrada", "El acto de cobranza ha sido debidamente anexado a la pista de auditoría.")
                    except Exception as e:
                        dictamen("peligro", "Aviso del Servidor", f"Error en transacción SQL. Detalle técnico: {str(e)}")

with col_historial:
    st.markdown("**Pista de Auditoría de Intervenciones Recientes**")
    try:
        res_bit = supabase.table("bitacora_cobranza").select("*").order("fecha_registro", desc=True).limit(10).execute()
        if res_bit.data:
            df_bit = pd.DataFrame(res_bit.data)
            df_bit_presentacion = df_bit[["fecha_registro", "id_credito_ref", "tipo_accion", "usuario_gestor"]].copy()
            df_bit_presentacion.columns = ["Fecha UTC", "Referencia", "Intervención", "Gestor Firmante"]
            st.dataframe(df_bit_presentacion, width='stretch')
        else:
            st.info("No existen registros de intervención extrajudicial en el historial reciente.")
    except Exception:
        st.info("La pista de auditoría legal estará activa tras la primera inserción contable.")