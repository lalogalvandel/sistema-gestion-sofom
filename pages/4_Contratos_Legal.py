import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
from fpdf import FPDF
from src.db import supabase
from src.theme import (
    aplicar_identidad_visual, encabezado_modulo, titulo_seccion,
    dictamen, tarjeta_kpi
)

st.set_page_config(page_title="Emisión Legal | SOFOM", layout="wide")

# 1. Inyectar identidad visual
aplicar_identidad_visual()

encabezado_modulo(
    titulo="Emisión de Instrumentos Legales y Pagarés",
    subtitulo="Generación automatizada de documentos ejecutivos mercantiles respaldados en servidor.",
    nombre_icono="documento_check",
    insignia="JURÍDICO MERCANTIL"
)

# -----------------------------------------------------------------------------
# CLASE PARA GENERACIÓN DE PDF LEGAL (FPDF2)
# -----------------------------------------------------------------------------
class PagarePDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.set_text_color(26, 54, 93) # Azul marino institucional
        self.cell(0, 10, 'PAGARÉ INCONDICIONAL DE PAGO', 0, 1, 'C')
        self.set_font('Arial', 'I', 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, 'Instrumento Ejecutivo Mercantil - SOFOM E.N.R.', 0, 1, 'C')
        self.ln(5)
        
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Página {self.page_no()} | Documento generado desde Servidor Institucional', 0, 0, 'C')

def generar_pdf_pagare(datos_prestamo, datos_cliente, cuotas_df, lugar_expedicion, aval_nombre, aval_rfc):
    pdf = PagarePDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)
    
    def clean_text(text):
        return str(text).encode('latin-1', 'replace').decode('latin-1')
    
    # 1. Recuadro de Cifras Principales
    pdf.set_fill_color(247, 250, 252)
    pdf.set_draw_color(26, 54, 93)
    pdf.set_line_width(0.5)
    pdf.rect(10, 30, 190, 25, 'DF')
    
    pdf.set_xy(15, 33)
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(90, 6, clean_text(f"BUENO POR: ${datos_prestamo['monto_principal']:,.2f} MXN"), 0, 0, 'L')
    pdf.cell(90, 6, clean_text(f"EXPEDIENTE: {str(datos_prestamo['id_prestamo'])[:8].upper()}"), 0, 1, 'R')
    
    pdf.set_xy(15, 41)
    pdf.set_font('Arial', '', 9)
    pdf.cell(90, 6, clean_text(f"LUGAR DE EXPEDICIÓN: {lugar_expedicion.upper()}"), 0, 0, 'L')
    pdf.cell(90, 6, clean_text(f"FECHA: {datos_prestamo['fecha_desembolso']}"), 0, 1, 'R')
    pdf.ln(15)
    
    # 2. Cuerpo del Pagaré (Cláusula Principal)
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(0, 0, 0)
    
    monto_total = float(datos_prestamo['monto_total_recaudar'])
    tasa_mensual = float(datos_prestamo['tasa_interes_mensual']) * 100
    tasa_moratoria = tasa_mensual * 2.0
    plazos = int(datos_prestamo['plazo_quincenas'])
    cuota_fija = float(datos_prestamo['cuota_fija_proyectada'])
    
    texto_clausula = (
        f"Por medio del presente PAGARÉ, yo, {datos_cliente['nombre_completo'].upper()}, con RFC {datos_cliente['rfc'].upper()}, "
        f"prometo y me obligo pagar incondicionalmente a la orden de LA SOCIEDAD FINANCIERA (SOFOM E.N.R.), "
        f"la cantidad total de ${monto_total:,.2f} MXN (incluye capital e intereses pactados), en la ciudad de {lugar_expedicion}.\n\n"
        f"El pago se efectuará mediante {plazos} cuotas quincenales consecutivas de ${cuota_fija:,.2f} MXN cada una, "
        f"de conformidad con las fechas de vencimiento estipuladas en el Anexo de Amortización adjunto, comenzando a partir de la fecha de desembolso.\n\n"
        f"En caso de falta de pago puntual en cualquiera de las cuotas estipuladas, el saldo insoluto total se dará por vencido anticipadamente, "
        f"causando intereses moratorios a razón del {tasa_moratoria:.2f}% mensual sobre los saldos vencidos hasta su total liquidación, "
        f"además de los gastos de cobranza legal y honorarios judiciales que se generen."
    )
    
    pdf.multi_cell(0, 6, clean_text(texto_clausula), 0, 'J')
    pdf.ln(10)
    
    # 3. Sección de Firmas (Deudor Principal y Aval Solidario)
    pdf.ln(20)
    y_firma = pdf.get_y()
    
    pdf.line(20, y_firma, 85, y_firma)
    pdf.set_xy(20, y_firma + 2)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(65, 5, clean_text("EL DEUDOR / SUSCRIPTOR"), 0, 1, 'C')
    pdf.set_font('Arial', '', 8)
    pdf.set_xy(20, pdf.get_y())
    pdf.cell(65, 4, clean_text(f"{datos_cliente['nombre_completo'].upper()}"), 0, 1, 'C')
    pdf.set_xy(20, pdf.get_y())
    pdf.cell(65, 4, clean_text(f"RFC: {datos_cliente['rfc'].upper()}"), 0, 1, 'C')
    
    if aval_nombre and len(aval_nombre.strip()) > 3:
        pdf.line(115, y_firma, 180, y_firma)
        pdf.set_xy(115, y_firma + 2)
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(65, 5, clean_text("AVAL / OBLIGADO SOLIDARIO"), 0, 1, 'C')
        pdf.set_font('Arial', '', 8)
        pdf.set_xy(115, pdf.get_y())
        pdf.cell(65, 4, clean_text(f"{aval_nombre.upper()}"), 0, 1, 'C')
        if aval_rfc and len(aval_rfc.strip()) >= 10:
            pdf.set_xy(115, pdf.get_y())
            pdf.cell(65, 4, clean_text(f"RFC: {aval_rfc.upper()}"), 0, 1, 'C')
        pdf.set_xy(115, pdf.get_y())
        pdf.cell(65, 4, clean_text("Acepto obligación solidaria e incondicional"), 0, 1, 'C')
        
    # 4. Anexo: Tabla de Amortización
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(26, 54, 93)
    pdf.cell(0, 10, clean_text('ANEXO 1: CALENDARIO DE AMORTIZACIÓN CONCILIADO'), 0, 1, 'L')
    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, clean_text(f"Expediente: {datos_prestamo['id_prestamo']} | Deudor: {datos_cliente['nombre_completo']}"), 0, 1, 'L')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 8)
    pdf.set_fill_color(26, 54, 93)
    pdf.set_text_color(255, 255, 255)
    
    anchos = [15, 30, 35, 35, 35, 40]
    columnas = ["No.", "Vencimiento", "Cuota Fija", "Interés", "Capital", "Saldo Insoluto"]
    
    for i, col in enumerate(columnas):
        pdf.cell(anchos[i], 7, clean_text(col), 1, 0, 'C', True)
    pdf.ln()
    
    pdf.set_font('Arial', '', 8)
    pdf.set_text_color(0, 0, 0)
    pdf.set_fill_color(247, 250, 252)
    
    for idx, fila in cuotas_df.iterrows():
        fill = True if idx % 2 == 0 else False
        pdf.cell(anchos[0], 6, str(fila['numero_cuota']), 1, 0, 'C', fill)
        pdf.cell(anchos[1], 6, str(fila['fecha_vencimiento']), 1, 0, 'C', fill)
        pdf.cell(anchos[2], 6, f"${float(fila['cuota_fija']):,.2f}", 1, 0, 'R', fill)
        pdf.cell(anchos[3], 6, f"${float(fila['interes_cobrado']):,.2f}", 1, 0, 'R', fill)
        pdf.cell(anchos[4], 6, f"${float(fila['abono_capital']):,.2f}", 1, 0, 'R', fill)
        pdf.cell(anchos[5], 6, f"${float(fila['saldo_insoluto']):,.2f}", 1, 0, 'R', fill)
        pdf.ln()
        
    return pdf.output()

# -----------------------------------------------------------------------------
# INTERFAZ DE USUARIO DEL MÓDULO LEGAL
# -----------------------------------------------------------------------------
titulo_seccion("balanza", "1. Selección de Expediente para Emisión Legal")

def obtener_creditos_formalizados():
    try:
        res = supabase.table("prestamos").select("*, clientes(*)").eq("estatus_credito", "VIGENTE").order("fecha_desembolso", desc=True).execute()
        return res.data if res.data else []
    except Exception:
        return []

creditos_db = obtener_creditos_formalizados()

col_sel, col_config = st.columns([1, 1.4])

with col_sel:
    if not creditos_db:
        st.info("No existen créditos formalizados en el servidor. Complete una transacción en el Módulo 2.")
        opciones_legal = ["-- Sin Expedientes Registrados --"]
    else:
        opciones_legal = ["-- Seleccione un Contrato --"]
        mapa_legal = {}
        for c in creditos_db:
            cli = c.get("clientes", {})
            et = f"{cli.get('nombre_completo', 'N/A')} | Préstamo: ${c['monto_principal']:,.2f} MXN"
            opciones_legal.append(et)
            mapa_legal[et] = c
            
    contrato_sel = st.selectbox("Expediente Institucional:", options=opciones_legal)

with col_config:
    st.markdown("#### Parámetros Jurídicos Adicionales")
    if contrato_sel in ["-- Sin Expedientes Registrados --", "-- Seleccione un Contrato --"]:
        dictamen("alerta", "Expediente Requerido", "Seleccione un contrato en el menú desplegable para cargar las cláusulas del pagaré mercantil.")
    else:
        datos_contrato = mapa_legal[contrato_sel]
        datos_cli = datos_contrato.get("clientes", {})
        id_p = datos_contrato["id_prestamo"]
        
        with st.form("form_emision_pdf"):
            lugar_exp = st.text_input("Lugar de Expedición (Ciudad / Estado):", value="Puebla, Puebla")
            
            st.markdown("---")
            st.markdown("#### Datos de Garantía Solidaria (Aval)")
            c_p1, c_p2 = st.columns(2)
            nombre_aval = c_p1.text_input("Nombre del Aval / Obligado Solidario:", placeholder="Ej. María López Morales")
            rfc_aval = c_p2.text_input("RFC del Aval (con homoclave):", max_chars=13, placeholder="Ej. LOMM850321XYZ").upper()
            
            st.markdown("---")
            st.markdown("#### Resumen de Obligación por Contratar")
            
            # Cuadrícula simétrica 2x2 para evitar recortes de texto
            m1, m2 = st.columns(2)
            with m1:
                tarjeta_kpi("billetera", "Principal Otorgado", f"${datos_contrato['monto_principal']:,.2f}", "Capital original prestado", "marino_800")
            with m2:
                tarjeta_kpi("banco", "Total a Pagar", f"${datos_contrato['monto_total_recaudar']:,.2f}", "Capital + Interés pactado", "dorado_600")
                
            st.markdown("<br>", unsafe_allow_html=True)
            
            m3, m4 = st.columns(2)
            with m3:
                tarjeta_kpi("calendario", "Plazo Pactado", f"{datos_contrato['plazo_quincenas']} quincenas", "Calendario de vencimientos", "azul_600")
            with m4:
                tarjeta_kpi("alerta_triangulo", "Tasa Moratoria", f"{float(datos_contrato['tasa_interes_mensual'])*200:.1f}% mensual", "Aplicable sobre saldos vencidos", "peligro")
            
            generar_doc = st.form_submit_button("Generar Pagaré Ejecutivo y Anexo (PDF)", use_container_width=True)
            
            if generar_doc:
                with st.spinner("Compilando instrumento legal y tabla de amortización desde servidor..."):
                    try:
                        res_tabla = supabase.table("plan_amortizacion").select("*").eq("id_prestamo", id_p).order("numero_cuota", desc=False).execute()
                        if not res_tabla.data or len(res_tabla.data) == 0:
                            dictamen("peligro", "Error de Compilación", "No se encontró la tabla de amortización para este préstamo en el servidor.")
                        else:
                            df_cuotas_legal = pd.DataFrame(res_tabla.data)
                            
                            pdf_bytes = generar_pdf_pagare(
                                datos_prestamo=datos_contrato,
                                datos_cliente=datos_cli,
                                cuotas_df=df_cuotas_legal,
                                lugar_expedicion=lugar_exp,
                                aval_nombre=nombre_aval,
                                aval_rfc=rfc_aval
                            )
                            
                            st.session_state["pdf_generado"] = {
                                "bytes": bytes(pdf_bytes),
                                "nombre_archivo": f"Pagare_Ejecutivo_{datos_cli['rfc']}_{str(id_p)[:8]}.pdf"
                            }
                            dictamen("exito", "Instrumento Compilado Exitosamente", "El documento PDF ha sido generado en calidad de impresión con sus respectivas cláusulas y anexos.")
                    except Exception as e:
                        dictamen("peligro", "Error en Generación", f"Fallo durante la compilación del documento PDF: {str(e)}")

st.divider()

# -----------------------------------------------------------------------------
# SECCIÓN 2: DESCARGA DE DOCUMENTO LEGAL
# -----------------------------------------------------------------------------
titulo_seccion("documento", "2. Emisión y Descarga del Instrumento")

if "pdf_generado" in st.session_state and st.session_state["pdf_generado"]:
    doc_info = st.session_state["pdf_generado"]
    st.info(f"Documento listo para descarga: **{doc_info['nombre_archivo']}**")
    
    col_d1, col_d2 = st.columns([1, 2])
    with col_d1:
        st.download_button(
            label="Descargar Instrumento Legal (PDF)",
            data=doc_info["bytes"],
            file_name=doc_info["nombre_archivo"],
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
    with col_d2:
        st.markdown("*Nota jurídica:* El documento se emite con la cláusula de vencimiento anticipado e integra en su segunda página la tabla de amortización conciliada como Anexo 1, protegiendo al fondo ante cualquier incumplimiento de pago en vía ejecutiva mercantil.")
else:
    st.info("Seleccione un expediente y presione el botón de generación para habilitar la descarga del documento PDF.")