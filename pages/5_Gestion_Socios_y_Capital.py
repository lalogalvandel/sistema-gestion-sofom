import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from src.db import supabase
from src.theme import (
    aplicar_identidad_visual, encabezado_modulo, titulo_seccion,
    dictamen, tarjeta_kpi
)

st.set_page_config(page_title="Gestión de Capital y Socios | SOFOM", layout="wide")

# 1. Inyectar identidad visual de alto contraste
aplicar_identidad_visual()

encabezado_modulo(
    titulo="Gestión de Capital Social y Cuentas en Participación",
    subtitulo="Control contable de aportaciones, Cap Table dinámico, dispersión de dividendos y bóveda legal PLD.",
    nombre_icono="billetera",
    insignia="FONDO PATRIMONIAL"
)

# -----------------------------------------------------------------------------
# FUNCIONES DE CONSULTA CONTABLE EN SERVIDOR (SUPABASE)
# -----------------------------------------------------------------------------
def obtener_socios_y_capital():
    try:
        res_s = supabase.table("socios").select("*").eq("estatus", "ACTIVO").execute()
        res_a = supabase.table("aportaciones_socios").select("*").execute()
        
        socios = res_s.data if res_s.data else []
        aportaciones = res_a.data if res_a.data else []
        
        df_soc = pd.DataFrame(socios) if socios else pd.DataFrame(columns=["id_socio", "nombre_completo", "rfc", "cuenta_clabe", "fecha_ingreso"])
        df_apo = pd.DataFrame(aportaciones) if aportaciones else pd.DataFrame(columns=["id_socio", "monto", "tipo_movimiento"])
        
        return df_soc, df_apo
    except Exception:
        return pd.DataFrame(), pd.DataFrame()

df_socios, df_aportaciones = obtener_socios_y_capital()

# Cálculo del Cap Table (Porcentaje de participación por socio)
capital_total_fondo = 0.0
cap_table = []

if not df_socios.empty:
    for idx, row in df_socios.iterrows():
        id_s = row["id_socio"]
        movs = df_aportaciones[df_aportaciones["id_socio"] == id_s] if not df_aportaciones.empty else pd.DataFrame()
        
        aportado = 0.0
        if not movs.empty:
            inyecciones = movs[movs["tipo_movimiento"] == "APORTACION"]["monto"].sum()
            retiros = movs[movs["tipo_movimiento"] == "RETIRO"]["monto"].sum()
            aportado = float(inyecciones - retiros)
            
        capital_total_fondo += aportado
        cap_table.append({
            "id_socio": id_s,
            "Nombre del Socio": row["nombre_completo"],
            "RFC": row["rfc"],
            "Cuenta CLABE": row["cuenta_clabe"],
            "Capital Aportado ($)": aportado,
            "Porcentaje (%)": 0.0 # Se calcula en el siguiente paso
        })
        
    # Asignar porcentajes exactos sobre el fondo total
    if capital_total_fondo > 0:
        for socio in cap_table:
            socio["Porcentaje (%)"] = round((socio["Capital Aportado ($)"] / capital_total_fondo) * 100, 2)
            
df_cap_table = pd.DataFrame(cap_table) if cap_table else pd.DataFrame()

# -----------------------------------------------------------------------------
# SECCIÓN 1: KPIs DEL FONDO PATRIMONIAL (CUADRÍCULA 2x2)
# -----------------------------------------------------------------------------
titulo_seccion("tendencia", "1. Estructura de Capital y Salud del Fondo")

num_socios = len(df_socios) if not df_socios.empty else 0
promedio_aportacion = (capital_total_fondo / num_socios) if num_socios > 0 else 0.0

# Consultar la bolsa acumulada de Flujo Real Socios en el Módulo de Cobranza
bolsa_dividendos_disponibles = 0.0
try:
    res_cob = supabase.table("cobranza_y_comisiones").select("utilidad_socios").execute()
    if res_cob.data:
        bolsa_dividendos_disponibles = float(pd.DataFrame(res_cob.data)["utilidad_socios"].sum())
except Exception:
    bolsa_dividendos_disponibles = 0.0

# Cuadrícula simétrica 2x2 sin cortes de texto
c1, c2 = st.columns(2)
with c1:
    tarjeta_kpi("billetera", "Capital Social Total Aportado", f"${capital_total_fondo:,.2f}", "Suma de aportaciones patrimoniales activas", "marino_800")
with c2:
    tarjeta_kpi("personas", "Socios Inversionistas Activos", f"{num_socios} socios", f"Aportación promedio: ${promedio_aportacion:,.2f} MXN", "azul_600")

st.markdown("<br>", unsafe_allow_html=True)

c3, c4 = st.columns(2)
with c3:
    tarjeta_kpi("banco", "Bolsa de Dividendos (65% + Cap)", f"${bolsa_dividendos_disponibles:,.2f}", "Flujo cobrado disponible para dispersión", "dorado_600")
with c4:
    tarjeta_kpi("escudo", "Modelo de Participación", "Proporcional", "Rendimiento variable según Cap Table (Sin riesgo de liquidez)", "verde_lago")

st.divider()

# -----------------------------------------------------------------------------
# SECCIÓN 2: CAP TABLE DINÁMICO Y REGISTRO DE APORTACIONES
# -----------------------------------------------------------------------------
col_tabla, col_gestion = st.columns([1.4, 1])

with col_tabla:
    titulo_seccion("balanza", "2. Cap Table Institucional (Participación al Día)")
    if not df_cap_table.empty:
        df_ver = df_cap_table.copy()
        df_ver["Capital Aportado ($)"] = df_ver["Capital Aportado ($)"].apply(lambda x: f"${x:,.2f}")
        df_ver["Porcentaje (%)"] = df_ver["Porcentaje (%)"].apply(lambda x: f"{x:.2f}%")
        st.dataframe(df_ver[["Nombre del Socio", "RFC", "Capital Aportado ($)", "Porcentaje (%)", "Cuenta CLABE"]], use_container_width=True)
    else:
        st.info("No hay socios registrados con capital activo. Utilice el formulario lateral para dar de alta al primer inversionista.")

with col_gestion:
    titulo_seccion("caja", "3. Ventanilla de Movimientos")
    
    pestaña_alta, pestaña_mov = st.tabs(["➕ Alta de Nuevo Socio", "💵 Aportación / Retiro"])
    
    with pestaña_alta:
        with st.form("form_alta_socio"):
            nom_s = st.text_input("Nombre Completo:", placeholder="Ej. Eduardo Galván del Río")
            rfc_s = st.text_input("RFC (con homoclave):", max_chars=13, placeholder="GALE900101XYZ").upper()
            clabe_s = st.text_input("Cuenta CLABE (18 dígitos):", max_chars=18, placeholder="012345678901234567")
            apo_ini = st.number_input("Aportación Inicial ($):", min_value=1000.0, value=50000.0, step=5000.0)
            
            crear_s = st.form_submit_button("Registrar Socio en Servidor", use_container_width=True)
            if crear_s:
                if not nom_s or len(rfc_s) < 12 or len(clabe_s) != 18:
                    st.error("Verifique que el RFC y los 18 dígitos de la cuenta CLABE sean correctos.")
                else:
                    with st.spinner("Creando expediente contable en Supabase..."):
                        try:
                            # Insertar socio
                            res_new = supabase.table("socios").insert({"nombre_completo": nom_s.strip(), "rfc": rfc_s.strip(), "cuenta_clabe": clabe_s.strip()}).execute()
                            id_new = res_new.data[0]["id_socio"]
                            
                            # Insertar aportación inicial
                            supabase.table("aportaciones_socios").insert({"id_socio": id_new, "monto": apo_ini, "tipo_movimiento": "APORTACION"}).execute()
                            
                            # Inicializar bóveda PLD
                            supabase.table("expedientes_pld").insert({"id_socio": id_new}).execute()
                            
                            st.success(f"Socio {nom_s} registrado con éxito.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error de base de datos: {str(e)}")

    with pestaña_mov:
        with st.form("form_mov_capital"):
            if not df_cap_table.empty:
                opciones_s = {f"{r['Nombre del Socio']} ({r['RFC']})": r["id_socio"] for r in cap_table}
                sel_socio_mov = st.selectbox("Seleccionar Inversionista:", options=list(opciones_s.keys()))
                tipo_m = st.radio("Tipo de Transacción:", ["APORTACION", "RETIRO"], horizontal=True)
                monto_m = st.number_input("Monto de Transacción ($):", min_value=500.0, value=10000.0, step=1000.0)
                
                ejecutar_m = st.form_submit_button("Asentar Movimiento en Libro Mayor", use_container_width=True)
                if ejecutar_m:
                    id_s_target = opciones_s[sel_socio_mov]
                    try:
                        supabase.table("aportaciones_socios").insert({"id_socio": id_s_target, "monto": monto_m, "tipo_movimiento": tipo_m}).execute()
                        st.success(f"Movimiento de ${monto_m:,.2f} asentado correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fallo transaccional: {str(e)}")
            else:
                st.warning("Registre un socio primero para realizar movimientos.")

st.divider()

# -----------------------------------------------------------------------------
# SECCIÓN 3: DISPERSIÓN CONTABLE DE DIVIDENDOS (SIMULADOR DE REPARTO)
# -----------------------------------------------------------------------------
titulo_seccion("porcentaje", "4. Calculadora de Dispersión Proporcional de Dividendos")

if not df_cap_table.empty and bolsa_dividendos_disponibles > 0:
    st.markdown("Esta tabla calcula exactamente **cuánto dinero le corresponde transferir a cada socio** en función de su porcentaje de participación sobre la bolsa de ganancias y capital cobrado en el Módulo de Cobranza.")
    
    df_reparto = df_cap_table.copy()
    df_reparto["Dividendo por Dispersar ($)"] = df_reparto["Porcentaje (%)"].apply(lambda p: round((p / 100.0) * bolsa_dividendos_disponibles, 2))
    
    # Formateo visual
    df_rep_visual = df_reparto.copy()
    df_rep_visual["Capital Aportado ($)"] = df_rep_visual["Capital Aportado ($)"].apply(lambda x: f"${x:,.2f}")
    df_rep_visual["Porcentaje (%)"] = df_rep_visual["Porcentaje (%)"].apply(lambda x: f"{x:.2f}%")
    df_rep_visual["Dividendo por Dispersar ($)"] = df_rep_visual["Dividendo por Dispersar ($)"].apply(lambda x: f"${x:,.2f}")
    
    st.dataframe(df_rep_visual[["Nombre del Socio", "RFC", "Porcentaje (%)", "Dividendo por Dispersar ($)", "Cuenta CLABE"]], use_container_width=True)
    
    col_d1, col_d2 = st.columns([1, 1])
    with col_d1:
        csv_reparto = df_reparto.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar Orden de Dispersión Bancaria (CSV)", data=csv_reparto, file_name="orden_transf_dividendos.csv", mime="text/csv", type="primary", use_container_width=True)
    with col_d2:
        st.info("💡 **Nota contable:** Al realizar la transferencia bancaria, adjunte el comprobante en la bitácora para sustentar la salida de caja de la entidad.")
else:
    st.info("No hay suficiente información o flujo en caja para calcular la dispersión de dividendos.")

st.divider()

# -----------------------------------------------------------------------------
# SECCIÓN 4: BÓVEDA DIGITAL DE CUMPLIMIENTO LEGAL Y FISCAL (PLD / KYC)
# -----------------------------------------------------------------------------
titulo_seccion("documento_check", "5. Bóveda Legal y Fiscal (Auditoría PLD / KYC)")

if not df_cap_table.empty:
    col_sel_pld, col_auditoria = st.columns([1, 1.8])
    
    mapa_id_nombre = {r["id_socio"]: f"{r['Nombre del Socio']} ({r['RFC']})" for r in cap_table}
    
    with col_sel_pld:
        id_pld_sel = st.selectbox("Seleccionar Expediente de Inversionista:", options=list(mapa_id_nombre.keys()), format_func=lambda x: mapa_id_nombre[x])
        
        # Consultar estado en expedientes_pld
        res_pld = supabase.table("expedientes_pld").select("*").eq("id_socio", id_pld_sel).execute()
        datos_pld = res_pld.data[0] if (res_pld.data and len(res_pld.data) > 0) else {"ine_validado": False, "csf_sat_validado": False, "domicilio_validado": False, "contrato_firmado": False, "notas_auditoria": "Sin registro inicial."}
        
        # Determinar semáforo de auditoría
        num_validados = sum([datos_pld["ine_validado"], datos_pld["csf_sat_validado"], datos_pld["domicilio_validado"], datos_pld["contrato_firmado"]])
        if num_validados == 4:
            dictamen("exito", "Expediente 100% Validado", "El socio cumple con todos los requisitos fiscales del SAT y normativos de PLD.")
        elif num_validados >= 2:
            dictamen("alerta", "Expediente Parcial (En Integración)", "Faltan documentos por cotejar. Puede operar bajo reserva temporal.")
        else:
            dictamen("peligro", "Expediente Incompleto / Riesgo PLD", "Se requiere recabar de inmediato la documentación fiscal antes de dispersar ganancias.")

    with col_auditoria:
        st.markdown("#### Cotejo y Check-list Documental (Requisitos CNBV / SAT)")
        with st.form("form_pld_auditoria"):
            a1, a2 = st.columns(2)
            chk_ine = a1.checkbox("1. Identificación Oficial Vigente (INE / Pasaporte)", value=datos_pld["ine_validado"])
            chk_csf = a1.checkbox("2. Constancia de Situación Fiscal SAT (Activa)", value=datos_pld["csf_sat_validado"])
            
            chk_dom = a2.checkbox("3. Comprobante de Domicilio (< 3 meses)", value=datos_pld["domicilio_validado"])
            chk_con = a2.checkbox("4. Contrato de Mutuo / Participación Firmado", value=datos_pld["contrato_firmado"])
            
            notas_aud = st.text_area("Notas de Auditoría o Enlaces a Archivos en Nube (Drive/Supabase):", value=datos_pld.get("notas_auditoria", ""), height=80)
            
            guardar_pld = st.form_submit_button("🔒 Actualizar Dictamen de Expediente PLD", use_container_width=True)
            if guardar_pld:
                with st.spinner("Asentando validación legal en servidor..."):
                    try:
                        payload_pld = {
                            "id_socio": id_pld_sel,
                            "ine_validado": chk_ine,
                            "csf_sat_validado": chk_csf,
                            "domicilio_validado": chk_dom,
                            "contrato_firmado": chk_con,
                            "notas_auditoria": notas_aud.strip()
                        }
                        supabase.table("expedientes_pld").upsert(payload_pld).execute()
                        st.success("Expediente fiscal actualizado correctamente en la base de datos.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fallo de servidor: {str(e)}")
else:
    st.info("No hay socios para auditar. Registre un inversionista arriba para habilitar la bóveda PLD.")