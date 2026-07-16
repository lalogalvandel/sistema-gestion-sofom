import streamlit as st
import pandas as pd
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
# 1. RECALCULO DE DATOS (PARA QUE NO FALTE LA VARIABLE)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=60)
def obtener_datos_contables():
    res_s = supabase.table("socios").select("*").eq("estatus", "ACTIVO").execute()
    res_a = supabase.table("aportaciones_socios").select("*").execute()
    
    socios = res_s.data if res_s.data else []
    aports = res_a.data if res_a.data else []
    
    df_soc = pd.DataFrame(socios)
    df_apo = pd.DataFrame(aports)
    
    cap_table = []
    total_fondo = 0.0
    
    # Calcular aportado por socio
    for _, row in df_soc.iterrows():
        movs = df_apo[df_apo["id_socio"] == row["id_socio"]]
        aportado = float(movs[movs["tipo_movimiento"] == "APORTACION"]["monto"].sum() - 
                         movs[movs["tipo_movimiento"] == "RETIRO"]["monto"].sum())
        total_fondo += aportado
        cap_table.append({**row.to_dict(), "aportado": aportado})
        
    df_cap = pd.DataFrame(cap_table)
    if total_fondo > 0:
        df_cap["Porcentaje (%)"] = round((df_cap["aportado"] / total_fondo) * 100, 2)
    else:
        df_cap["Porcentaje (%)"] = 0.0
        
    return df_cap

df_cap_table = obtener_datos_contables()

# -----------------------------------------------------------------------------
# 2. LÓGICA DE PDF
# -----------------------------------------------------------------------------
class ContratoPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'CONTRATO DE ASOCIACIÓN EN PARTICIPACIÓN', 0, 1, 'C')
        self.ln(10)

def generar_pdf_asociacion(socio_nombre, socio_rfc, monto, porcentaje, vigencia):
    pdf = ContratoPDF()
    pdf.add_page()
    pdf.set_font('Arial', '', 11)
    def clean(t): return str(t).encode('latin-1', 'replace').decode('latin-1')
    
    texto = f"""
CONTRATO DE ASOCIACIÓN EN PARTICIPACIÓN celebrado entre "LA ASOCIANTE" (LA SOFOM E.N.R.) y "EL ASOCIADO" {socio_nombre.upper()}, RFC {socio_rfc.upper()}.

PRIMERA.- OBJETO. "EL ASOCIADO" entrega ${monto:,.2f} MXN para fondeo de microcrédito.
SEGUNDA.- PARTICIPACIÓN. "EL ASOCIADO" percibirá {porcentaje}% del rendimiento neto quincenal.
TERCERA.- NATURALEZA. Acuerdo de participación en resultados, no constituye relación laboral.
CUARTA.- VIGENCIA. {vigencia} meses.
    """
    pdf.multi_cell(0, 6, clean(texto))
    return pdf.output()

# -----------------------------------------------------------------------------
# 3. INTERFAZ
# -----------------------------------------------------------------------------
titulo_seccion("personas", "1. Selección de Inversionista")

if df_cap_table.empty:
    st.info("No hay socios registrados.")
else:
    opciones = {f"{r['nombre_completo']} ({r['rfc']})": r for r in df_cap_table.to_dict('records')}
    seleccion = st.selectbox("Seleccionar Socio:", options=list(opciones.keys()))
    datos_s = opciones[seleccion]

    titulo_seccion("documento_check", "2. Parámetros del Contrato")
    with st.form("form_contrato"):
        c1, c2 = st.columns(2)
        # Usamos los datos calculados de df_cap_table
        monto = c1.number_input("Capital aportado ($):", value=float(datos_s['aportado']), disabled=True)
        pct = c2.number_input("Porcentaje de participación (%):", value=float(datos_s['Porcentaje (%)']), disabled=True)
        vigencia = st.number_input("Vigencia (meses):", value=12)
        
        if st.form_submit_button("Generar Contrato PDF", use_container_width=True):
            pdf_bytes = generar_pdf_asociacion(datos_s["nombre_completo"], datos_s["rfc"], monto, pct, vigencia)
            st.session_state["contrato_socio"] = bytes(pdf_bytes)
            dictamen("exito", "Contrato Generado", "Listo para descarga.")

if "contrato_socio" in st.session_state:
    st.download_button("📥 Descargar PDF", data=st.session_state["contrato_socio"], file_name=f"Contrato_{datos_s['rfc']}.pdf", mime="application/pdf", use_container_width=True)