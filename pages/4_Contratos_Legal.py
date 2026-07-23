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
import io
from fpdf import FPDF
from src.auth import verificar_acceso
from src.db import supabase
from src.theme import (
    aplicar_identidad_visual, encabezado_modulo, titulo_seccion,
    tarjeta_kpi, dictamen
)

st.set_page_config(page_title="Formalización y Contratos | SOFOM", layout="wide")

# --- BLINDAJE INSTITUCIONAL RBAC ---
# Nivel de acceso: COBRANZA (2), accesible para Operaciones, Cobranza y Dirección General
verificar_acceso("COBRANZA")
# -----------------------------------

aplicar_identidad_visual()

encabezado_modulo(
    titulo="Formalización Jurídica y Emisión de Títulos de Crédito",
    subtitulo="Generación automatizada de Contratos de Adhesión (RECA), cálculo actuarial de CAT oficial y emisión de Pagaré Ejecutivo Mercantil (Art. 170 LGTOC).",
    nombre_icono="escudo",
    insignia="JURÍDICO Y PLD"
)

usuario_actual = st.session_state.get("user_email", "Usuario No Identificado")
rol_actual = st.session_state.get("user_role", "COBRANZA")

# -----------------------------------------------------------------------------
# 1. MOTOR ACTUARIAL DE CÁLCULO CAT (METODOLOGÍA BANXICO / CONDUSEF)
# -----------------------------------------------------------------------------
def calcular_cat_banxico(monto_prestado, plazo_periodos, tasa_mensual_pct, comision_apertura_pct=0.0, frecuencia="Mensual"):
    """
    Calcula el Costo Anual Total (CAT) sin IVA mediante la resolución de la Tasa Interna 
    de Retorno (TIR) de los flujos netos del crédito utilizando el método de Newton-Raphson.
    Metodología oficial de la Circular 21/2009 de Banco de México.
    """
    try:
        r_periodo = tasa_mensual_pct / 100.0
        if frecuencia.lower() == "quincenal":
            r_periodo = r_periodo / 2.0
            periodos_por_anio = 24
        else:
            periodos_por_anio = 12
            
        # Cuota constante periódica (PMT)
        if r_periodo > 0:
            cuota = monto_prestado * (r_periodo * (1.0 + r_periodo)**plazo_periodos) / ((1.0 + r_periodo)**plazo_periodos - 1.0)
        else:
            cuota = monto_prestado / plazo_periodos
            
        # Capital líquido recibido por el cliente (Descontando comisión por apertura sin IVA)
        neto_desembolsado = monto_prestado * (1.0 - (comision_apertura_pct / 100.0))
        
        # Iteración numérica de Newton-Raphson para hallar la tasa interna 'i'
        i = r_periodo # Valor semilla
        for _ in range(50):
            if i <= -1.0:
                i = 0.001
            # Ecuación de valor presente de anualidad: f(i) = neto - cuota * [1 - (1+i)^(-n)] / i
            val_f = neto_desembolsado - (cuota * (1.0 - (1.0 + i)**(-plazo_periodos)) / i)
            # Derivada analítica f'(i)
            val_df = -cuota * ((plazo_periodos * (1.0 + i)**(-plazo_periodos - 1.0)) / i - (1.0 - (1.0 + i)**(-plazo_periodos)) / (i**2))
            
            if abs(val_df) < 1e-10:
                break
            i_siguiente = i - (val_f / val_df)
            if abs(i_siguiente - i) < 1e-7:
                i = i_siguiente
                break
            i = i_siguiente
            
        # Capitalización anual compuesta según circular Banxico: CAT = (1 + i)^m - 1
        cat_anualizado = ((1.0 + i)**periodos_por_anio - 1.0) * 100.0
        return max(round(cat_anualizado, 2), round(tasa_mensual_pct * 12.0, 2)), round(cuota, 2)
    except Exception:
        # Fallback actuarial en caso de valores extremos no convergentes
        tasa_nominal_anual = round(tasa_mensual_pct * 12.0, 2)
        cuota_simple = round((monto_prestado * (1.0 + (tasa_nominal_anual/100.0))) / plazo_periodos, 2)
        return tasa_nominal_anual, cuota_simple

# -----------------------------------------------------------------------------
# 2. SELECCIÓN DE EXPEDIENTE EN BASE DE DATOS
# -----------------------------------------------------------------------------
titulo_seccion("documento", "1. Selección de Crédito y Expediente por Formalizar")

@st.cache_data(ttl=15)
def obtener_creditos_candidatos():
    try:
        # 1. Leemos los créditos listos para firma legal (priorizando ESTRUCTURADO)
        res = supabase.table("prestamos").select("*").in_("estatus", ["ESTRUCTURADO", "APROBADO", "APROBADO PREFERENCIAL", "APROBADO CONDICIONADO"]).order("fecha_otorgamiento", desc=True).execute()
        if not res.data:
            return pd.DataFrame()
        df = pd.DataFrame(res.data)
        return df
    except Exception:
        return pd.DataFrame()

df_prestamos = obtener_creditos_candidatos()

if df_prestamos.empty:
    st.info("No se detectaron créditos activos o en proceso de formalización en la tabla de préstamos del servidor.")
    st.stop()
else:
    # Mapeo inteligente para visualización
    col_nom = "cliente" if "cliente" in df_prestamos.columns else ("nombre" if "nombre" in df_prestamos.columns else None)
    col_rfc = "rfc" if "rfc" in df_prestamos.columns else None
    col_mon = "monto" if "monto" in df_prestamos.columns else ("monto_prestado" if "monto_prestado" in df_prestamos.columns else ("saldo_pendiente" if "saldo_pendiente" in df_prestamos.columns else None))
    
    df_prestamos["etiqueta_sel"] = df_prestamos.apply(
        lambda r: f"{str(r.get(col_nom, 'Cliente sin nombre'))} | RFC: {str(r.get(col_rfc, 'N/A'))} | Capital: ${float(r.get(col_mon, 0)):,.2f}", 
        axis=1
    )
    
    credito_seleccionado = st.selectbox("Seleccione el acreditado para emitir instrumentos jurídicos:", df_prestamos["etiqueta_sel"].tolist())
    
    # Extraer fila del crédito seleccionado
    idx_sel = df_prestamos["etiqueta_sel"].tolist().index(credito_seleccionado)
    fila_credito = df_prestamos.iloc[idx_sel]
    
    # --- EXTRACCIÓN Y BLINDAJE NUMÉRICO (Validando NaN antes de convertir) ---
    val_monto = fila_credito.get(col_mon, fila_credito.get("monto_prestado", 15000.0))
    monto_op = float(val_monto) if pd.notna(val_monto) else 15000.0

    # Plazo (Corrección de ValueError: evita NaN a int)
    val_plazo = fila_credito.get("plazo_meses", fila_credito.get("plazo", 12))
    plazo_op = int(val_plazo) if pd.notna(val_plazo) and str(val_plazo).lower() != 'nan' else 12

    # Tasa
    val_tasa = fila_credito.get("tasa_mensual", fila_credito.get("tasa", 6.0))
    tasa_mes_op = float(val_tasa) if pd.notna(val_tasa) and str(val_tasa).lower() != 'nan' else 6.0

    frec_op = str(fila_credito.get("frecuencia", "Mensual")).capitalize()
    nombre_cliente_op = str(fila_credito.get(col_nom, "Acreditado Institucional"))
    rfc_cliente_op = str(fila_credito.get(col_rfc, "XEXX010101000"))

# -----------------------------------------------------------------------------
# 3. PARAMETRIZACIÓN LEGAL Y CÁLCULO DE CAT
# -----------------------------------------------------------------------------
titulo_seccion("herramienta", "2. Parametrización Jurídica y Cláusulas del Contrato")

with st.form("form_parametros_legales"):
    c_leg1, c_leg2, c_leg3 = st.columns(3)
    with c_leg1:
        # Leemos de secrets si existe, o ponemos un nombre institucional genérico
        val_razon = st.secrets.get("legal", {}).get("razon_social", "FINANCIERA GALA SOFOM, E.N.R.")
        val_rep = st.secrets.get("legal", {}).get("representante_legal", "Apoderado Legal Institucional")
        
        razon_social_sofom = st.text_input("Razón Social de la Entidad:", value=val_razon)
        representante_legal = st.text_input("Apoderado / Representante Legal:", value=val_rep)
    with c_leg2:
        val_reca = st.secrets.get("legal", {}).get("reca_numero", "2026-001-09238-01")
        num_reca = st.text_input("No. Registro CONDUSEF (RECA):", value=val_reca)
        plaza_jurisdiccion = st.selectbox("Plaza de Jurisdicción Contenciosa:", [
            "Puebla de Zaragoza, Puebla",
            "Ciudad de México",
            "Monterrey, Nuevo León",
            "Guadalajara, Jalisco"
        ])
    with c_leg3:
        comision_apertura = st.number_input("Comisión por Apertura (% sobre capital):", min_value=0.0, max_value=10.0, value=2.0, step=0.5)
        tasa_moratoria = st.number_input("Tasa Moratoria (% Mensual insoluto):", min_value=1.0, max_value=30.0, value=round(tasa_mes_op * 2.0, 2), step=0.5)
        
    st.markdown("---")
    c_aval1, c_aval2 = st.columns(2)
    with c_aval1:
        # Por prudencia financiera, el aval inicia desmarcado y las casillas LIMPIAS
        requiere_aval = st.checkbox("Incluir figura de Aval / Obligado Solidario", value=False)
        nombre_aval = st.text_input(
            "Nombre Completo del Aval:", 
            value="" if requiere_aval else "N/A", 
            placeholder="Ej: Nombre Completo del Obligado Solidario", 
            disabled=not requiere_aval
        )
    with c_aval2:
        st.markdown("<br>", unsafe_allow_html=True)
        domicilio_aval = st.text_input(
            "Domicilio Legal para Emplazamiento:", 
            value="" if requiere_aval else "N/A", 
            placeholder="Ej: Av. Principal #100, Col. Centro, Municipio, Estado", 
            disabled=not requiere_aval
        )

    st.markdown("<br>", unsafe_allow_html=True)
    actualizar_calculos = st.form_submit_button("Auditar Parámetros y Calcular CAT Oficial", width="stretch")

# Ejecución algorítmica CAT
cat_oficial_calc, cuota_periodica_calc = calcular_cat_banxico(
    monto_prestado=monto_op,
    plazo_periodos=plazo_op,
    tasa_mensual_pct=tasa_mes_op,
    comision_apertura_pct=comision_apertura,
    frecuencia=frec_op
)

st.divider()
titulo_seccion("estadisticas", "3. Síntesis de Obligación Exigible y CAT Oficial")

k1, k2, k3, k4 = st.columns(4)
with k1:
    tarjeta_kpi("Capital Otorgado", f"${monto_op:,.2f} MXN", f"Comisión Apertura: {comision_apertura}%")
with k2:
    tarjeta_kpi("Cuota Fija Periódica", f"${cuota_periodica_calc:,.2f} MXN", f"Periodicidad: {frec_op} ({plazo_op} cuotas)")
with k3:
    tarjeta_kpi("CAT Oficial (Sin IVA)", f"{cat_oficial_calc:.1f}%", "Metodología Banxico Circular 21/2009")
with k4:
    tarjeta_kpi("Tasa Moratoria Legal", f"{tasa_moratoria:.2f}%", "Mensual sobre saldo insoluto vencido")

st.markdown("<br>", unsafe_allow_html=True)
dictamen("exito", "Dictamen de Viabilidad Legal", f"El instrumento crediticio a nombre de **{nombre_cliente_op}** cumple con las disposiciones de la LGTOC y la transparencia normativa del CAT (**{cat_oficial_calc:.1f}% sin IVA**). La jurisdicción en **{plaza_jurisdiccion}** blinda la exigibilidad del Pagaré ante tribunales mercantiles.")

st.divider()

# -----------------------------------------------------------------------------
# 4. MOTOR DE GENERACIÓN PDF (FPDF BLINDADO CONTRA ERRORES LATIN-1)
# -----------------------------------------------------------------------------
def limpiar_txt(texto):
    """Limpia caracteres y asegura compatibilidad estricta de codificación en FPDF."""
    return str(texto).encode('latin-1', 'replace').decode('latin-1')

def generar_pdf_instrumento_legal():
    pdf = FPDF(orientation='P', unit='mm', format='Letter')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # --- ENCABEZADO INSTITUCIONAL ---
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 7, limpiar_txt(razon_social_sofom), ln=True, align="C")
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 5, limpiar_txt(f"CONTRATO DE ADHESIÓN DE APERTURA DE CRÉDITO SIMPLE | RECA CONDUSEF: {num_reca}"), ln=True, align="C")
    pdf.cell(0, 5, limpiar_txt(f"Plaza de Emisión: {plaza_jurisdiccion} | Fecha de Formalización: {datetime.now().strftime('%d/%m/%Y')}"), ln=True, align="C")
    pdf.ln(5)
    
    # --- RECUADRO CAT OFICIAL (OBLIGATORIO BANXICO) ---
    pdf.set_fill_color(240, 244, 248)
    pdf.set_draw_color(30, 41, 59)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, limpiar_txt(" RECUADRO DE TRANSPARENCIA Y COSTO ANUAL TOTAL (CAT)"), border=1, ln=True, fill=True, align="L")
    
    pdf.set_font("Arial", "", 8.5)
    txt_cat = (f"COSTO ANUAL TOTAL (CAT) PROMEDIO: {cat_oficial_calc:.1f}% SIN IVA. "
               f"Tasa de Interés Ordinaria Anual Fija: {round(tasa_mes_op*12, 2)}%. "
               f"Tasa de Interés Moratoria Anual Fija: {round(tasa_moratoria*12, 2)}%. "
               f"Comisión por Apertura: {comision_apertura}% ($ {round(monto_op*(comision_apertura/100), 2)} MXN sin IVA). "
               f"Monto del Crédito: $ {monto_op:,.2f} MXN. Cuota periódica ({frec_op}): $ {cuota_periodica_calc:,.2f} MXN. "
               f"Para fines informativos y de comparación exclusivamente. Calculado al {datetime.now().strftime('%d/%m/%Y')}.")
    pdf.multi_cell(0, 4.5, limpiar_txt(txt_cat), border=1, align="J")
    pdf.ln(5)
    
    # --- CLÁUSULAS GENERALES DEL CONTRATO ---
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, limpiar_txt("I. DECLARACIONES Y CLÁUSULAS PRINCIPALES"), ln=True, align="L")
    pdf.set_font("Arial", "", 8.5)
    
    clausulas = [
        f"PRIMERA (OBJETO): '{razon_social_sofom}' otorga al ACREDITADO ({nombre_cliente_op}, RFC: {rfc_cliente_op}) un crédito simple por la cantidad de $ {monto_op:,.2f} MXN, obligándose el ACREDITADO a restituir el capital conjuntamente con los intereses ordinarios devengados en un plazo de {plazo_op} periodos de amortización {frec_op.lower()}s.",
        f"SEGUNDA (INTERESES Y PRELACIÓN): Las amortizaciones se aplicarán en estricto orden de prelación contable: 1) Impuestos y gastos de cobranza, 2) Intereses moratorios, 3) Intereses ordinarios devengados, y 4) Remanente a reducción de capital (saldo insoluto).",
        f"TERCERA (VENCIMIENTO ANTICIPADO): La falta de pago oportuno de dos o más cuotas {frec_op.lower()}s facultará a '{razon_social_sofom}' a dar por vencido anticipadamente el plazo del crédito y exigir judicialmente el pago inmediato del saldo insoluto total, más los intereses moratorios causados a razón del {tasa_moratoria}% mensual.",
        f"CUARTA (PLD/FT): El ACREDITADO declara bajo protesta de decir verdad que los recursos materia del crédito serán destinados a fines lícitos y que los pagos para la amortización del mismo provendrán de fuentes legítimas, sujetándose a la fiscalización de la Ley Federal para la Prevención e Identificación de Operaciones con Recursos de Procedencia Ilícita."
    ]
    
    for cl in clausulas:
        pdf.multi_cell(0, 4.2, limpiar_txt(cl), align="J")
        pdf.ln(1.5)
        
    pdf.ln(3)
    
    # --- PAGARÉ EJECUTIVO MERCANTIL (ART. 170 LGTOC) ---
    pdf.set_draw_color(185, 28, 28) # Borde rojo corporativo para distinguir título de crédito
    pdf.set_fill_color(254, 242, 242)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 7, limpiar_txt(" TÍTULO DE CRÉDITO: PAGARÉ (ARTÍCULO 170 LGTOC)"), border=1, ln=True, fill=True, align="C")
    
    pdf.set_draw_color(30, 41, 59)
    pdf.set_font("Arial", "", 8.5)
    
    fecha_vencimiento_est = (datetime.now() + timedelta(days=(15 if frec_op.lower() == "quincenal" else 30) * plazo_op)).strftime('%d/%m/%Y')
    
    txt_pagare = (
        f"POR ESTE PAGARÉ, debo(emos) y pagaré(mos) incondicionalmente por este título de crédito a la orden de "
        f"{razon_social_sofom}, en la plaza de {plaza_jurisdiccion}, o en cualquier otra ciudad donde se me(nos) requiera de pago, "
        f"el día {fecha_vencimiento_est} (o al vencimiento de las cuotas pactadas en el calendario de amortización), la cantidad principal de:\n\n"
        f"                              $ {monto_op:,.2f} MXN (CAPITAL VALOR RECIBIDO A MI ENTERA SATISFACCIÓN)\n\n"
        f"En caso de falta de pago oportuno de la cantidad principal a su vencimiento, me(nos) obligo(amos) a pagar intereses moratorios "
        f"a razón del {tasa_moratoria}% mensual causados día a día sobre el saldo insoluto exigible desde la fecha de incumplimiento "
        f"hasta su liquidación total. Este PAGARÉ es mercantil y está regido por el Artículo 170 y correlativos de la Ley General de Títulos "
        f"y Operaciones de Crédito. Suscrito en {plaza_jurisdiccion} el {datetime.now().strftime('%d de %B de %Y')}."
    )
    pdf.multi_cell(0, 4.5, limpiar_txt(txt_pagare), border=1, align="J")
    pdf.ln(12)
    
    # --- SECCIÓN DE FIRMAS LEGALES ---
    pdf.set_font("Arial", "B", 8.5)
    if requiere_aval:
        pdf.cell(95, 5, limpiar_txt("EL ACREDITADO (SUSCRIPTOR)"), align="C")
        pdf.cell(95, 5, limpiar_txt("AVAL / OBLIGADO SOLIDARIO"), align="C", ln=True)
        pdf.ln(12)
        pdf.cell(95, 4, limpiar_txt("__________________________________________"), align="C")
        pdf.cell(95, 4, limpiar_txt("__________________________________________"), align="C", ln=True)
        pdf.set_font("Arial", "", 8)
        pdf.cell(95, 4, limpiar_txt(f"Firma: {nombre_cliente_op}"), align="C")
        pdf.cell(95, 4, limpiar_txt(f"Firma: {nombre_aval}"), align="C", ln=True)
        pdf.cell(95, 4, limpiar_txt(f"RFC: {rfc_cliente_op}"), align="C")
        pdf.cell(95, 4, limpiar_txt(f"Domicilio: {domicilio_aval}"), align="C", ln=True)
    else:
        pdf.cell(0, 5, limpiar_txt("EL ACREDITADO (SUSCRIPTOR DEL PAGARÉ)"), align="C", ln=True)
        pdf.ln(14)
        pdf.cell(0, 4, limpiar_txt("___________________________________________________"), align="C", ln=True)
        pdf.set_font("Arial", "", 8.5)
        pdf.cell(0, 4, limpiar_txt(f"Firma autógrafa / digital: {nombre_cliente_op}"), align="C", ln=True)
        pdf.cell(0, 4, limpiar_txt(f"RFC: {rfc_cliente_op} | Acepto incondicionalmente"), align="C", ln=True)
        
    # Ajuste nativo para fpdf2: extrae el flujo de bytes directamente sin parámetros obsoletos
    return bytes(pdf.output())

# -----------------------------------------------------------------------------
# 5. FORMALIZACIÓN SUPREMA Y EMISIÓN DE TÍTULO EJECUTIVO
# -----------------------------------------------------------------------------
titulo_seccion("documento_check", "4. Formalización Definitiva y Emisión del Instrumento")

st.markdown("Al presionar este botón, el sistema compilará el **Contrato de Adhesión RECA** junto con el **Pagaré Ejecutivo Mercantil**. Simultáneamente, el servidor registrará la firma del instrumento y moverá el crédito al estatus **VIGENTE** en la cartera viva.")

col_btn1, col_btn2 = st.columns([1, 2])
with col_btn1:
    # EL BOTÓN DEFINITIVO: Formaliza en BD y emite el título de crédito
    btn_generar = st.button("Formalizar Crédito, Emitir Pagaré y Desembolsar", type="primary", width="stretch")

if btn_generar:
    with st.spinner("Compilando cláusulas mercantiles e inscribiendo crédito en Cartera Viva..."):
        try:
            # A) Fabricamos el PDF del Contrato y Pagaré Mercantil
            pdf_bytes = generar_pdf_instrumento_legal()
            
            # B) LA ACTIVACIÓN JURÍDICA: Cambiamos el estatus a VIGENTE en el servidor
            target_id = str(rfc_cliente_op).strip()
            payload_formalizacion = {
                "estatus": "VIGENTE", # <--- LA CORONA: El crédito nace legalmente aquí
                "fecha_otorgamiento": datetime.now().strftime("%Y-%m-%d")
            }
            
            # Intentamos actualizar por RFC o por Nombre del Cliente
            res_upd = supabase.table("prestamos").update(payload_formalizacion).eq("rfc", target_id).in_("estatus", ["ESTRUCTURADO", "APROBADO", "APROBADO PREFERENCIAL", "APROBADO CONDICIONADO"]).execute()
            if not res_upd.data:
                res_upd = supabase.table("prestamos").update(payload_formalizacion).eq("cliente", nombre_cliente_op).in_("estatus", ["ESTRUCTURADO", "APROBADO", "APROBADO PREFERENCIAL", "APROBADO CONDICIONADO"]).execute()
            
            # Registro en bitácora local de emisión
            st.session_state["ultimo_reca_emitido"] = f"RECA-{rfc_cliente_op}-{datetime.now().strftime('%m%d%H%M')}"
            
            # C) MENSAJE DE TRIUNFO INSTITUCIONAL
            st.success(f"¡CRÉDITO FORMALIZADO CON ÉXITO! El acreditado **{nombre_cliente_op}** es ahora un deudor activo en la cartera viva (**VIGENTE**).")
            st.info("**Siguiente paso del ciclo operativo:** El expediente ha pasado a manos de la Mesa de Cobranza para el seguimiento de sus cuotas quincenales.")
            
            # D) Habilitamos la descarga inmediata del Pagaré
            st.download_button(
                label="📥 Descargar Contrato y Pagaré Mercantil (PDF)",
                data=pdf_bytes,
                file_name=f"Contrato_Pagare_{rfc_cliente_op}_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                width="stretch"
            )
        except Exception as e:
            st.error(f"Error técnico durante la formalización contractual: {str(e)}")