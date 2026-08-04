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
import plotly.graph_objects as go
from datetime import datetime
from src.auth import verificar_acceso
from src.db import supabase
from src.theme import (
    aplicar_identidad_visual, encabezado_modulo, titulo_seccion,
    tarjeta_kpi, dictamen
)

st.set_page_config(page_title="Gestión de Riesgos | SOFOM", layout="wide")
verificar_acceso("AUDITOR")
aplicar_identidad_visual()

# --- EL RIESGO ESTÉTICO (SIGNATURE DESIGN) ---
st.markdown("""
<style>
    [data-testid="stMetricValue"], .stDataFrame {
        font-family: 'JetBrains Mono', 'Courier New', monospace !important;
        letter-spacing: -0.5px;
    }
    [data-testid="metric-container"] {
        border-radius: 2px !important;
        border-left: 4px solid #1e293b !important; 
    }
</style>
""", unsafe_allow_html=True)

encabezado_modulo(
    titulo="Inteligencia Actuarial y Riesgo Estocástico",
    subtitulo="Monitoreo algorítmico del IMOR, Value at Risk (VaR) y calibración de precios basados en métricas reales de la cartera viva.",
    nombre_icono="escudo",
    insignia="DIRECCIÓN Y AUDITORÍA"
)

# -----------------------------------------------------------------------------
# 1. MOTOR DE EXTRACCIÓN (DATOS REALES)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=15)
def obtener_cartera_de_riesgo():
    try:
        # Solo traemos los créditos que tienen dinero vivo en la calle
        res = supabase.table("prestamos").select("id_prestamo, cliente, rfc, monto_principal, estatus, proximo_vencimiento").in_("estatus", ["VIGENTE", "MORA", "ACTIVO"]).execute()
        data = res.data if res.data else []
        if not data: return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # Blindaje para asegurar que tratamos con números puros (Limpieza SQL)
        df["monto_principal"] = pd.to_numeric(df["monto_principal"], errors="coerce").fillna(0.0)
        df = df[df["monto_principal"] > 0.01]
        
        # CÁLCULO DE DÍAS DE ATRASO REALES (Adiós np.random)
        hoy = datetime.now().date()
        
        def calcular_dias_atraso(fecha_venc_str):
            if not fecha_venc_str: return 0
            try:
                fech_v = datetime.strptime(str(fecha_venc_str), "%Y-%m-%d").date()
                dias = (hoy - fech_v).days
                return max(dias, 0) # Si faltan días para pagar, el atraso es 0
            except:
                return 0
                
        df["dias_atraso"] = df["proximo_vencimiento"].apply(calcular_dias_atraso)
        
        def clasificar_bucket(dias):
            if dias <= 0: return "Al Corriente"
            elif dias <= 30: return "Atraso Leve (1-30d)"
            elif dias <= 60: return "Atraso Moderado (31-60d)"
            elif dias <= 90: return "Atraso Crítico (61-90d)"
            else: return "Cartera Vencida (>90d)"
            
        df["Bucket"] = df["dias_atraso"].apply(clasificar_bucket)
        return df
    except Exception as e:
        st.error(f"Error extrayendo matriz de riesgo: {str(e)}")
        return pd.DataFrame()

df_cartera = obtener_cartera_de_riesgo()

# -----------------------------------------------------------------------------
# 2. PANEL GERENCIAL DE SALUD
# -----------------------------------------------------------------------------
titulo_seccion("estadisticas", "SALUD DE CARTERA Y RESERVAS")

if df_cartera.empty:
    st.info("El motor de riesgo requiere datos reales de colocación. **Acuda al módulo de 'Originación', formalice un expediente y regrese** para visualizar el impacto estocástico.")
else:
    cartera_total = float(df_cartera["monto_principal"].sum())
    
    # Cartera Vencida (Exigible +90 días)
    vencida_df = df_cartera[df_cartera["dias_atraso"] > 90]
    cartera_vencida = float(vencida_df["monto_principal"].sum()) if not vencida_df.empty else 0.0
    imor = round((cartera_vencida / cartera_total) * 100, 2) if cartera_total > 0 else 0.0
    
    # Pérdida Esperada (Reserva Preventiva: NIIF 9 Simplificado)
    # 15% sobre cartera en mora temprana (>30 días) + 50% sobre cartera vencida (>90)
    vol_mora_temprana = float(df_cartera[(df_cartera["dias_atraso"] > 30) & (df_cartera["dias_atraso"] <= 90)]["monto_principal"].sum())
    reserva_recomendada = round((vol_mora_temprana * 0.15) + (cartera_vencida * 0.50), 2)
    
    k1, k2, k3, k4 = st.columns(4)
    with k1: tarjeta_kpi("Capital Expuesto", f"${cartera_total:,.2f}", "Total colocado en plaza")
    with k2: tarjeta_kpi("Cartera Vencida", f"${cartera_vencida:,.2f}", "Exigible judicial (>90d)")
    with k3: tarjeta_kpi("IMOR Global", f"{imor}%", "Índice de morosidad institucional")
    with k4: tarjeta_kpi("Reserva NIIF 9 (Ajustada)", f"${reserva_recomendada:,.2f}", "Pérdida esperada estimada")
    
    st.markdown("<br>", unsafe_allow_html=True)
    col_grafico, col_tabla = st.columns([1.3, 1])
    
    with col_grafico:
        st.markdown("**Concentración de Capital por Bucket**")
        resumen_buckets = df_cartera.groupby("Bucket")["monto_principal"].sum().reset_index()
        st.bar_chart(data=resumen_buckets, x="Bucket", y="monto_principal", width='stretch', color="#1e293b")
        
    with col_tabla:
        st.markdown("**Distribución de Riesgo**")
        resumen_tabla = df_cartera.groupby("Bucket").agg(Créditos=('monto_principal', 'count'), Volumen=('monto_principal', 'sum')).reset_index()
        resumen_tabla["Concentración"] = (resumen_tabla["Volumen"] / cartera_total).map("{:.1%}".format)
        
        # Formateamos el volumen visualmente
        resumen_tabla["Volumen"] = resumen_tabla["Volumen"].apply(lambda x: f"${x:,.2f}")
        st.dataframe(resumen_tabla, width='stretch', hide_index=True)

st.divider()

# -----------------------------------------------------------------------------
# 3. MODELOS ESTOCÁSTICOS
# -----------------------------------------------------------------------------
titulo_seccion("tendencia", "PROYECCIÓN ESTOCÁSTICA DE CAPITAL (VaR)")

if not df_cartera.empty and cartera_total > 0:
    c_markov, c_montecarlo = st.columns([1, 1.4])
    
    with c_markov:
        st.markdown("**Matriz de Transición (Cadenas de Markov Dinámicas)**")
        
        # CÁLCULO DINÁMICO DE PROBABILIDADES BASADO EN LA CARTERA REAL
        volumen_sano = float(df_cartera[df_cartera["dias_atraso"] <= 30]["monto_principal"].sum())
        volumen_mora = vol_mora_temprana
        volumen_default = cartera_vencida
        
        # Evitar divisiones por cero
        p_v_m = round((volumen_mora + volumen_default) / cartera_total, 3) if cartera_total > 0 else 0.12
        p_m_d = round(volumen_default / (volumen_mora + volumen_default), 3) if (volumen_mora + volumen_default) > 0 else 0.35
        p_v_v = round(1.0 - p_v_m, 3)
        
        st.caption("Probabilidades calibradas en tiempo real con datos de cartera (a 90 días).")
        st.markdown(f"- **Retención (Sano ➔ Sano):** {p_v_v*100:.1f}%\n- **Deterioro (Sano ➔ Mora):** {p_v_m*100:.1f}%\n- **Default (Mora ➔ Vencida):** {p_m_d*100:.1f}%")
        
        proyeccion_default = (volumen_sano * p_v_m * p_m_d) + (volumen_mora * p_m_d)
        st.metric(label="Pérdida Esperada (Drift a 90d)", value=f"${proyeccion_default:,.2f}")
    
    with c_montecarlo:
        st.markdown("**Simulación de Monte Carlo (12 Meses)**")
        
        # Alimentamos Montecarlo con el IMOR real histórico
        volatilidad_historica = max(0.06, imor / 100.0)
        crecimiento_esperado = 0.04 # 4% de crecimiento de cartera mensual objetivo
        
        np.random.seed(42)
        trayectorias, meses = 1000, 12
        simulaciones = np.zeros((meses + 1, trayectorias))
        simulaciones[0] = cartera_total
        
        for t in range(1, meses + 1):
            simulaciones[t] = simulaciones[t-1] * (1 + np.random.normal(loc=crecimiento_esperado, scale=volatilidad_historica, size=trayectorias))
            
        fig = go.Figure()
        for i in range(50):
            fig.add_trace(go.Scatter(y=simulaciones[:, i], mode='lines', line=dict(width=0.5, color='rgba(100, 116, 139, 0.15)'), showlegend=False))
        fig.add_trace(go.Scatter(y=np.mean(simulaciones, axis=1), mode='lines', line=dict(width=2, color='#0f172a'), name='Media Esperada'))
        fig.add_trace(go.Scatter(y=np.percentile(simulaciones, 5, axis=1), mode='lines', line=dict(width=2, color='#b91c1c', dash='dot'), name='Límite VaR (95%)'))
        
        fig.update_layout(height=260, margin=dict(l=0, r=0, t=0, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
        
        c_var1, c_var2 = st.columns(2)
        with c_var1: st.metric(label="Flujo Esperado (Mes 12)", value=f"${np.mean(simulaciones[-1]):,.2f}")
        with c_var2: st.metric(label="Value at Risk (VaR 95%)", value=f"${np.percentile(simulaciones[-1], 5):,.2f}")

st.divider()

# -----------------------------------------------------------------------------
# 4. CALCULADORA ACTUARIAL
# -----------------------------------------------------------------------------
titulo_seccion("herramienta", "CALIBRACIÓN DE PRECIOS AJUSTADOS POR RIESGO")

st.markdown("Determine la Tasa de Indiferencia Financiera para asegurar que el interés cobrado absorba el costo de capital, gasto operativo y riesgo estadístico.")

col_calc1, col_calc2 = st.columns([1, 1.2])

with col_calc1:
    with st.form("form_tasa_indiferencia"):
        costo_capital = st.number_input("Costo de Capital (% Anual):", value=12.0) / 100.0
        gasto_operativo = st.number_input("Gasto Operativo (% sobre colocación):", value=4.0) / 100.0
        prima_riesgo = st.number_input("Prima de Riesgo Cliente (%):", value=3.0) / 100.0
        prob_default = st.slider("Probabilidad de Default (Pd %):", 0.0, 25.0, 5.0) / 100.0
        
        calcular_tasa = st.form_submit_button("Ejecutar Modelo Actuarial", width='stretch')

with col_calc2:
    if calcular_tasa:
        denominador = 1.0 - prob_default
        if denominador <= 0:
            dictamen("peligro", "Inviabilidad Matemática", "Certeza de ruina técnica. Rechace la solicitud.")
        else:
            tasa_anual_optima = ((costo_capital + gasto_operativo + prima_riesgo) / denominador) * 100.0
            
            c_res1, c_res2 = st.columns(2)
            with c_res1: st.metric(label="Tasa Mínima Anual", value=f"{tasa_anual_optima:.2f}%")
            with c_res2: st.metric(label="Tasa Óptima Mensual", value=f"{(tasa_anual_optima / 12.0):.2f}%")
            
            st.info("Esta es la tasa piso. Originar por debajo de este umbral destruirá capital del fondo.")
    else:
        st.markdown("<br>", unsafe_allow_html=True)
        st.info("Ajuste los parámetros a la izquierda y ejecute el modelo para obtener la tasa piso.")

st.divider()

# -----------------------------------------------------------------------------
# 5. BITÁCORA LEGAL (CONEXIÓN BD ACTIVA)
# -----------------------------------------------------------------------------
titulo_seccion("documento", "REGISTRO CONTENCIOSO Y EXTRAJUDICIAL")

usuario_actual = st.session_state.get("user_email", "Usuario No Identificado")
rol_actual = st.session_state.get("user_role", "AUDITOR")
es_auditor_solo_lectura = (rol_actual == "AUDITOR")

col_bitacora, col_historial = st.columns([1, 1.5])

with col_bitacora:
    if es_auditor_solo_lectura:
        st.warning("Perfil de Solo Lectura. El registro de intervenciones está inhabilitado para auditores.")
    
    with st.form("form_bitacora_cobranza"):
        # Le pasamos las opciones de los créditos reales que vimos arriba
        opciones_id_cobranza = df_cartera["id_prestamo"].tolist() if not df_cartera.empty else ["Sin créditos disponibles"]
        
        id_credito_ref = st.selectbox("Expediente (ID Préstamo):", opciones_id_cobranza, disabled=es_auditor_solo_lectura)
        tipo_accion = st.selectbox("Clasificación de la Acción:", [
            "Acuerdo Telefónico", "Notificación Formal de Vencimiento", "Carta Convenio", "Turno a Despacho Legal"
        ], disabled=es_auditor_solo_lectura)
        
        fecha_promesa = st.date_input("Fecha de Cumplimiento:", disabled=es_auditor_solo_lectura)
        notas_gestion = st.text_area("Extracto de la Gestión:", disabled=es_auditor_solo_lectura)
        
        guardar_bitacora = st.form_submit_button("Registrar Intervención en Bitácora", width='stretch', disabled=es_auditor_solo_lectura)
        
        if guardar_bitacora and not es_auditor_solo_lectura:
            if id_credito_ref == "Sin créditos disponibles" or len(notas_gestion) < 5:
                st.error("Seleccione un expediente válido y redacte al menos 5 caracteres en la nota.")
            else:
                with st.spinner("Registrando pista de auditoría inmutable..."):
                    try:
                        payload_bitacora = {
                            "id_credito_ref": str(id_credito_ref),
                            "tipo_accion": str(tipo_accion),
                            "fecha_compromiso": fecha_promesa.strftime("%Y-%m-%d"),
                            "notas": str(notas_gestion),
                            "usuario_gestor": usuario_actual
                        }
                        supabase.table("bitacora_cobranza").insert(payload_bitacora).execute()
                        st.success("Intervención legal resguardada en el servidor.")
                        st.rerun() # Refresca para que aparezca en la tabla de al lado
                    except Exception as e_bit:
                        st.error(f"Fallo de conexión SQL: {str(e_bit)}")

with col_historial:
    st.markdown("**Pista de Auditoría Reciente**")
    try:
        res_bit = supabase.table("bitacora_cobranza").select("fecha_registro, id_credito_ref, tipo_accion").order("fecha_registro", desc=True).limit(5).execute()
        if res_bit.data:
            df_bit_presentacion = pd.DataFrame(res_bit.data)
            df_bit_presentacion.columns = ["Fecha UTC", "ID Expediente", "Intervención"]
            # Recortamos el ID visualmente para que quepa bien en la tabla
            df_bit_presentacion["ID Expediente"] = df_bit_presentacion["ID Expediente"].apply(lambda x: str(x)[:8] + "...")
            
            st.dataframe(df_bit_presentacion, width='stretch', hide_index=True)
        else:
            st.info("La pista de auditoría está vacía. Registre una intervención a la izquierda para iniciar el historial.")
    except Exception as e:
        st.info(f"Conecte el servidor para visualizar el historial legal.")