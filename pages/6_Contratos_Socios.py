import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
from src.db import supabase
from src.theme import (
    aplicar_identidad_visual, encabezado_modulo, titulo_seccion,
    dictamen, tarjeta_kpi
)

st.set_page_config(page_title="Legal Socios | SOFOM", layout="wide")
aplicar_identidad_visual()

encabezado_modulo(
    titulo="Emisión de Contratos de Asociación en Participación",
    subtitulo="Generación de instrumentos mercantiles para la formalización del capital de inversión.",
    nombre_icono="documento",
    insignia="INSTRUMENTO LEGAL"
)

# -----------------------------------------------------------------------------
# CLASE PDF PARA CONTRATO A en P
# -----------------------------------------------------------------------------
class ContratoPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'CONTRATO DE ASOCIACIÓN EN PARTICIPACIÓN', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, 'Documento Confidencial - SOFOM E.N.R.', 0, 0, 'C')

def generar_pdf_asociacion(socio_nombre, socio_rfc, monto, porcentaje, vigencia):
    pdf = ContratoPDF()
    pdf.add_page()
    pdf.set_font('Arial', '', 11)
    
    def clean(text): return str(text).encode('latin-1', 'replace').decode('latin-1')
    
    texto = f"""
CONTRATO DE ASOCIACIÓN EN PARTICIPACIÓN que celebran por una parte "LA ASOCIANTE" (LA SOFOM E.N.R.) y por otra parte "EL ASOCIADO" {socio_nombre.upper()}, con RFC {socio_rfc.upper()}, bajo las siguientes cláusulas:

PRIMERA.- OBJETO. "EL ASOCIADO" entrega a "LA ASOCIANTE" la cantidad de ${monto:,.2f} MXN, la cual será destinada exclusivamente al fondeo de operaciones de microcrédito.

SEGUNDA.- PARTICIPACIÓN. "EL ASOCIADO" tendrá derecho a percibir una utilidad correspondiente al {porcentaje}% del rendimiento neto generado por la cartera de crédito fondeada con su capital, de manera quincenal.

TERCERA.- NATURALEZA. Este contrato no constituye una relación laboral, ni una sociedad mercantil común, sino un acuerdo de participación en utilidades y riesgos, conforme a la Ley General de Sociedades Mercantiles.

CUARTA.- VIGENCIA. El presente instrumento tendrá una vigencia de {vigencia} meses, renovable por acuerdo de las partes.

QUINTA.- DOMICILIO. Ambas partes señalan sus domicilios para recibir notificaciones y efectos legales.
    """
    
    pdf.multi_cell(0, 6, clean(texto))
    pdf.ln(30)
    
    # Firmas
    y = pdf.get_y()
    pdf.line(20, y, 90, y)
    pdf.set_xy(20, y+2)
    pdf.cell(70, 5, "LA ASOCIANTE (SOFOM)", 0, 0, 'C')
    
    pdf.line(120, y, 190, y)
    pdf.set_xy(120, y+2)
    pdf.cell(70, 5, "EL ASOCIADO", 0, 1, 'C')
    
    return pdf.output()

# -----------------------------------------------------------------------------
# INTERFAZ
# -----------------------------------------------------------------------------
titulo_seccion("personas", "1. Selección de Inversionista")
try:
    res_s = supabase.table("socios").select("id_socio, nombre_completo, rfc").execute()
    socios_lista = res_s.data if res_s.data else []
except:
    socios_lista = []

if not socios_lista:
    st.info("No hay socios registrados.")
else:
    mapa_socios = {f"{s['nombre_completo']} ({s['rfc']})": s for s in socios_lista}
    seleccion = st.selectbox("Seleccionar Socio:", options=list(mapa_socios.keys()))
    datos_s = mapa_socios[seleccion]

    st.markdown("---")
    titulo_seccion("documento_check", "2. Parámetros del Contrato")
    
    with st.form("form_contrato"):
        c1, c2 = st.columns(2)
        monto = c1.number_input("Capital aportado ($):", value=50000.0, step=1000.0)
        pct = c2.number_input("Porcentaje de participación (%):", value=10.0, step=0.5)
        vigencia = st.number_input("Vigencia (meses):", value=12)
        
        btn_gen = st.form_submit_button("Generar Contrato PDF", use_container_width=True)
        
        if btn_gen:
            pdf_bytes = generar_pdf_asociacion(datos_s["nombre_completo"], datos_s["rfc"], monto, pct, vigencia)
            st.session_state["contrato_socio"] = bytes(pdf_bytes)
            dictamen("exito", "Contrato Generado", "El PDF está listo para descarga y firma.")

if "contrato_socio" in st.session_state:
    st.download_button("📥 Descargar Contrato de Asociación (PDF)", data=st.session_state["contrato_socio"], file_name=f"Contrato_{datos_s['rfc']}.pdf", mime="application/pdf", use_container_width=True)