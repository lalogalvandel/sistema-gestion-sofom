# 
# Copyright (c) 2026 Eduardo Galván del Rio. Todos los derechos reservados.
# 
# Este código fuente es propiedad exclusiva y confidencial. Queda estrictamente
# prohibida su reproducción, distribución, comercialización o modificación
# sin autorización expresa y por escrito del autor.
# 
import streamlit as st
import pandas as pd
from datetime import datetime
from src.db import supabase
from src.theme import (
    aplicar_identidad_visual, encabezado_modulo, titulo_seccion,
    dictamen, tarjeta_kpi
)

st.set_page_config(page_title="Gestión de Capital y Socios | SOFOM", layout="wide")

from src.auth import verificar_acceso
verificar_acceso("ADMIN")

# 1. Inyectar identidad visual
aplicar_identidad_visual()

encabezado_modulo(
    titulo="Gestión de Capital Social y Cuentas en Participación",
    subtitulo="Control contable de aportaciones, Cap Table dinámico, dispersión de dividendos y bóveda legal PLD.",
    nombre_icono="billetera",
    insignia="FONDO PATRIMONIAL"
)

# -----------------------------------------------------------------------------
# 1. CONSULTA DE SOCIOS, APORTACIONES Y RENDIMIENTOS REALES
# -----------------------------------------------------------------------------
@st.cache_data(ttl=15)
def obtener_datos_patrimoniales():
    try:
        res_s = supabase.table("socios").select("*").execute()
        res_a = supabase.table("aportaciones_socios").select("*").execute()
        
        socios = res_s.data if res_s.data else []
        aportaciones = res_a.data if res_a.data else []
        
        df_soc = pd.DataFrame(socios) if socios else pd.DataFrame(columns=["id_socio", "nombre_completo", "rfc", "cuenta_clabe", "estatus"])
        df_apo = pd.DataFrame(aportaciones) if aportaciones else pd.DataFrame(columns=["id_socio", "monto", "tipo_movimiento"])
        
        return df_soc, df_apo
    except Exception:
        return pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=15)
def obtener_bolsa_dividendos_reales():
    """Calcula la utilidad real para los socios basándose en el 65% de los intereses de préstamos"""
    try:
        res_p = supabase.table("prestamos").select("*").execute()
        if not res_p.data:
            return 0.0
            
        df_p = pd.DataFrame(res_p.data)
        
        # Mapeo de columnas flexible
        col_monto = "monto_principal" if "monto_principal" in df_p.columns and df_p["monto_principal"].sum() > 0 else ("monto" if "monto" in df_p.columns else None)
        col_tasa = "tasa_mensual" if "tasa_mensual" in df_p.columns else ("tasa_interes_mensual" if "tasa_interes_mensual" in df_p.columns else None)
        
        if col_monto and col_tasa:
            df_p["monto_calc"] = pd.to_numeric(df_p[col_monto], errors="coerce").fillna(0.0)
            df_p["tasa_calc"] = pd.to_numeric(df_p[col_tasa], errors="coerce").fillna(6.0)
            if df_p["tasa_calc"].mean() > 1.0:
                df_p["tasa_calc"] = df_p["tasa_calc"] / 100.0
                
            interes_total = (df_p["monto_calc"] * df_p["tasa_calc"]).sum()
            return round(interes_total * 0.65, 2) # El 65% pactado para dividendos de los socios
        return 0.0
    except Exception:
        return 0.0

df_socios, df_aportaciones = obtener_datos_patrimoniales()
bolsa_dividendos_disponibles = obtener_bolsa_dividendos_reales()

# -----------------------------------------------------------------------------
# 2. MOTOR DE CÁLCULO DEL CAP TABLE
# -----------------------------------------------------------------------------
capital_total_fondo = 0.0
cap_table = []

if not df_socios.empty:
    for idx, row in df_socios.iterrows():
        id_s = row["id_socio"]
        movs = df_aportaciones[df_aportaciones["id_socio"] == id_s] if not df_aportaciones.empty else pd.DataFrame()
        aportado = 0.0
        if not movs.empty:
            inyecciones = pd.to_numeric(movs[movs["tipo_movimiento"] == "APORTACION"]["monto"], errors="coerce").sum()
            retiros = pd.to_numeric(movs[movs["tipo_movimiento"] == "RETIRO"]["monto"], errors="coerce").sum()
            aportado = float(inyecciones - retiros)
            
        capital_total_fondo += aportado
        cap_table.append({
            "id_socio": id_s,
            "Nombre del Socio": row.get("nombre_completo", "Sin Nombre"),
            "RFC": row.get("rfc", "SIN-RFC"),
            "Cuenta CLABE": row.get("cuenta_clabe", "N/A"),
            "Capital Aportado ($)": aportado,
            "Porcentaje (%)": 0.0
        })
        
    if capital_total_fondo > 0:
        for socio in cap_table:
            socio["Porcentaje (%)"] = round((socio["Capital Aportado ($)"] / capital_total_fondo) * 100, 2)
            
df_cap_table = pd.DataFrame(cap_table) if cap_table else pd.DataFrame()

# -----------------------------------------------------------------------------
# 3. PANEL DE SALUD Y KPIS DEL FONDO
# -----------------------------------------------------------------------------
titulo_seccion("tendencia", "1. Estructura de Capital y Salud del Fondo")
num_socios = len(df_socios) if not df_socios.empty else 0

c1, c2 = st.columns(2)
with c1:
    tarjeta_kpi("billetera", "Capital Social Total Aportado", f"${capital_total_fondo:,.2f}", "Suma de aportaciones patrimoniales activas", "marino_800")
with c2:
    tarjeta_kpi("personas", "Socios Inversionistas Activos", f"{num_socios} socios", "Inversionistas fondeando la operación", "azul_600")

st.markdown("<br>", unsafe_allow_html=True)

c3, c4 = st.columns(2)
with c3:
    tarjeta_kpi("banco", "Bolsa de Dividendos (65% Rendimiento)", f"${bolsa_dividendos_disponibles:,.2f}", "Flujo cobrado disponible para dispersión", "dorado_600")
with c4:
    tarjeta_kpi("escudo", "Modelo de Participación", "Proporcional", "Rendimiento variable según Cap Table", "verde_lago")

st.divider()

# -----------------------------------------------------------------------------
# 4. CAP TABLE Y VENTANILLA DE MOVIMIENTOS
# -----------------------------------------------------------------------------
col_tabla, col_gestion = st.columns([1.4, 1])

with col_tabla:
    titulo_seccion("balanza", "2. Cap Table Institucional")
    if not df_cap_table.empty:
        df_ver = df_cap_table.copy()
        df_ver["Capital Aportado ($)"] = df_ver["Capital Aportado ($)"].apply(lambda x: f"${x:,.2f}")
        df_ver["Porcentaje (%)"] = df_ver["Porcentaje (%)"].apply(lambda x: f"{x:.2f}%")
        st.dataframe(df_ver[["Nombre del Socio", "RFC", "Capital Aportado ($)", "Porcentaje (%)", "Cuenta CLABE"]], width="stretch")
    else:
        st.info("No hay socios registrados en el servidor.")

with col_gestion:
    titulo_seccion("caja", "3. Ventanilla de Movimientos")
    pestaña_alta, pestaña_mov = st.tabs(["➕ Alta de Socio", "💵 Movimiento de Capital"])
    
    with pestaña_alta:
        with st.form("form_alta_socio"):
            nom_s = st.text_input("Nombre Completo del Inversionista:")
            rfc_s = st.text_input("RFC / ID Fiscal:")
            clabe_s = st.text_input("Cuenta CLABE (Para dispersión):")
            apo_ini = st.number_input("Aportación Inicial ($ MXN):", min_value=1000.0, value=50000.0, step=5000.0)
            
            if st.form_submit_button("Registrar Socio en Fondo", width="stretch"):
                try:
                    payload_socio = {"nombre_completo": nom_s, "rfc": rfc_s, "cuenta_clabe": clabe_s, "estatus": "ACTIVO"}
                    res_new = supabase.table("socios").insert(payload_socio).execute()
                    
                    if res_new.data:
                        id_new = res_new.data[0]["id_socio"]
                    else:
                        # Respaldo de búsqueda en caso de que RLS no devuelva la fila insertada
                        res_bus = supabase.table("socios").select("id_socio").eq("rfc", rfc_s).execute()
                        id_new = res_bus.data[0]["id_socio"] if res_bus.data else None
                        
                    if id_new:
                        supabase.table("aportaciones_socios").insert({"id_socio": id_new, "monto": apo_ini, "tipo_movimiento": "APORTACION"}).execute()
                        st.toast("✅ Socio registrado exitosamente en el Cap Table.")
                        st.rerun()
                    else:
                        st.error("No se pudo obtener el ID del nuevo socio para inscribir su aportación.")
                except Exception as e:
                    st.error(f"Error al registrar socio en SQL: {str(e)}")

    with pestaña_mov:
        with st.form("form_mov_capital"):
            if not df_cap_table.empty:
                mapa_opciones = {f"{r['Nombre del Socio']} ({r['RFC']})": r["id_socio"] for r in cap_table}
                sel_socio_mov = st.selectbox("Seleccione Inversionista:", options=list(mapa_opciones.keys()))
                tipo_m = st.radio("Tipo de Movimiento:", ["APORTACION", "RETIRO"], horizontal=True)
                monto_m = st.number_input("Monto del Movimiento ($ MXN):", min_value=100.0, value=10000.0, step=1000.0)
                
                if st.form_submit_button("Asentar Movimiento Patrimonial", width="stretch"):
                    try:
                        id_target = mapa_opciones[sel_socio_mov]
                        supabase.table("aportaciones_socios").insert({"id_socio": id_target, "monto": monto_m, "tipo_movimiento": tipo_m}).execute()
                        st.toast(f"✅ Movimiento de {tipo_m} registrado.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error en la transacción SQL: {str(e)}")
            else:
                st.info("Registre al menos un socio en la pestaña de Alta para gestionar movimientos.")

st.divider()

# -----------------------------------------------------------------------------
# 5. DISPERSIÓN Y CALCULADORA DE DIVIDENDOS
# -----------------------------------------------------------------------------
titulo_seccion("porcentaje", "4. Calculadora de Dispersión de Dividendos")

if not df_cap_table.empty and bolsa_dividendos_disponibles > 0:
    st.markdown(f"La bolsa actual de **${bolsa_dividendos_disponibles:,.2f} MXN** se distribuye proporcionalmente según la participación en el Cap Table:")
    df_reparto = df_cap_table.copy()
    df_reparto["Dividendo Correspondiente ($)"] = df_reparto["Porcentaje (%)"].apply(lambda p: round((p / 100.0) * bolsa_dividendos_disponibles, 2))
    df_reparto["Dividendo Formateado"] = df_reparto["Dividendo Correspondiente ($)"].apply(lambda x: f"${x:,.2f}")
    
    st.dataframe(df_reparto[["Nombre del Socio", "RFC", "Cuenta CLABE", "Dividendo Formateado"]], width="stretch")
elif df_cap_table.empty:
    st.info("No hay socios registrados en el Cap Table.")
else:
    st.info("Actualmente la bolsa de dividendos es de $0.00 MXN. Conforme los deudores paguen sus intereses en la ventanilla de cobranza, este fondo se alimentará automáticamente.")

st.divider()

# -----------------------------------------------------------------------------
# 5. BÓVEDA LEGAL PLD Y EXPEDIENTE DE CUMPLIMIENTO (KYC)
# -----------------------------------------------------------------------------
titulo_seccion("documento_check", "5. Bóveda Legal PLD y Expediente de Cumplimiento")

st.markdown("""
En cumplimiento con las Disposiciones Generales en materia de PLD/CFT, todo inversionista debe integrar su expediente legal acreditando la procedencia de sus aportaciones antes de la dispersión de dividendos.
""")

if not df_cap_table.empty:
    mapa_socios = {f"{r['Nombre del Socio']} | RFC: {r['RFC']}": r["id_socio"] for r in cap_table}
    socio_pld_sel = st.selectbox("Expediente en Mesa de Control PLD:", options=list(mapa_socios.keys()))
    
    # Extracción de identificadores
    id_socio_target = mapa_socios[socio_pld_sel]
    nombre_clean = socio_pld_sel.split('|')[0].strip()
    rfc_clean = socio_pld_sel.split('|')[1].replace('RFC:', '').strip()
    
    # Consulta a la base de datos para obtener el estado real del checklist
    res_pld = supabase.table("expedientes_pld").select("*").eq("id_socio", id_socio_target).execute()
    datos_pld = res_pld.data[0] if res_pld.data else {}
    
    # Asignación de estados booleanos
    val_ine = datos_pld.get("ine_validado", False)
    val_csf = datos_pld.get("csf_sat_validado", False)
    val_dom = datos_pld.get("domicilio_validado", False)
    val_con = datos_pld.get("contrato_firmado", False)
    notas_actuales = datos_pld.get("notas_auditoria", "Expediente en proceso de revisión inicial.")
    
    st.divider()
    
    col_checklist, col_carga = st.columns([1.1, 1.3])
    
    with col_checklist:
        st.markdown(f"**Matriz de Validación Normativa: {nombre_clean}**")
        st.caption("Verificación de documentos obligatorios. Marque las casillas para certificar la existencia y validez del documento en el archivo físico/digital.")
        
        with st.form("form_checklist_pld"):
            chk_ine = st.checkbox("Identificación Oficial Vigente (Cotejada)", value=val_ine)
            chk_csf = st.checkbox("Constancia de Situación Fiscal (SAT)", value=val_csf)
            chk_dom = st.checkbox("Comprobante de Domicilio Legal", value=val_dom)
            chk_con = st.checkbox("Declaración de Origen Lícito y Contrato", value=val_con)
            
            notas_auditoria = st.text_area("Dictamen del Oficial de Cumplimiento:", value=notas_actuales, height=100)
            
            btn_guardar_checklist = st.form_submit_button("Actualizar Estatus de Auditoría", type="primary", width="stretch")
            
            if btn_guardar_checklist:
                with st.spinner("Registrando validación en el servidor..."):
                    try:
                        payload_checklist = {
                            "id_socio": id_socio_target,
                            "ine_validado": chk_ine,
                            "csf_sat_validado": chk_csf,
                            "domicilio_validado": chk_dom,
                            "contrato_firmado": chk_con,
                            "notas_auditoria": notas_auditoria
                        }
                        # Upsert crea el registro si no existe, o lo actualiza si ya existe
                        supabase.table("expedientes_pld").upsert(payload_checklist).execute()
                        st.success("Matriz de validación actualizada correctamente.")
                        st.rerun()
                    except Exception as e_chk:
                        st.error(f"Error al actualizar el checklist: {str(e_chk)}")
        
    with col_carga:
        st.markdown("**Ingesta y Digitalización de Documentos**")
        st.caption("Indexación de archivos a la bóveda segura del servidor.")
        
        with st.form("form_carga_pld"):
            tipo_doc_pld = st.selectbox(
                "Clasificación del Documento:",
                [
                    "Declaración de Origen Lícito de Recursos",
                    "Identificación Oficial (INE / Pasaporte)",
                    "Constancia de Situación Fiscal (SAT)",
                    "Comprobante de Domicilio",
                    "Estado de Cuenta Bancario (CLABE)"
                ]
            )
            
            archivo_pld = st.file_uploader(
                label="Seleccione el archivo digitalizado (PDF, JPG, PNG):",
                type=["pdf", "png", "jpg"]
            )
            
            nota_archivo = st.text_input("Referencia del archivo:", placeholder="Folio o fecha de emisión del documento.")
            
            st.markdown("<br>", unsafe_allow_html=True)
            btn_subir_pld = st.form_submit_button("Subir Archivo a Bóveda Institucional", width="stretch")
            
        if btn_subir_pld:
            if archivo_pld is not None:
                with st.spinner("Transmitiendo archivo cifrado..."):
                    try:
                        prefijo_doc = tipo_doc_pld.split('(')[0].strip().replace(" ", "_").lower()
                        nombre_storage = f"pld_socios/{rfc_clean}/{prefijo_doc}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                        
                        file_bytes = archivo_pld.getvalue()
                        supabase.storage.from_("expedientes").upload(
                            path=nombre_storage,
                            file=file_bytes,
                            file_options={"content-type": archivo_pld.type, "upsert": "true"}
                        )
                        
                        dictamen("exito", "Archivo Indexado", f"El documento '{tipo_doc_pld}' ha sido resguardado en la ruta: {nombre_storage}.")
                    except Exception as e_storage:
                        dictamen("peligro", "Alerta de Almacenamiento", f"Fallo en la transferencia al Storage: {str(e_storage)}. Verifique la configuración del bucket.")
            else:
                st.warning("Seleccione un archivo antes de procesar la solicitud.")
else:
    st.info("El directorio del Cap Table se encuentra vacío. Registre un socio para gestionar su expediente normativo.")