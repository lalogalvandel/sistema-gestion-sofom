# 
# Copyright (c) 2026 Eduardo Galván del Rio. Todos los derechos reservados.
# 
# Este código fuente es propiedad exclusiva y confidencial. Queda estrictamente
# prohibida su reproducción, distribución, comercialización o modificación
# sin autorización expresa y por escrito del autor.
# 
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
from src.auth import verificar_acceso
verificar_acceso("ADMIN")
encabezado_modulo(
    titulo="Emisión de Contratos de Asociación en Participación",
    subtitulo="Generación de instrumentos mercantiles solemnes para la formalización del capital de inversión.",
    nombre_icono="documento",
    insignia="JURÍDICO INVERSIONES"
)

# -----------------------------------------------------------------------------
# 1. CONSULTA Y RECÁLCULO DEL CAP TABLE DEL RESPONSABLE
# -----------------------------------------------------------------------------
@st.cache_data(ttl=30)
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
        
        for _, row in df_soc.iterrows():
            movs = df_apo[df_apo["id_socio"] == row["id_socio"]] if not df_apo.empty else pd.DataFrame()
            aportado = 0.0
            if not movs.empty:
                aportado = float(movs[movs["tipo_movimiento"] == "APORTACION"]["monto"].sum() - 
                                 movs[movs["tipo_movimiento"] == "RETIRO"]["monto"].sum())
            total_fondo += aportado
            cap_table.append({**row.to_dict(), "aportado": aportado})
            
        df_cap = pd.DataFrame(cap_table) if cap_table else pd.DataFrame(columns=["id_socio", "nombre_completo", "rfc", "cuenta_clabe", "aportado"])
        
        if total_fondo > 0 and not df_cap.empty:
            df_cap["Porcentaje (%)"] = round((df_cap["aportado"] / total_fondo) * 100, 2)
        else:
            df_cap["Porcentaje (%)"] = 0.0
            
        return df_cap
    except Exception:
        return pd.DataFrame()

df_cap_table = obtener_datos_contables()

# -----------------------------------------------------------------------------
# 2. MOTOR DE PDF PROFESIONAL CON MARGENES Y SECCIONES
# -----------------------------------------------------------------------------
class ContratoPDF(FPDF):
    def header(self):
        # Encabezado corporativo discreto
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
    pdf.set_margins(22, 22, 22) # Márgenes ejecutivos amplios
    
    def clean(t): return str(t).encode('latin-1', 'replace').decode('latin-1')
    
    # TÍTULO PRINCIPAL EN AZUL CORPORATIVO
    pdf.set_font('Arial', 'B', 13)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 8, clean('CONTRATO DE ASOCIACIÓN EN PARTICIPACIÓN'), 0, 1, 'C')
    pdf.ln(6)
    
    # PROEMIO
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 5, clean('PROEMIO:'), 0, 1, 'L')
    pdf.ln(2)
    pdf.set_font('Arial', '', 10)
    proemio_txt = (
        f"CONTRATO DE ASOCIACIÓN EN PARTICIPACIÓN QUE CELEBRAN POR UNA PARTE LA SOCIEDAD FINANCIERA "
        f"OPERATIVA DE MICROCRÉDITOS (EN LO SUCESIVO DENOMINADA COMO \"LA ASOCIANTE\") Y, POR LA OTRA PARTE, "
        f"EL C. {socio_nombre.upper()} (EN LO SUCESIVO DENOMINADO COMO \"EL ASOCIADO\"), AL TENOR DE LAS "
        f"SIGUIENTES DECLARACIONES Y CLÁUSULAS CONCILIADAS:"
    )
    pdf.multi_cell(0, 5.5, clean(proemio_txt), 0, 'J')
    pdf.ln(5)
    
    # DECLARACIONES
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 5, clean('DECLARACIONES:'), 0, 1, 'L')
    pdf.ln(2)
    pdf.set_font('Arial', '', 10)
    declara_txt = (
        "I.- Declara \"LA ASOCIANTE\" ser una entidad mercantil debidamente constituida bajo las leyes de la República Mexicana, "
        "cuyo objeto social principal comprende la colocación y administración de microcréditos productivos y soluciones financieras en el mercado retail.\n\n"
        f"II.- Declara \"EL ASOCIADO\" ser una persona física en pleno ejercicio de sus facultades legales, con Registro Federal de Contribuyentes "
        f"{socio_rfc.upper()}, manifestando bajo protesta de decir verdad que posee el capital lícito y suficiente para participar activamente en el fondo contable."
    )
    pdf.multi_cell(0, 5.5, clean(declara_txt), 0, 'J')
    pdf.ln(5)
    
    # CLÁUSULAS
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 5, clean('CLÁUSULAS:'), 0, 1, 'L')
    pdf.ln(2)
    pdf.set_font('Arial', '', 10)
    
    c1 = f"PRIMERA.- OBJETO DE LA APORTACIÓN. \"EL ASOCIADO\" entrega formalmente a \"LA ASOCIANTE\" la cantidad líquida de ${monto:,.2f} MXN (Moneda Nacional). Dicho capital será destinado de forma íntegra e inmediata al pool transaccional de colocación de microcréditos de la firma."
    pdf.multi_cell(0, 5.5, clean(c1), 0, 'J')
    pdf.ln(4)
    
    c2 = f"SEGUNDA.- ASIGNACIÓN DE DIVIDENDOS Y RENDIMIENTOS. \"EL ASOCIADO\" tendrá el derecho inalienable de percibir el {porcentaje}% del flujo neto real distribuible recaudado en caja quincenalmente (bolsa del 65% del interés cobrado y el capital recuperado en ventanilla), liquidado automáticamente según el Cap Table del servidor."
    pdf.multi_cell(0, 5.5, clean(c2), 0, 'J')
    pdf.ln(4)
    
    c3 = "TERCERA.- EXCLUSIÓN DE ASOCIACIÓN LABORAL. Las partes ratifican que este instrumento se rige exclusivamente por las leyes mercantiles vigentes en México. No constituye de ninguna forma subordinación laboral, sociedad comercial externa ni copropiedad sobre los activos fijos de la entidad financiera."
    pdf.multi_cell(0, 5.5, clean(c3), 0, 'J')
    pdf.ln(4)
    
    c4 = f"CUARTA.- VIGENCIA Y RENOVACIÓN. El presente acuerdo mercantil surtirá efectos a partir de su suscripción y mantendrá un plazo forzoso de vigencia de {vigencia} meses. Al término del periodo, las utilidades podrán ser reinvertidas al capital principal o retiradas mediante orden expresa."
    pdf.multi_cell(0, 5.5, clean(c4), 0, 'J')
    pdf.ln(22)
    
    # BLOQUE DE FIRMAS PERFECTAMENTE ALINEADO
    y_firma = pdf.get_y()
    
    # Firma Izquierda: La SOFOM
    pdf.line(22, y_firma, 87, y_firma)
    pdf.set_xy(22, y_firma + 2)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(65, 4, clean("LA ASOCIANTE"), 0, 1, 'C')
    pdf.set_font('Arial', '', 9)
    pdf.set_x(22)
    pdf.cell(65, 4, clean("Representación Legal SOFOM"), 0, 1, 'C')
    
    # Firma Derecha: El Inversionista
    pdf.line(123, y_firma, 188, y_firma)
    pdf.set_xy(123, y_firma + 2)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(65, 4, clean("EL ASOCIADO"), 0, 1, 'C')
    pdf.set_font('Arial', '', 9)
    pdf.set_x(123)
    pdf.cell(65, 4, clean(socio_nombre.upper()), 0, 1, 'C')
    
    return pdf.output()

# -----------------------------------------------------------------------------
# 3. INTERFAZ DE USUARIO CON GRIDS INSTITUCIONALES
# -----------------------------------------------------------------------------
titulo_seccion("personas", "1. Selección de Instrumento de Inversión")

if df_cap_table.empty:
    st.info("No hay socios inversionistas activos registrados en el servidor de base de datos.")
else:
    # Compilar catálogo dinámico
    opciones = {f"{r['nombre_completo']} | RFC: {r['rfc']}": r for r in df_cap_table.to_dict('records')}
    seleccion = st.selectbox("Inversionista Patrimonial:", options=list(opciones.keys()))
    datos_s = opciones[seleccion]

    st.markdown("<br>", unsafe_allow_html=True)
    titulo_seccion("documento_check", "2. Revisión de Cláusulas y Datos Contractuales")
    
    with st.form("form_contrato_pld"):
        c_l1, c_l2 = st.columns(2)
        monto_cap = c_l1.number_input("Capital Patrimonial Activo ($):", value=float(datos_s['aportado']), disabled=True)
        pct_cap = c_l2.number_input("Porcentaje Asignado en Cap Table (%):", value=float(datos_s['Porcentaje (%)']), disabled=True)
        
        vigencia_meses = st.number_input("Vigencia del Contrato Mercantil (Meses):", min_value=1, value=12, step=1)
        
        st.markdown("<br>", unsafe_allow_html=True)
        generar_doc = st.form_submit_button("Compilar Contrato Formal en PDF", use_container_width=True)
        
        if generar_doc:
            with st.spinner("Construyendo instrumento legal de inversión..."):
                try:
                    pdf_bytes = generar_pdf_asociacion(
                        socio_nombre=datos_s["nombre_completo"],
                        socio_rfc=datos_s["rfc"],
                        monto=monto_cap,
                        porcentaje=pct_cap,
                        vigencia=vigencia_meses
                    )
                    st.session_state["pdf_contrato_socio"] = bytes(pdf_bytes)
                    dictamen("exito", "Instrumento Legal Compilado", "El contrato de asociación ha sido estructurado conforme a la ley de sociedades mercantiles. Listo para firma.")
                except Exception as e:
                    dictamen("peligro", "Fallo de Compilación", f"Error técnico al estructurar el archivo PDF: {str(e)}")

st.divider()

titulo_seccion("documento", "3. Bóveda de Descarga y Formalización")

if "pdf_contrato_socio" in st.session_state and not df_cap_table.empty:
    st.info(f"Expediente jurídico generado exitosamente para: **{datos_s['nombre_completo']}**")
    
    d_col1, d_col2 = st.columns([1, 2])
    with d_col1:
        st.download_button(
            label="Descargar Contrato PDF",
            data=st.session_state["pdf_contrato_socio"],
            file_name=f"Contrato_Asociacion_{datos_s['rfc']}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
    with d_col2:
        st.markdown("*Cotejo Normativo:* Este documento integra las declaraciones obligatorias de prevención de lavado de dinero y la cláusula de exclusión de sociedad laboral. Debe imprimirse en duplicado para firmas físicas.")
else:
    st.info("Configure el expediente en la sección superior y presione el botón de compilación para habilitar el repositorio de descarga.")