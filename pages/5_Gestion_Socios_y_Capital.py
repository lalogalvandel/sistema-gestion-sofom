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
# FUNCIONES DE CONSULTA CONTABLE
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

# Cálculo del Cap Table
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
            "Porcentaje (%)": 0.0
        })
    if capital_total_fondo > 0:
        for socio in cap_table:
            socio["Porcentaje (%)"] = round((socio["Capital Aportado ($)"] / capital_total_fondo) * 100, 2)
            
df_cap_table = pd.DataFrame(cap_table) if cap_table else pd.DataFrame()

# -----------------------------------------------------------------------------
# SECCIÓN 1: KPIs
# -----------------------------------------------------------------------------
titulo_seccion("tendencia", "1. Estructura de Capital y Salud del Fondo")
num_socios = len(df_socios) if not df_socios.empty else 0
bolsa_dividendos_disponibles = 0.0
try:
    res_cob = supabase.table("cobranza_y_comisiones").select("utilidad_socios").execute()
    if res_cob.data:
        bolsa_dividendos_disponibles = float(pd.DataFrame(res_cob.data)["utilidad_socios"].sum())
except:
    bolsa_dividendos_disponibles = 0.0

c1, c2 = st.columns(2)
with c1:
    tarjeta_kpi("billetera", "Capital Social Total Aportado", f"${capital_total_fondo:,.2f}", "Suma de aportaciones patrimoniales activas", "marino_800")
with c2:
    tarjeta_kpi("personas", "Socios Inversionistas Activos", f"{num_socios} socios", "Inversionistas fondeando la operación", "azul_600")

st.markdown("<br>", unsafe_allow_html=True)

c3, c4 = st.columns(2)
with c3:
    tarjeta_kpi("banco", "Bolsa de Dividendos (65% + Cap)", f"${bolsa_dividendos_disponibles:,.2f}", "Flujo cobrado disponible para dispersión", "dorado_600")
with c4:
    tarjeta_kpi("escudo", "Modelo de Participación", "Proporcional", "Rendimiento variable según Cap Table", "verde_lago")

st.divider()

# -----------------------------------------------------------------------------
# SECCIÓN 2: CAP TABLE Y REGISTRO
# -----------------------------------------------------------------------------
col_tabla, col_gestion = st.columns([1.4, 1])

with col_tabla:
    titulo_seccion("balanza", "2. Cap Table Institucional")
    if not df_cap_table.empty:
        df_ver = df_cap_table.copy()
        df_ver["Capital Aportado ($)"] = df_ver["Capital Aportado ($)"].apply(lambda x: f"${x:,.2f}")
        df_ver["Porcentaje (%)"] = df_ver["Porcentaje (%)"].apply(lambda x: f"{x:.2f}%")
        st.dataframe(df_ver[["Nombre del Socio", "RFC", "Capital Aportado ($)", "Porcentaje (%)", "Cuenta CLABE"]], use_container_width=True)
    else:
        st.info("No hay socios registrados.")

with col_gestion:
    titulo_seccion("caja", "3. Ventanilla de Movimientos")
    pestaña_alta, pestaña_mov = st.tabs(["➕ Alta", "💵 Movimientos"])
    with pestaña_alta:
        with st.form("form_alta_socio"):
            nom_s = st.text_input("Nombre Completo:")
            rfc_s = st.text_input("RFC:")
            clabe_s = st.text_input("Cuenta CLABE:")
            apo_ini = st.number_input("Aportación Inicial ($):", value=50000.0)
            if st.form_submit_button("Registrar Socio"):
                res_new = supabase.table("socios").insert({"nombre_completo": nom_s, "rfc": rfc_s, "cuenta_clabe": clabe_s}).execute()
                id_new = res_new.data[0]["id_socio"]
                supabase.table("aportaciones_socios").insert({"id_socio": id_new, "monto": apo_ini, "tipo_movimiento": "APORTACION"}).execute()
                supabase.table("expedientes_pld").insert({"id_socio": id_new}).execute()
                st.rerun()

    with pestaña_mov:
        with st.form("form_mov_capital"):
            if not df_cap_table.empty:
                opciones_s = {f"{r['Nombre del Socio']} ({r['RFC']})": r["id_socio"] for r in cap_table}
                sel_socio_mov = st.selectbox("Inversionista:", options=list(opciones_s.keys()))
                tipo_m = st.radio("Tipo:", ["APORTACION", "RETIRO"], horizontal=True)
                monto_m = st.number_input("Monto ($):", value=10000.0)
                if st.form_submit_button("Asentar Movimiento"):
                    supabase.table("aportaciones_socios").insert({"id_socio": opciones_s[sel_socio_mov], "monto": monto_m, "tipo_movimiento": tipo_m}).execute()
                    st.rerun()

st.divider()

# -----------------------------------------------------------------------------
# SECCIÓN 3: DISPERSIÓN
# -----------------------------------------------------------------------------
titulo_seccion("porcentaje", "4. Calculadora de Dividendos")
if not df_cap_table.empty and bolsa_dividendos_disponibles > 0:
    df_reparto = df_cap_table.copy()
    df_reparto["Dividendo ($)"] = df_reparto["Porcentaje (%)"].apply(lambda p: round((p / 100.0) * bolsa_dividendos_disponibles, 2))
    st.dataframe(df_reparto[["Nombre del Socio", "Dividendo ($)"]], use_container_width=True)

# -----------------------------------------------------------------------------
# SECCIÓN 4: BÓVEDA PLD
# -----------------------------------------------------------------------------
titulo_seccion("documento_check", "5. Bóveda Legal (PLD / KYC)")
if not df_cap_table.empty:
    id_pld_sel = st.selectbox("Auditoría de Inversionista:", options=list(mapa_id_nombre.keys()), format_func=lambda x: mapa_id_nombre[x]) if 'mapa_id_nombre' in locals() else st.selectbox("Seleccione:", options=list({f"{r['Nombre del Socio']}": r['id_socio'] for r in cap_table}.keys()))