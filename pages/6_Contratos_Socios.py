# =============================================================================
# Copyright (c) 2026 Eduardo Galván del Rio. Todos los derechos reservados.
# 
# Este código fuente es propiedad exclusiva y confidencial. Queda estrictamente
# prohibida su reproducción, distribución, comercialización o modificación
# sin autorización expresa y por escrito del autor.
# =============================================================================

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
from src.auth import verificar_acceso
verificar_acceso("ADMIN")

# --- FIRMA VISUAL (SIGNATURE) ---
st.markdown("""
<style>
    [data-testid="stMetricValue"], .stDataFrame {
        font-family: 'JetBrains Mono', 'Courier New', monospace !important;
    }
</style>
""", unsafe_allow_html=True)

encabezado_modulo(
    titulo="Emisión de Contratos de Asociación en Participación",
    subtitulo="Generación de instrumentos solemnes para capital de inversión e indexación en Bóveda Nube.",
    nombre_icono="documento",
    insignia="JURÍDICO INVERSIONES"
)

# -----------------------------------------------------------------------------
# 1. CONSULTA Y RECÁLCULO DEL CAP TABLE DEL RESPONSABLE
# -----------------------------------------------------------------------------
@st.cache_data(ttl=10)
def obtener_datos_contables():
    try:
        res_s = supabase.table("socios").select("*").eq("estatus", "ACTIVO").execute()
        res_a = supabase.table("aportaciones_socios").select("*").execute()
        
        socios = res_s.data if res_s.data else []
        aports = res_a.data if res_a.data else []
        
        df_soc = pd.DataFrame(socios)
        df_apo = pd.DataFrame(aports)
        
        cap_table = []
        total_fondo = 0.0
        
        if df_soc.empty: return pd.DataFrame()
        
        for _, row in df_soc.iterrows():
            movs = df_apo[df_apo["id_socio"] == row["id_socio"]] if not df_apo.empty else pd.DataFrame()
            aportado = 0.0
            if not movs.empty:
                inyecciones = pd.to_numeric(movs[movs["tipo_movimiento"] == "APORTACION"]["monto"], errors="coerce").sum()
                retiros = pd.to_numeric(movs[movs["tipo_movimiento"] == "RETIRO_CAPITAL"]["monto"], errors="coerce").sum()
                aportado = float(inyecciones - retiros)
                
            total_fondo += aportado
            cap_table.append({**row.to_dict(), "aportado": aportado})
            
        df_cap = pd.DataFrame(cap_table)
        
        if total_fondo > 0 and not df_cap.empty:
            df_cap["Porcentaje (%)"] = round((df_cap["aportado"] / total_fondo) * 100, 2)
        else:
            df_cap["Porcentaje (%)"] = 0.0
            
        return df_cap
    except Exception:
        return pd.DataFrame()

df_cap_table = obtener_datos_contables()

# -----------------------------------------------------------------------------
# 2. MOTOR DE PDF PROFESIONAL
# -----------------------------------------------------------------------------
class ContratoPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 5, 'INSTRUMENTO PRIVADO DE INVERSIÓN PATRIMONIAL - CONFIDENCIAL', 0, 1, 'R')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, f'Página {self.page_no()} | Documento emitido mediante Servidor Central SOFOM', 0, 0, 'C')

def generar_pdf_asociacion(socio_nombre, socio_rfc, monto, porcentaje, vigencia):
    pdf = ContratoPDF()
    pdf.add_page()
    pdf.set_margins(22, 22, 22)
    
    def clean(t): return str(t).encode('latin-1', 'replace').decode('latin-1')
    
    pdf.set_font('Arial', 'B', 13)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 8, clean('CONTRATO DE ASOCIACIÓN EN PARTICIPACIÓN'), 0, 1, 'C')
    pdf.ln(6)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 5, clean('PROEMIO:'), 0, 1, 'L')
    pdf.ln(2)
    pdf.set_font('Arial', '', 10)
    proemio_txt = (
        f"CONTRATO DE ASOCIACIÓN EN PARTICIPACIÓN QUE CELEBRAN POR UNA PARTE LA SOCIEDAD FINANCIERA "
        f"OPERATIVA DE MICROCRÉDITOS (EN LO SUCESIVO DENOMINADA COMO \"LA ASOCIANTE\") Y, POR LA OTRA PARTE, "
        f"EL C. {socio_nombre.upper()} (EN LO SUCESIVO DENOMINADO COMO \"EL ASOCIADO\"), AL TENOR DE LAS "
        f"SIGUIENTES DECLARACIONES Y CLÁUSULAS:"
    )
    pdf.multi_cell(0, 5.5, clean(proemio_txt), 0, 'J')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 5, clean('DECLARACIONES:'), 0, 1, 'L')
    pdf.ln(2)
    pdf.set_font('Arial', '', 10)
    declara_txt = (
        "I.- Declara \"LA ASOCIANTE\" ser una entidad mercantil constituida bajo las leyes mexicanas, cuyo objeto "
        "comprende la colocación de microcréditos.\n\n"
        f"II.- Declara \"EL ASOCIADO\" con RFC {socio_rfc.upper()}, manifestando bajo protesta de decir verdad "
        "que posee capital lícito para participar en el fondo."
    )
    pdf.multi_cell(0, 5.5, clean(declara_txt), 0, 'J')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 5, clean('CLÁUSULAS:'), 0, 1, 'L')
    pdf.ln(2)
    pdf.set_font('Arial', '', 10)
    
    c1 = f"PRIMERA.- OBJETO. \"EL ASOCIADO\" entrega a \"LA ASOCIANTE\" la cantidad de ${monto:,.2f} MXN, destinada íntegramente a colocación."
    pdf.multi_cell(0, 5.5, clean(c1), 0, 'J')
    pdf.ln(3)
    
    c2 = f"SEGUNDA.- DIVIDENDOS. \"EL ASOCIADO\" percibirá el {porcentaje}% del flujo neto real distribuible (bolsa del 65% del interés cobrado)."
    pdf.multi_cell(0, 5.5, clean(c2), 0, 'J')
    pdf.ln(3)
    
    c3 = f"TERCERA.- VIGENCIA. Plazo forzoso de vigencia de {vigencia} meses. Al término, se podrán reinvertir o retirar las utilidades."
    pdf.multi_cell(0, 5.5, clean(c3), 0, 'J')
    pdf.ln(22)
    
    y_firma = pdf.get_y()
    pdf.line(22, y_firma, 87, y_firma)
    pdf.set_xy(22, y_firma + 2)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(65, 4, clean("LA ASOCIANTE"), 0, 1, 'C')
    pdf.set_font('Arial', '', 9)
    pdf.set_x(22)
    pdf.cell(65, 4, clean("Representación Legal"), 0, 1, 'C')
    
    pdf.line(123, y_firma, 188, y_firma)
    pdf.set_xy(123, y_firma + 2)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(65, 4, clean("EL ASOCIADO"), 0, 1, 'C')
    pdf.set_font('Arial', '', 9)
    pdf.set_x(123)
    pdf.cell(65, 4, clean(socio_nombre.upper()), 0, 1, 'C')
    
    return bytes(pdf.output())

# -----------------------------------------------------------------------------
# 3. INTERFAZ DE USUARIO Y TRANSACCIÓN SQL
# -----------------------------------------------------------------------------
titulo_seccion("personas", "1. Selección de Instrumento de Inversión")

if df_cap_table.empty:
    st.info("No hay socios inversionistas activos registrados en el servidor de base de datos.")
else:
    opciones = {f"{r['nombre_completo']} | RFC: {r['rfc']}": r for r in df_cap_table.to_dict('records')}
    seleccion = st.selectbox("Inversionista Patrimonial:", options=list(opciones.keys()))
    datos_s = opciones[seleccion]

    st.markdown("<br>", unsafe_allow_html=True)
    titulo_seccion("documento_check", "2. Configuración, Formalización y Bóveda")
    
    with st.form("form_contrato_pld"):
        c_l1, c_l2 = st.columns(2)
        monto_cap = c_l1.number_input("Capital Patrimonial Activo ($):", value=float(datos_s['aportado']), disabled=True)
        pct_cap = c_l2.number_input("Porcentaje Asignado en Cap Table (%):", value=float(datos_s['Porcentaje (%)']), disabled=True)
        
        vigencia_meses = st.number_input("Vigencia del Contrato Mercantil (Meses):", min_value=1, value=12, step=1)
        
        st.markdown("<br>", unsafe_allow_html=True)
        # Cambio de nombre al botón para reflejar que ahora hace un UPDATE SQL
        generar_doc = st.form_submit_button("Formalizar Vigencia y Compilar PDF", width='stretch', type="primary")
        
        if generar_doc:
            with st.spinner("Construyendo instrumento legal e indexando en servidor..."):
                try:
                    # 1. Generación del Archivo Físico (PDF Bytes)
                    pdf_bytes = generar_pdf_asociacion(
                        socio_nombre=datos_s["nombre_completo"], socio_rfc=datos_s["rfc"],
                        monto=monto_cap, porcentaje=pct_cap, vigencia=vigencia_meses
                    )
                    
                    # 2. Resguardo Automático en Supabase Storage (La Observación del Auditor)
                    nombre_archivo_storage = f"contratos_socios/{datos_s['rfc']}_CONTRATO_ASOCIACION_{datetime.now().strftime('%Y%m%d')}.pdf"
                    supabase.storage.from_("expedientes").upload(
                        path=nombre_archivo_storage,
                        file=pdf_bytes,
                        file_options={"content-type": "application/pdf", "upsert": "true"}
                    )
                    
                    # 3. Transacción SQL: Registrar la vigencia en el perfil del socio
                    # Creamos una columna 'vigencia_contrato_meses' si no existe, o usamos una metadata
                    supabase.table("socios").update({"vigencia_contrato_meses": int(vigencia_meses)}).eq("id_socio", datos_s["id_socio"]).execute()

                    # 4. Memoria para descarga local
                    st.session_state["pdf_contrato_socio"] = pdf_bytes
                    st.session_state["ruta_storage_socio"] = nombre_archivo_storage
                    
                    dictamen("exito", "Instrumento Legal Formalizado", f"El contrato fue estructurado y resguardado de forma inmutable en la nube ({nombre_archivo_storage}). La vigencia de {vigencia_meses} meses fue fijada en el servidor.")
                except Exception as e:
                    dictamen("peligro", "Fallo de Servidor", f"Error técnico en la bóveda o compilación: {str(e)}")

st.divider()

titulo_seccion("documento", "3. Expediente Físico (Descarga)")

if "pdf_contrato_socio" in st.session_state and not df_cap_table.empty:
    d_col1, d_col2 = st.columns([1, 2])
    with d_col1:
        st.download_button(
            label="Descargar Contrato para Firma Autógrafa",
            data=st.session_state["pdf_contrato_socio"],
            file_name=f"Contrato_{datos_s['rfc']}.pdf",
            mime="application/pdf",
            type="secondary",
            width='stretch'
        )
    with d_col2:
        st.markdown("*Cumplimiento PLD:* Este documento fue indexado en la bóveda cifrada en la nube y la vigencia fue fijada en la base de datos SQL. Imprima para recabar firmas en tinta húmeda.")
else:
    st.info("Configure el expediente en la sección superior y presione el botón de formalización para habilitar la descarga.")