import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from src.db import supabase
from src.theme import (
    aplicar_identidad_visual, encabezado_modulo, titulo_seccion,
    dictamen, tarjeta_kpi
)

st.set_page_config(page_title="Control de Cobranza | SOFOM", layout="wide")
aplicar_identidad_visual()
from src.auth import verificar_acceso
verificar_acceso("COBRANZA")
encabezado_modulo(
    titulo="Ventanilla de Cobranza y Gestión de Capital",
    subtitulo="Procesamiento de pagos con prelación (Interés > Capital) y recálculo automático de saldos.",
    nombre_icono="banco",
    insignia="COBRANZA ACTIVA"
)

# -----------------------------------------------------------------------------
# LÓGICA DE RECALCULO DE AMORTIZACIÓN
# -----------------------------------------------------------------------------
def recalcular_calendario(id_prestamo, nuevo_saldo, tasa_mensual, cuotas_restantes, fecha_base):
    tasa_q = tasa_mensual / 2
    if tasa_q > 0:
        nueva_cuota = nuevo_saldo * (tasa_q * (1 + tasa_q)**cuotas_restantes) / ((1 + tasa_q)**cuotas_restantes - 1)
    else:
        nueva_cuota = nuevo_saldo / cuotas_restantes
        
    nuevas_cuotas = []
    saldo = nuevo_saldo
    fecha_iter = fecha_base
    
    for q in range(1, cuotas_restantes + 1):
        fecha_iter += timedelta(days=15)
        int_q = round(saldo * tasa_q, 2)
        if q == cuotas_restantes:
            cap_q = saldo
            cuota_real = round(cap_q + int_q, 2)
            saldo = 0.0
        else:
            cuota_real = round(nueva_cuota, 2)
            cap_q = round(cuota_real - int_q, 2)
            saldo = round(saldo - cap_q, 2)
            
        nuevas_cuotas.append({
            "numero_cuota": q,
            "fecha_vencimiento": fecha_iter.strftime("%Y-%m-%d"),
            "cuota_fija": cuota_real,
            "interes_cobrado": int_q,
            "abono_capital": cap_q,
            "saldo_insoluto": saldo,
            "estatus_pago": "PENDIENTE"
        })
    return nuevas_cuotas

# -----------------------------------------------------------------------------
# DASHBOARD COBRANZA
# -----------------------------------------------------------------------------
# KPI superiores
@st.cache_data(ttl=15)
def obtener_resumen_cobranza():
    try:
        res = supabase.table("cobranza_y_comisiones").select("monto_recibido, interes_real_cobrado, comision_operador, reserva_riesgo, utilidad_socios").execute()
        if res.data and len(res.data) > 0:
            df_c = pd.DataFrame(res.data)
            return float(df_c["monto_recibido"].sum()), float(df_c["interes_real_cobrado"].sum()), float(df_c["comision_operador"].sum()), float(df_c["utilidad_socios"].sum())
        return 0.0, 0.0, 0.0, 0.0
    except:
        return 0.0, 0.0, 0.0, 0.0

recibido_hist, interes_hist, comision_hist, utilidad_hist = obtener_resumen_cobranza()

k1, k2 = st.columns(2)
with k1:
    tarjeta_kpi("billetera", "Total Recaudado en Caja", f"${recibido_hist:,.2f}", "Flujo acumulado", "marino_800")
with k2:
    tarjeta_kpi("porcentaje", "Interés Real Cobrado", f"${interes_hist:,.2f}", "Base para retribuciones", "azul_600")

st.markdown("<br>", unsafe_allow_html=True)
k3, k4 = st.columns(2)
with k3:
    tarjeta_kpi("escudo", "Tu Comisión (20%)", f"${comision_hist:,.2f}", "Ingreso Administrador", "dorado_600")
with k4:
    tarjeta_kpi("personas", "Utilidad Socios", f"${utilidad_hist:,.2f}", "65% Interés + Capital", "verde_lago")

st.divider()

# Ventanilla
titulo_seccion("caja", "2. Ventanilla de Cobranza")
prestamos_activos = supabase.table("prestamos").select("id_prestamo, monto_principal, clientes(nombre_completo)").eq("estatus_credito", "VIGENTE").execute().data or []

col_sel, col_operacion = st.columns([1, 1.4])
with col_sel:
    opciones = ["-- Seleccione Crédito --"] + [f"{p['clientes']['nombre_completo']} | ${p['monto_principal']:,.2f}" for p in prestamos_activos]
    mapa = {f"{p['clientes']['nombre_completo']} | ${p['monto_principal']:,.2f}": p for p in prestamos_activos}
    credito_sel = st.selectbox("Expediente:", options=opciones)

with col_operacion:
    if credito_sel != "-- Seleccione Crédito --":
        p = mapa[credito_sel]
        cuota_pend = supabase.table("plan_amortizacion").select("*").eq("id_prestamo", p["id_prestamo"]).eq("estatus_pago", "PENDIENTE").order("numero_cuota").limit(1).execute().data
        
        if cuota_pend:
            c = cuota_pend[0]
            with st.form("cobro"):
                st.info(f"Vencimiento: Q{c['numero_cuota']} | {c['fecha_vencimiento']}")
                monto_recibido_real = st.number_input("Monto Real Recibido ($):", value=float(c['cuota_fija']))
                
                # Prelación
                interes_real = float(c['interes_cobrado']) if monto_recibido_real >= float(c['interes_cobrado']) else monto_recibido_real
                abono_cap_real = round(monto_recibido_real - interes_real, 2)
                
                if st.form_submit_button("Registrar Pago"):
                    # 1. Registrar pago
                    supabase.table("cobranza_y_comisiones").insert({
                        "id_cuota": c["id_cuota"],
                        "monto_recibido": monto_recibido_real,
                        "interes_real_cobrado": interes_real,
                        "comision_operador": round(interes_real * 0.20, 2),
                        "reserva_riesgo": round(interes_real * 0.15, 2),
                        "utilidad_socios": round((interes_real * 0.65) + abono_cap_real, 2)
                    }).execute()
                    
                    # 2. Recalculo si hubo abono a capital
                    if abono_cap_real > 0:
                        prestamo = supabase.table("prestamos").select("*").eq("id_prestamo", p["id_prestamo"]).single().execute().data
                        cuotas_futuras = supabase.table("plan_amortizacion").select("*").eq("id_prestamo", p["id_prestamo"]).eq("estatus_pago", "PENDIENTE").execute().data
                        supabase.table("plan_amortizacion").delete().eq("id_prestamo", p["id_prestamo"]).eq("estatus_pago", "PENDIENTE").execute()
                        nuevas = recalcular_calendario(p["id_prestamo"], float(c["saldo_insoluto"]) - abono_cap_real, prestamo["tasa_interes_mensual"], len(cuotas_futuras), datetime.strptime(c["fecha_vencimiento"], "%Y-%m-%d"))
                        for f in nuevas:
                            f["id_prestamo"] = p["id_prestamo"]
                            supabase.table("plan_amortizacion").insert(f).execute()
                            
                    supabase.table("plan_amortizacion").update({"estatus_pago": "PAGADO", "abono_capital": abono_cap_real, "interes_cobrado": interes_real}).eq("id_cuota", c["id_cuota"]).execute()
                    st.rerun()
        else:
            dictamen("exito", "Crédito al corriente", "No hay cuotas pendientes.")