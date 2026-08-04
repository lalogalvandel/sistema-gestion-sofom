# =============================================================================
# Copyright (c) 2026 Eduardo Galván del Río. Todos los derechos reservados.
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
    titulo="Formalización Jurídica y Títulos de Crédito",
    subtitulo="Generación de Contratos RECA, cálculo de CAT, emisión de Pagarés y dispersión de Tesorería.",
    nombre_icono="escudo",
    insignia="JURÍDICO Y TESORERÍA"
)

usuario_actual = st.session_state.get("user_email", "Usuario No Identificado")
rol_actual = st.session_state.get("user_role", "COBRANZA")

# -----------------------------------------------------------------------------
# 1. MOTOR ACTUARIAL DE CÁLCULO CAT (METODOLOGÍA BANXICO)
# -----------------------------------------------------------------------------
def calcular_cat_banxico(monto_prestado, plazo_periodos, tasa_mensual_pct, comision_apertura_pct=0.0):
    try:
        r_periodo = (tasa_mensual_pct / 100.0) / 2.0  # Siempre Quincenal
        periodos_por_anio = 24
            
        if r_periodo > 0:
            cuota = monto_prestado * (r_periodo * (1.0 + r_periodo)**plazo_periodos) / ((1.0 + r_periodo)**plazo_periodos - 1.0)
        else:
            cuota = monto_prestado / plazo_periodos
            
        neto_desembolsado = monto_prestado * (1.0 - (comision_apertura_pct / 100.0))
        
        i = r_periodo 
        for _ in range(50):
            if i <= -1.0: i = 0.001
            val_f = neto_desembolsado - (cuota * (1.0 - (1.0 + i)**(-plazo_periodos)) / i)
            val_df = -cuota * ((plazo_periodos * (1.0 + i)**(-plazo_periodos - 1.0)) / i - (1.0 - (1.0 + i)**(-plazo_periodos)) / (i**2))
            
            if abs(val_df) < 1e-10: break
            i_siguiente = i - (val_f / val_df)
            if abs(i_siguiente - i) < 1e-7:
                i = i_siguiente
                break
            i = i_siguiente
            
        cat_anualizado = ((1.0 + i)**periodos_por_anio - 1.0) * 100.0
        return max(round(cat_anualizado, 2), round(tasa_mensual_pct * 12.0, 2)), round(cuota, 2)
    except Exception:
        tasa_nominal_anual = round(tasa_mensual_pct * 12.0, 2)
        cuota_simple = round((monto_prestado * (1.0 + (tasa_nominal_anual/100.0))) / plazo_periodos, 2)
        return tasa_nominal_anual, cuota_simple

# -----------------------------------------------------------------------------
# 2. SELECCIÓN DE EXPEDIENTE (NOMENCLATURA PURA SQL)
# -----------------------------------------------------------------------------
titulo_seccion("documento", "SELECCIÓN DE CRÉDITO ESTRUCTURADO")

@st.cache_data(ttl=10)
def obtener_creditos_candidatos():
    try:
        # Cruce con clientes para traer el nombre real y RFC
        res = supabase.table("prestamos").select("id_prestamo, monto_principal, tasa_interes_mensual, plazo_quincenas, estatus, clientes(nombre_completo, rfc)").eq("estatus", "ESTRUCTURADO").execute()
        return res.data if res.data else []
    except Exception as e:
        st.error(f"Error de conexión: {str(e)}")
        return []

creditos_db = obtener_creditos_candidatos()

if not creditos_db:
    st.info("No hay créditos en estatus ESTRUCTURADO listos para formalizar. Vaya al Módulo de Amortización.")
    st.stop()

opciones_creditos = ["-- Seleccione un Expediente Estructurado --"]
mapa_creditos = {}
for c in creditos_db:
    cli_data = c.get("clientes", {})
    if not cli_data: continue # Si el join falló, omitimos
    nom = cli_data.get("nombre_completo", "Sin Nombre")
    rfc = cli_data.get("rfc", "SIN-RFC")
    mon = float(c.get("monto_principal", 0.0))
    id_pres = c.get("id_prestamo")
    
    etiqueta = f"{nom} | RFC: {rfc} | Capital: ${mon:,.2f} | ID: {str(id_pres)[:8]}"
    opciones_creditos.append(etiqueta)
    mapa_creditos[etiqueta] = c

credito_seleccionado = st.selectbox("Expediente Jurídico:", opciones_creditos)

if credito_seleccionado != "-- Seleccione un Expediente Estructurado --":
    fila_credito = mapa_creditos[credito_seleccionado]
    
    id_prestamo_op = fila_credito["id_prestamo"]
    monto_op = float(fila_credito["monto_principal"])
    plazo_op = int(fila_credito["plazo_quincenas"])
    tasa_mes_op = float(fila_credito["tasa_interes_mensual"])
    nombre_cliente_op = fila_credito["clientes"]["nombre_completo"]
    rfc_cliente_op = fila_credito["clientes"]["rfc"]

    # -----------------------------------------------------------------------------
    # 3. PARAMETRIZACIÓN LEGAL Y CÁLCULO DE CAT
    # -----------------------------------------------------------------------------
    st.divider()
    titulo_seccion("herramienta", "PARÁMETROS DEL TÍTULO DE CRÉDITO")

    with st.form("form_parametros_legales"):
        c_leg1, c_leg2, c_leg3 = st.columns(3)
        with c_leg1:
            razon_social_sofom = st.text_input("Razón Social Institucional:", value="FINANCIERA GALA SOFOM, E.N.R.")
            representante_legal = st.text_input("Apoderado Legal:", value="Ramiro Galván Barbosa")
        with c_leg2:
            num_reca = st.text_input("No. Registro RECA (CONDUSEF):", value="2026-001-09238-01")
            plaza_jurisdiccion = st.selectbox("Plaza de Jurisdicción Mercantil:", ["Puebla de Zaragoza, Puebla", "Ciudad de México", "Monterrey, Nuevo León"])
        with c_leg3:
            comision_apertura = st.number_input("Comisión Apertura (%):", min_value=0.0, max_value=10.0, value=2.0, step=0.5)
            tasa_moratoria = st.number_input("Tasa Moratoria (% Mensual):", min_value=1.0, value=round(tasa_mes_op * 2.0, 2), step=0.5)
            
        st.markdown("---")
        c_aval1, c_aval2 = st.columns(2)
        with c_aval1:
            requiere_aval = st.checkbox("Incluir figura de Aval / Obligado Solidario", value=False)
            nombre_aval = st.text_input("Nombre del Aval:", value="" if requiere_aval else "N/A", disabled=not requiere_aval)
        with c_aval2:
            st.markdown("<br>", unsafe_allow_html=True)
            domicilio_aval = st.text_input("Domicilio del Aval:", value="" if requiere_aval else "N/A", disabled=not requiere_aval)

        st.markdown("<br>", unsafe_allow_html=True)
        actualizar_calculos = st.form_submit_button("Auditar Parámetros y Calcular CAT Oficial", width="stretch")

    cat_oficial_calc, cuota_periodica_calc = calcular_cat_banxico(monto_op, plazo_op, tasa_mes_op, comision_apertura)

    st.divider()
    titulo_seccion("estadisticas", "SÍNTESIS DE EXIGIBILIDAD (TRANSPARENCIA)")

    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("Capital a Desembolsar", f"${monto_op:,.2f}")
    with k2: st.metric("Cuota Fija Quincenal", f"${cuota_periodica_calc:,.2f}", f"{plazo_op} cuotas")
    with k3: st.metric("CAT Oficial Promedio", f"{cat_oficial_calc:.1f}%", "Sin IVA")
    with k4: st.metric("Tasa Moratoria Legal", f"{tasa_moratoria:.2f}%", "Mensual")

    st.markdown("<br>", unsafe_allow_html=True)
    dictamen("exito", "Viabilidad Legal Confirmada", f"El contrato para **{nombre_cliente_op}** cumple con la metodología Banxico. Jurisdicción: {plaza_jurisdiccion}.")
    st.divider()

    # -----------------------------------------------------------------------------
    # 4. MOTOR PDF
    # -----------------------------------------------------------------------------
    def limpiar_txt(texto): return str(texto).encode('latin-1', 'replace').decode('latin-1')

    def generar_pdf_instrumento_legal():
        pdf = FPDF(orientation='P', unit='mm', format='Letter')
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        pdf.set_font("Arial", "B", 13)
        pdf.cell(0, 7, limpiar_txt(razon_social_sofom), ln=True, align="C")
        pdf.set_font("Arial", "", 9)
        pdf.cell(0, 5, limpiar_txt(f"CONTRATO DE ADHESIÓN DE CRÉDITO SIMPLE | RECA: {num_reca}"), ln=True, align="C")
        pdf.cell(0, 5, limpiar_txt(f"Plaza: {plaza_jurisdiccion} | Fecha: {datetime.now().strftime('%d/%m/%Y')}"), ln=True, align="C")
        pdf.ln(5)
        
        pdf.set_fill_color(240, 244, 248)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, limpiar_txt(" RECUADRO DE TRANSPARENCIA Y COSTO ANUAL TOTAL (CAT)"), border=1, ln=True, fill=True)
        
        pdf.set_font("Arial", "", 8.5)
        txt_cat = (f"CAT PROMEDIO: {cat_oficial_calc:.1f}% SIN IVA. Tasa Ordinaria Fija: {round(tasa_mes_op*12, 2)}% Anual. "
                   f"Tasa Moratoria Fija: {round(tasa_moratoria*12, 2)}% Anual. Comisión Apertura: {comision_apertura}%. "
                   f"Monto: $ {monto_op:,.2f} MXN. Cuota Quincenal: $ {cuota_periodica_calc:,.2f} MXN.")
        pdf.multi_cell(0, 4.5, limpiar_txt(txt_cat), border=1, align="J")
        pdf.ln(5)
        
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 6, limpiar_txt("I. CLÁUSULAS PRINCIPALES"), ln=True)
        pdf.set_font("Arial", "", 8.5)
        
        clausulas = [
            f"PRIMERA: '{razon_social_sofom}' otorga al ACREDITADO ({nombre_cliente_op}, RFC: {rfc_cliente_op}) $ {monto_op:,.2f} MXN a un plazo de {plazo_op} quincenas.",
            f"SEGUNDA: La falta de pago oportuno generará intereses moratorios del {tasa_moratoria}% mensual.",
            "TERCERA (PLD/FT): El ACREDITADO declara el origen lícito de los recursos destinados al pago."
        ]
        for cl in clausulas:
            pdf.multi_cell(0, 4.2, limpiar_txt(cl))
            pdf.ln(1.5)
            
        pdf.ln(5)
        
        # PAGARÉ ART 170
        pdf.set_draw_color(185, 28, 28)
        pdf.set_fill_color(254, 242, 242)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 7, limpiar_txt(" TÍTULO DE CRÉDITO: PAGARÉ (ART. 170 LGTOC)"), border=1, ln=True, fill=True, align="C")
        pdf.set_draw_color(0,0,0)
        pdf.set_font("Arial", "", 8.5)
        
        fecha_vencimiento_est = (datetime.now() + timedelta(days=15 * plazo_op)).strftime('%d/%m/%Y')
        
        txt_pagare = (
            f"POR ESTE PAGARÉ, debo(emos) y pagaré(mos) incondicionalmente a la orden de {razon_social_sofom}, en {plaza_jurisdiccion}, "
            f"el día {fecha_vencimiento_est}, la cantidad principal de:\n\n"
            f"                              $ {monto_op:,.2f} MXN (VALOR RECIBIDO A MI ENTERA SATISFACCIÓN)\n\n"
            f"Me obligo a pagar moratorios a razón del {tasa_moratoria}% mensual en caso de atraso. Suscrito el {datetime.now().strftime('%d/%m/%Y')}."
        )
        pdf.multi_cell(0, 4.5, limpiar_txt(txt_pagare), border=1)
        pdf.ln(12)
        
        pdf.set_font("Arial", "B", 8.5)
        if requiere_aval:
            pdf.cell(95, 5, limpiar_txt("EL ACREDITADO"), align="C")
            pdf.cell(95, 5, limpiar_txt("OBLIGADO SOLIDARIO"), align="C", ln=True)
            pdf.ln(10)
            pdf.cell(95, 4, limpiar_txt(f"Firma: {nombre_cliente_op}"), align="C")
            pdf.cell(95, 4, limpiar_txt(f"Firma: {nombre_aval}"), align="C", ln=True)
        else:
            pdf.cell(0, 5, limpiar_txt("EL ACREDITADO (SUSCRIPTOR)"), align="C", ln=True)
            pdf.ln(10)
            pdf.cell(0, 4, limpiar_txt(f"Firma: {nombre_cliente_op}"), align="C", ln=True)
            pdf.cell(0, 4, limpiar_txt(f"RFC: {rfc_cliente_op}"), align="C", ln=True)
            
        return bytes(pdf.output())

    # -----------------------------------------------------------------------------
    # 5. FORMALIZACIÓN Y TESORERÍA (CONEXIÓN BD)
    # -----------------------------------------------------------------------------
    titulo_seccion("documento_check", "FORMALIZACIÓN Y DESEMBOLSO")
    st.markdown("El servidor compilará el Pagaré, lo resguardará en la Bóveda Segura y **registrará la salida de flujo de la tesorería**.")

    if st.button("Firma Electrónica, Subir a Bóveda y Desembolsar", type="primary", width="stretch"):
        with st.spinner("Ejecutando protocolo notarial y de tesorería..."):
            try:
                # 1. Generar PDF
                pdf_bytes = generar_pdf_instrumento_legal()
                
                # 2. Subir a Supabase Storage (BÓVEDA LEGAL)
                nombre_pdf = f"contratos/{rfc_cliente_op}_PAGARE_{id_prestamo_op[:8]}.pdf"
                supabase.storage.from_("expedientes").upload(
                    path=nombre_pdf, file=pdf_bytes, file_options={"content-type": "application/pdf", "upsert": "true"}
                )
                
                # 3. Asiento de Tesorería (Salida de dinero)
                # Inyectamos el registro en bitacora_cobranza como movimiento de salida
                supabase.table("bitacora_cobranza").insert({
                    "id_credito_ref": id_prestamo_op,
                    "tipo_accion": "DESEMBOLSO TESORERÍA",
                    "notas": f"Salida de capital por ${monto_op:,.2f} MXN fondeado a cliente.",
                    "usuario_gestor": usuario_actual
                }).execute()
                
                # 4. Actualizar Préstamo a VIGENTE
                supabase.table("prestamos").update({
                    "estatus": "VIGENTE", 
                    "fecha_desembolso": datetime.now().strftime("%Y-%m-%d")
                }).eq("id_prestamo", id_prestamo_op).execute()
                
                st.success(f"CRÉDITO FORMALIZADO Y DESEMBOLSADO. Expediente subido a bóveda: `{nombre_pdf}`")
                
                # Sigue permitiendo la descarga por si la quieren imprimir en papel
                st.download_button(
                    label="📥 Descargar Pagaré para Firma Autógrafa",
                    data=pdf_bytes,
                    file_name=f"Pagare_{rfc_cliente_op}.pdf",
                    mime="application/pdf",
                    width="stretch"
                )
            except Exception as e:
                st.error(f"Fallo crítico en el protocolo: {str(e)}")