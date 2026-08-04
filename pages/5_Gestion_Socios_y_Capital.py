# =============================================================================
# Copyright (c) 2026 Eduardo Galván del Río. Todos los derechos reservados.
# 
# Este código fuente es propiedad exclusiva y confidencial. Queda estrictamente
# prohibida su reproducción, distribución, comercialización o modificación
# sin autorización expresa y por escrito del autor.
# =============================================================================

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
    titulo="Gestión de Capital Social y Cuentas en Participación",
    subtitulo="Control contable de aportaciones, dispersión de flujo libre (Free Cash Flow) y bóveda KYC/PLD.",
    nombre_icono="billetera",
    insignia="FONDO PATRIMONIAL"
)

# -----------------------------------------------------------------------------
# 1. CONSULTA DE SOCIOS, APORTACIONES Y RENDIMIENTOS REALES (FLUJO DE CAJA)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=5)
def obtener_datos_patrimoniales():
    try:
        res_s = supabase.table("socios").select("*").execute()
        res_a = supabase.table("aportaciones_socios").select("*").execute()
        res_pld = supabase.table("expedientes_pld").select("*").execute()
        
        socios = res_s.data if res_s.data else []
        aportaciones = res_a.data if res_a.data else []
        pld_data = res_pld.data if res_pld.data else []
        
        df_soc = pd.DataFrame(socios) if socios else pd.DataFrame(columns=["id_socio", "nombre_completo", "rfc", "cuenta_clabe", "estatus"])
        df_apo = pd.DataFrame(aportaciones) if aportaciones else pd.DataFrame(columns=["id_socio", "monto", "tipo_movimiento"])
        df_pld = pd.DataFrame(pld_data) if pld_data else pd.DataFrame(columns=["id_socio", "ine_validado", "csf_sat_validado", "domicilio_validado", "contrato_firmado"])
        
        return df_soc, df_apo, df_pld
    except Exception:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=5)
def obtener_bolsa_dividendos_reales():
    """Calcula la utilidad REAL leyendo estrictamente la tabla de cobranza y comisiones (Dinero en caja)"""
    try:
        # Sumamos la utilidad generada por TODOS los pagos ingresados en Ventanilla
        res_c = supabase.table("cobranza_y_comisiones").select("utilidad_socios").execute()
        if not res_c.data: return 0.0
        
        df_c = pd.DataFrame(res_c.data)
        utilidad_historica = pd.to_numeric(df_c["utilidad_socios"], errors="coerce").sum()
        
        # Le restamos los dividendos que YA han sido retirados por los socios
        res_a = supabase.table("aportaciones_socios").select("monto").eq("tipo_movimiento", "RETIRO_DIVIDENDO").execute()
        dividendos_retirados = 0.0
        if res_a.data:
            df_a = pd.DataFrame(res_a.data)
            dividendos_retirados = pd.to_numeric(df_a["monto"], errors="coerce").sum()
            
        bolsa_disponible = utilidad_historica - dividendos_retirados
        return max(round(bolsa_disponible, 2), 0.0)
    except Exception:
        return 0.0

df_socios, df_aportaciones, df_pld = obtener_datos_patrimoniales()
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
            # Retiros de capital puro (no dividendos)
            retiros = pd.to_numeric(movs[movs["tipo_movimiento"] == "RETIRO_CAPITAL"]["monto"], errors="coerce").sum()
            aportado = float(inyecciones - retiros)
            
        # Revisamos el estatus PLD para ver si está bloqueado
        estatus_pld_texto = "BLOQUEADO (PLD)"
        pld_socio = df_pld[df_pld["id_socio"] == id_s] if not df_pld.empty else pd.DataFrame()
        if not pld_socio.empty:
            s_pld = pld_socio.iloc[0]
            if s_pld.get("ine_validado") and s_pld.get("csf_sat_validado") and s_pld.get("domicilio_validado") and s_pld.get("contrato_firmado"):
                estatus_pld_texto = "AL CORRIENTE"
            
        capital_total_fondo += aportado
        cap_table.append({
            "id_socio": id_s,
            "Nombre del Socio": row.get("nombre_completo", "Sin Nombre"),
            "RFC": row.get("rfc", "SIN-RFC"),
            "Estatus PLD": estatus_pld_texto,
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
with c1: tarjeta_kpi("billetera", "Capital Social Total Aportado", f"${capital_total_fondo:,.2f}", "Suma de aportaciones vigentes", "marino_800")
with c2: tarjeta_kpi("personas", "Socios Inversionistas Activos", f"{num_socios} socios", "Inversionistas del Cap Table", "azul_600")

st.markdown("<br>", unsafe_allow_html=True)
c3, c4 = st.columns(2)
with c3: tarjeta_kpi("banco", "Bolsa de Dividendos (Real en Caja)", f"${bolsa_dividendos_disponibles:,.2f}", "Flujo de utilidades ya recaudado de la calle", "dorado_600")
with c4: tarjeta_kpi("escudo", "Modelo de Participación", "Proporcional", "Reparto con candado PLD activado", "verde_lago")

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
        st.dataframe(df_ver[["Nombre del Socio", "RFC", "Capital Aportado ($)", "Porcentaje (%)", "Estatus PLD"]], width="stretch")
    else:
        st.info("No hay socios registrados en el servidor.")

with col_gestion:
    titulo_seccion("caja", "3. Tesorería Societaria")
    pestaña_alta, pestaña_mov = st.tabs(["➕ Alta de Inversionista", "💵 Movimiento de Capital"])
    
    with pestaña_alta:
        with st.form("form_alta_socio"):
            nom_s = st.text_input("Nombre Completo:")
            rfc_s = st.text_input("RFC con Homoclave:")
            clabe_s = st.text_input("Cuenta CLABE:")
            apo_ini = st.number_input("Aportación Inicial ($ MXN):", min_value=1000.0, value=50000.0, step=5000.0)
            
            if st.form_submit_button("Registrar en Cap Table", width="stretch"):
                try:
                    payload_socio = {"nombre_completo": nom_s, "rfc": rfc_s, "cuenta_clabe": clabe_s, "estatus": "ACTIVO"}
                    supabase.table("socios").upsert(payload_socio, on_conflict="rfc").execute()
                    
                    res_bus = supabase.table("socios").select("id_socio").eq("rfc", rfc_s).execute()
                    id_new = res_bus.data[0]["id_socio"] if res_bus.data else None
                        
                    if id_new:
                        supabase.table("aportaciones_socios").insert({"id_socio": id_new, "monto": apo_ini, "tipo_movimiento": "APORTACION"}).execute()
                        st.toast("✅ Inversionista registrado y fondeado.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error SQL: {str(e)}")

    with pestaña_mov:
        with st.form("form_mov_capital"):
            if not df_cap_table.empty:
                mapa_opciones = {f"{r['Nombre del Socio']} ({r['RFC']})": r["id_socio"] for r in cap_table}
                sel_socio_mov = st.selectbox("Inversionista:", options=list(mapa_opciones.keys()))
                tipo_m = st.radio("Movimiento Patrimonial:", ["APORTACION", "RETIRO_CAPITAL"], horizontal=True)
                monto_m = st.number_input("Monto ($ MXN):", min_value=100.0, value=10000.0, step=1000.0)
                
                if st.form_submit_button("Asentar Movimiento", width="stretch"):
                    try:
                        id_target = mapa_opciones[sel_socio_mov]
                        supabase.table("aportaciones_socios").insert({"id_socio": id_target, "monto": monto_m, "tipo_movimiento": tipo_m}).execute()
                        st.toast(f"✅ Movimiento de {tipo_m} asentado en tesorería.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error SQL: {str(e)}")
            else:
                st.info("Registre un socio primero.")

st.divider()

# -----------------------------------------------------------------------------
# 5. DISPERSIÓN DE DIVIDENDOS (CON CANDADO PLD ACTIVADO)
# -----------------------------------------------------------------------------
titulo_seccion("porcentaje", "4. Calculadora y Dispersión de Dividendos")

if not df_cap_table.empty and bolsa_dividendos_disponibles > 0.01:
    st.markdown(f"Flujo libre en caja para dispersión: **${bolsa_dividendos_disponibles:,.2f} MXN**. Se aplicará bloqueo normativo (Retención) a los socios con expediente PLD incompleto.")
    
    # Construcción de la matriz de pago
    matriz_pago = []
    total_a_dispersar_hoy = 0.0
    
    for socio in cap_table:
        dividendo_bruto = round((socio["Porcentaje (%)"] / 100.0) * bolsa_dividendos_disponibles, 2)
        bloqueado = socio["Estatus PLD"] != "AL CORRIENTE"
        monto_liberado = 0.0 if bloqueado else dividendo_bruto
        total_a_dispersar_hoy += monto_liberado
        
        matriz_pago.append({
            "id_socio": socio["id_socio"],
            "Inversionista": socio["Nombre del Socio"],
            "Estatus Normativo": socio["Estatus PLD"],
            "Dividendo Generado": f"${dividendo_bruto:,.2f}",
            "Monto a Liberar": f"${monto_liberado:,.2f}",
            "_monto_raw": monto_liberado # Variable invisible para inyección SQL
        })
        
    df_reparto = pd.DataFrame(matriz_pago)
    st.dataframe(df_reparto.drop(columns=["id_socio", "_monto_raw"]), width="stretch")
    
    if total_a_dispersar_hoy > 0:
        c_disp1, c_disp2 = st.columns([1, 2])
        with c_disp1:
            st.metric("Total de Emisión Aprobada", f"${total_a_dispersar_hoy:,.2f}")
        with c_disp2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Ejecutar Transferencia y Asentar Retiro de Utilidades", type="primary"):
                with st.spinner("Procesando pólizas de dispersión..."):
                    payload_masivo = []
                    for fila in matriz_pago:
                        if fila["_monto_raw"] > 0:
                            payload_masivo.append({
                                "id_socio": fila["id_socio"],
                                "monto": fila["_monto_raw"],
                                "tipo_movimiento": "RETIRO_DIVIDENDO"
                            })
                    
                    if payload_masivo:
                        try:
                            supabase.table("aportaciones_socios").insert(payload_masivo).execute()
                            st.success(f"¡Dispersión Exitosa! Se ha asentado el retiro de ${total_a_dispersar_hoy:,.2f} MXN de la caja de dividendos.")
                            st.rerun()
                        except Exception as e_disp:
                            st.error(f"Fallo contable: {str(e_disp)}")
    else:
        dictamen("peligro", "Bloqueo Operativo", "El 100% del Cap Table se encuentra bloqueado por incumplimiento PLD. Regularice los expedientes en la sección 5.")

elif df_cap_table.empty:
    st.info("No hay socios registrados en el Cap Table.")
else:
    st.info("Actualmente la bolsa de utilidades es de $0.00 MXN. Conforme los deudores paguen sus intereses reales en Ventanilla, este fondo se alimentará.")

st.divider()

# -----------------------------------------------------------------------------
# 5. BÓVEDA LEGAL PLD Y EXPEDIENTE DE CUMPLIMIENTO (KYC)
# -----------------------------------------------------------------------------
titulo_seccion("documento_check", "5. Bóveda Legal PLD y Expediente de Cumplimiento")

st.markdown("""
En cumplimiento con las Disposiciones Generales en materia de PLD/CFT, todo inversionista debe integrar su expediente legal antes de la dispersión de utilidades.
""")

if not df_cap_table.empty:
    mapa_socios = {f"{r['Nombre del Socio']} | RFC: {r['RFC']}": r["id_socio"] for r in cap_table}
    socio_pld_sel = st.selectbox("Expediente en Mesa de Control PLD:", options=list(mapa_socios.keys()))
    
    id_socio_target = mapa_socios[socio_pld_sel]
    nombre_clean = socio_pld_sel.split('|')[0].strip()
    rfc_clean = socio_pld_sel.split('|')[1].replace('RFC:', '').strip()
    
    # Extraemos el estatus directo del DataFrame cacheado para no hacer llamadas extra
    pld_socio = df_pld[df_pld["id_socio"] == id_socio_target]
    val_ine, val_csf, val_dom, val_con = False, False, False, False
    notas_actuales = "Expediente en proceso de revisión."
    
    if not pld_socio.empty:
        s = pld_socio.iloc[0]
        val_ine = bool(s.get("ine_validado", False))
        val_csf = bool(s.get("csf_sat_validado", False))
        val_dom = bool(s.get("domicilio_validado", False))
        val_con = bool(s.get("contrato_firmado", False))
        notas_actuales = str(s.get("notas_auditoria", notas_actuales))
    
    st.divider()
    
    col_checklist, col_carga = st.columns([1.1, 1.3])
    
    with col_checklist:
        st.markdown(f"**Matriz de Validación Normativa: {nombre_clean}**")
        
        with st.form("form_checklist_pld"):
            chk_ine = st.checkbox("Identificación Oficial Vigente (Cotejada)", value=val_ine)
            chk_csf = st.checkbox("Constancia de Situación Fiscal (SAT)", value=val_csf)
            chk_dom = st.checkbox("Comprobante de Domicilio Legal", value=val_dom)
            chk_con = st.checkbox("Contrato de Participación Firmado", value=val_con)
            
            notas_auditoria = st.text_area("Dictamen del Oficial de Cumplimiento:", value=notas_actuales, height=100)
            
            btn_guardar_checklist = st.form_submit_button("Actualizar Estatus de Auditoría", type="primary", width="stretch")
            
            if btn_guardar_checklist:
                with st.spinner("Registrando validación..."):
                    try:
                        payload_checklist = {
                            "id_socio": id_socio_target, "ine_validado": chk_ine,
                            "csf_sat_validado": chk_csf, "domicilio_validado": chk_dom,
                            "contrato_firmado": chk_con, "notas_auditoria": notas_auditoria
                        }
                        supabase.table("expedientes_pld").upsert(payload_checklist).execute()
                        st.success("Matriz de validación actualizada. Recargue para reflejar en el Cap Table.")
                        st.rerun()
                    except Exception as e_chk:
                        st.error(f"Error al actualizar el checklist: {str(e_chk)}")
        
    with col_carga:
        st.markdown("**Ingesta de Documentos Institucionales**")
        with st.form("form_carga_pld"):
            tipo_doc_pld = st.selectbox("Clasificación del Documento:", ["Identificación Oficial", "Constancia de Situación Fiscal", "Comprobante de Domicilio", "Contrato / Origen de Recursos"])
            archivo_pld = st.file_uploader("Seleccione archivo (PDF, JPG):", type=["pdf", "png", "jpg"])
            st.markdown("<br>", unsafe_allow_html=True)
            btn_subir_pld = st.form_submit_button("Subir Archivo a Bóveda Nube", width="stretch")
            
        if btn_subir_pld and archivo_pld:
            with st.spinner("Transmitiendo archivo cifrado..."):
                try:
                    prefijo_doc = tipo_doc_pld.split('(')[0].strip().replace(" ", "_").lower()
                    nombre_storage = f"pld_socios/{rfc_clean}/{prefijo_doc}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                    
                    supabase.storage.from_("expedientes").upload(path=nombre_storage, file=archivo_pld.getvalue(), file_options={"content-type": archivo_pld.type, "upsert": "true"})
                    dictamen("exito", "Archivo Indexado", f"El documento fue resguardado en la ruta: {nombre_storage}.")
                except Exception as e_storage:
                    dictamen("peligro", "Alerta de Almacenamiento", f"Fallo en Storage: {str(e_storage)}.")