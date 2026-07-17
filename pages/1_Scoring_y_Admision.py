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

encabezado_modulo(
    titulo="Motor Actuarial de Admisión y Credit Scoring",
    subtitulo="Evaluación algorítmica de riesgo crediticio, verificación legal KYC/PLD, fijación de Tasa de Indiferencia y formalización de colocación.",
    nombre_icono="escudo",
    insignia="ORIGINACIÓN INSTITUCIONAL"
)

usuario_actual = st.session_state.get("user_email", "Usuario No Identificado")
rol_actual = st.session_state.get("user_role", "COBRANZA")

# -----------------------------------------------------------------------------
# 1. MOTOR DE MACHINE LEARNING: REGRESIÓN LOGÍSTICA CALIBRADA
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
# 2. BÓVEDA DIGITAL, ASISTENTE DE DECISIÓN SIC Y CONSENTIMIENTO
# -----------------------------------------------------------------------------
titulo_seccion("documento", "1. Bóveda Digital, Asistente de Decisión y Consentimiento Legal")

st.markdown(f"**Funcionario Evaluador en Sesión:** `{usuario_actual}` ({rol_actual})")

# -- ASISTENTE INTERACTIVO DE DECISIÓN SIC --
st.markdown("**Matriz de Decisión Institucional: ¿Qué documento solicitar al cliente?**")
perfil_cliente = st.selectbox(
    "Seleccione el perfil financiero o laboral principal del solicitante:",
    [
        "A) Asalariado formal, profesionista o empresa con nómina en Bancos Tradicionales (BBVA, Banorte, Banamex, Santander, etc.)",
        "B) Comerciante, trabajador independiente, o usuario de FinTechs (Nu, Mercado Pago), Tiendas Retail (Coppel, Elektra) y Microcréditos",
        "C) Perfil mixto, economía informal o sin historial bancario identificable"
    ]
)

if perfil_cliente.startswith("A)"):
    st.info("**Instrucción Institucional:** El perfil bancario tradicional concentra su historial en **BURÓ DE CRÉDITO**. Solicite al cliente que descargue su Reporte de Crédito Especial gratuito en el siguiente enlace oficial: [www.burodecredito.com.mx](https://www.burodecredito.com.mx)")
elif perfil_cliente.startswith("B)"):
    st.info("**Instrucción Institucional:** El ecosistema FinTech, comercial y microfinanciero reporta prioritariamente a **CÍRCULO DE CRÉDITO**. Solicite al cliente su reporte gratuito en el siguiente enlace oficial: [www.circulodecredito.com.mx](https://www.circulodecredito.com.mx)")
else:
    st.info("**Instrucción Institucional:** Para perfiles de la economía informal o sin historial bancario, **prescinda de la consulta crediticia** y solicite estrictamente los **Últimos 3 Estados de Cuenta Bancarios (PDF)** para evaluar liquidez real y flujo de caja.")

# -- GUÍA DE LECTURA RÁPIDA (ACORDEÓN DESPLEGABLE) --
with st.expander("Ayuda Operativa: Guía de Lectura Rápida de PDF (Traducción de Códigos MOP)"):
    st.markdown("""
    Al abrir el documento PDF del cliente, localice la sección de **Historial de Pagos** y busque la clave de comportamiento (**MOP** o semáforo). Utilice la siguiente tabla de conversión para llenar el formulario inferior:
    
    * **MOP 01 (Cuenta al corriente / Sin atrasos):** Asigne el valor **0** en el modelo.
    * **MOP 02 (Atraso de 1 a 29 días):** Asigne el valor **1 (Atraso leve)** en el modelo.
    * **MOP 03 (Atraso de 30 a 59 días):** Asigne el valor **2 (Atraso moderado)** en el modelo.
    * **MOP 04, 05, 99 o Cuenta en Cobranza Judicial:** Asigne el valor **3 (Atraso severo / marca negativa)** en el modelo.
    * *Si evalúa con Estados de Cuenta Bancarios y no hay sobregiros ni rebotes:* Asigne el valor **0**.
    """)

st.markdown("---")

col_doc1, col_doc2 = st.columns([1, 1.2])

with col_doc1:
    st.markdown("**Carga de Expediente Digital (PDF obligatorio):**")
    archivo_kyc = st.file_uploader("Adjuntar Reporte Crediticio o Estados de Cuenta (PDF):", type=["pdf"])

with col_doc2:
    st.markdown("**Validación Jurídica de Consentimiento (Innegociable):**")
    declaracion_legal = st.checkbox(
        "**Declaración Legal de Consentimiento y Veracidad (Art. 28 LRSIC y Disposiciones PLD):**\n"
        "Bajo protesta de decir verdad, el solicitante declara que el documento digital adjunto fue obtenido por su propia cuenta de manera legítima y lo otorga voluntariamente a la SOFOM para el análisis y evaluación de su solvencia crediticia. Asimismo, autoriza expresamente a la entidad para realizar consultas y reportes periódicos a las Sociedades de Información Crediticia durante la vigencia de la relación comercial."
    )

st.divider()

# -----------------------------------------------------------------------------
# 3. CAPTURA DE PARAMÉTRICOS Y EVALUACIÓN FINANCIERA
# -----------------------------------------------------------------------------
titulo_seccion("personas", "2. Expediente Paramétrico y Perfil Financiero")

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
        mora_buro = st.selectbox("Clasificación de Historial en Buró de Crédito (Acreditado en PDF):", [
            (0, "0. Sin atrasos reportados en historial (0 días - MOP 01)"),
            (1, "1. Atraso leve histórico (1 a 30 días - MOP 02)"),
            (2, "2. Atraso moderado histórico (31 a 60 días - MOP 03)"),
            (3, "3. Atraso severo o marca negativa (> 60 días - MOP 04+)"),
        ], format_func=lambda x: x[1])[0]
    with c_mora2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Nota de Auditoría: El parámetro seleccionado en esta casilla debe coincidir de forma estricta con la clave MOP o comportamiento reflejado en el documento PDF adjuntado en la Sección 1.")

    st.markdown("<br>", unsafe_allow_html=True)
    ejecutar_evaluacion = st.form_submit_button("Ejecutar Motor de Inteligencia y Calcular Tasa", use_container_width=True)

# -----------------------------------------------------------------------------
# 4. PROCESAMIENTO ALGORÍTMICO Y DICTAMEN DE RIESGO
# -----------------------------------------------------------------------------
if ejecutar_evaluacion:
    if not archivo_kyc:
        st.error("BLOQUEO DE AUDITORÍA: No se puede ejecutar el modelo de scoring si no se ha adjuntado el expediente digital (PDF) en la Bóveda de Consentimiento.")
    elif not declaracion_legal:
        st.error("BLOQUEO LEGAL: Es indispensable validar la casilla de Declaración Legal de Consentimiento (Art. 28 LRSIC) para procesar la evaluación crediticia.")
    elif not nombre_cliente or len(rfc_cliente) < 10:
        st.warning("Debe ingresar la razón social completa y un RFC válido con homoclave para formalizar la evaluación.")
    else:
        cuota_mensual_estimada = (monto_solicitado / plazo_meses) * 1.06
        ingreso_disponible = max(ingreso_mensual - gastos_fijos, 0.01)
        ratio_cobertura_calc = round(ingreso_disponible / cuota_mensual_estimada, 2)
        ratio_apalancamiento_calc = round(monto_solicitado / max(patrimonio_garantia, 1.0), 2)
        
        vector_cliente = pd.DataFrame({
            "ratio_cobertura": [ratio_cobertura_calc],
            "antiguedad": [antiguedad_anios],
            "apalancamiento": [ratio_apalancamiento_calc],
            "mora_previa": [mora_buro]
        })
        
        vector_escalado = escalador_features.transform(vector_cliente)
        
        prob_default = float(modelo_scoring.predict_proba(vector_escalado)[:, 1][0])
        
        score_crediticio = int(850 - (prob_default * 550))
        score_crediticio = max(min(score_crediticio, 850), 300)
        
        costo_capital_anual = 0.12
        gasto_operativo_anual = 0.04
        
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
        titulo_seccion("estadisticas", "3. Dictamen del Comité Algorítmico y Pricing")
        
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            tarjeta_kpi("Score Crediticio", f"{score_crediticio} pts", calificacion_grado)
        with k2:
            nivel_pd = "BAJO RIESGO" if prob_default < 0.06 else ("MODERADO" if prob_default < 0.12 else "ALTO RIESGO")
            tarjeta_kpi("Probabilidad de Default (Pd)", f"{prob_default*100:.2f}%", f"Nivel: {nivel_pd}")
        with k3:
            tarjeta_kpi("Ratio Cobertura Deuda", f"{ratio_cobertura_calc}x", "Mínimo exigido: 1.20x")
        with k4:
            if estatus_dictamen == "RECHAZADO":
                tarjeta_kpi("Tasa Mensual Sugerida", "N/A", "Operación Inviable")
            else:
                tarjeta_kpi("Tasa de Indiferencia", f"{tasa_mensual_asignada}% mensual", f"{tasa_anual_asignada}% anualizada")

        st.markdown("<br>", unsafe_allow_html=True)
        
        if estatus_dictamen == "RECHAZADO":
            dictamen("peligro", "Dictamen: SOLICITUD RECHAZADA POR RIESGO ACTUARIAL", 
                     f"El modelo algorítmico determina una Probabilidad de Incumplimiento del **{prob_default*100:.2f}%** (Score: **{score_crediticio}**). La relación de cobertura de deuda de **{ratio_cobertura_calc}x** y el nivel de apalancamiento no cumplen con los parámetros del umbral de solvencia. Autorizar esta colocación generaría un valor patrimonial negativo para el fondo.")
        else:
            dictamen("exito", f"Dictamen: SOLICITUD {estatus_dictamen}", 
                     f"El perfil evaluado acredita solvencia técnica con un Score de **{score_crediticio}** y una Probabilidad de Incumplimiento de **{prob_default*100:.2f}%**. Para garantizar la rentabilidad operativa del 20% y el rendimiento del capital social, la **Tasa de Indiferencia asignada es de {tasa_mensual_asignada}% mensual** ({tasa_anual_asignada}% anual). Documento KYC auditable: {archivo_kyc.name}.")

            st.markdown("<br>", unsafe_allow_html=True)
            titulo_seccion("documento_check", "4. Formalización y Alta en Cartera de Préstamos")
            
            st.markdown("Al confirmar la colocación, el sistema registrará el crédito en el servidor y habilitará la emisión de pagarés y tablas de amortización con la tasa actuarial asignada.")
            
            col_conf1, col_conf2 = st.columns([1, 2])
            with col_conf1:
                btn_guardar_prestamo = st.button("Formalizar y Enviar a Cartera Viva", use_container_width=True, type="primary")
            
            if btn_guardar_prestamo:
                with st.spinner("Subiendo expediente a bóveda segura e inscribiendo crédito..."):
                    try:
                        # 1. Preparación del archivo para Storage
                        # Definimos una ruta única basada en RFC y tiempo para evitar colisiones
                        nombre_archivo_storage = f"kyc/{rfc_cliente.strip()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                        file_bytes = archivo_kyc.getvalue()
                        
                        # 2. Subida al bucket 'expedientes' en Supabase
                        res_storage = supabase.storage.from_("expedientes").upload(
                            path=nombre_archivo_storage,
                            file=file_bytes,
                            file_options={"content-type": "application/pdf"}
                        )
                        
                        # 3. Inserción de datos en la tabla 'prestamos'
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
                            # Guardamos la ruta del archivo en Storage para futura auditoría
                            "gestor_originador": f"{usuario_actual} | Doc: {nombre_archivo_storage}"
                        }
                        
                        supabase.table("prestamos").insert(payload_prestamo).execute()
                        
                        st.success(f"¡Formalización Exitosa! El crédito a nombre de {nombre_cliente} está activo. El expediente digital ha sido almacenado permanentemente en la bóveda 'expedientes'.")
                        
                    except Exception as e:
                        # Si algo falla (subida o inserción), informamos al gestor
                        dictamen("peligro", "Error en Formalización", f"No fue posible completar la formalización. Detalle técnico: {str(e)}")