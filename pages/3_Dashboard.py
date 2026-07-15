import streamlit as st
import pandas as pd
from datetime import datetime
from src.db import supabase
from src.theme import (
    aplicar_identidad_visual, encabezado_modulo, titulo_seccion,
    dictamen, tarjeta_kpi
)

st.set_page_config(page_title="Control de Cobranza y Comisiones | SOFOM", layout="wide")

# 1. Inyectar identidad visual y encabezado modular
aplicar_identidad_visual()

encabezado_modulo(
    titulo="Panel Operativo de Cobranza y Comisiones",
    subtitulo="Gestión transaccional de pagos en tiempo real y separación contable del rendimiento operativo.",
    nombre_icono="banco",
    insignia="COBRANZA ACTIVA"
)

# -----------------------------------------------------------------------------
# SECCIÓN 1: KPI DE RECAUDACIÓN Y TU COMISIÓN (CUADRÍCULA 2x2)
# -----------------------------------------------------------------------------
titulo_seccion("tendencia", "1. Estado de Cuenta Consolidado de la Entidad")

@st.cache_data(ttl=15)
def obtener_resumen_cobranza():
    try:
        res = supabase.table("cobranza_y_comisiones").select("monto_recibido, interes_real_cobrado, comision_operador, reserva_riesgo, utilidad_socios").execute()
        if res.data and len(res.data) > 0:
            df_c = pd.DataFrame(res.data)
            tot_recibido = float(df_c["monto_recibido"].sum())
            tot_interes = float(df_c["interes_real_cobrado"].sum())
            tot_comision = float(df_c["comision_operador"].sum())
            tot_utilidad = float(df_c["utilidad_socios"].sum())
            return tot_recibido, tot_interes, tot_comision, tot_utilidad
        return 0.0, 0.0, 0.0, 0.0
    except Exception:
        return 0.0, 0.0, 0.0, 0.0

recibido_hist, interes_hist, comision_hist, utilidad_hist = obtener_resumen_cobranza()

# Cuadrícula simétrica 2x2 para evitar recortes numéricos
k1, k2 = st.columns(2)
with k1:
    tarjeta_kpi("billetera", "Total Recaudado en Caja", f"${recibido_hist:,.2f}", "Flujo acumulado de capital e interés", "marino_800")
with k2:
    tarjeta_kpi("porcentaje", "Interés Real Cobrado", f"${interes_hist:,.2f}", "Base de cálculo para retribuciones", "azul_600")

st.markdown("<br>", unsafe_allow_html=True)

k3, k4 = st.columns(2)
with k3:
    tarjeta_kpi("escudo", "Tu Comisión Operativa (20%)", f"${comision_hist:,.2f}", "Ingreso Administrador del Fondo", "dorado_600")
with k4:
    tarjeta_kpi("personas", "Utilidad Neta Socios Capitalistas", f"${utilidad_hist:,.2f}", "65% Interés + Capital recuperado", "verde_lago")

st.divider()

# -----------------------------------------------------------------------------
# SECCIÓN 2: REGISTRO TRANSACCIONAL DE PAGOS QUINCENALES
# -----------------------------------------------------------------------------
titulo_seccion("caja", "2. Ventanilla de Cobranza y Registro de Abonos")

def obtener_prestamos_vigentes():
    try:
        res = supabase.table("prestamos").select("id_prestamo, monto_principal, cuota_fija_proyectada, clientes(nombre_completo, rfc)").eq("estatus_credito", "VIGENTE").execute()
        return res.data if res.data else []
    except Exception:
        return []

prestamos_activos = obtener_prestamos_vigentes()

col_sel, col_operacion = st.columns([1, 1.4])

with col_sel:
    st.markdown("#### Selección de Expediente")
    if not prestamos_activos:
        st.info("No hay créditos vigentes registrados en el servidor. Formalice un préstamo en el Módulo 2.")
        opciones_prestamo = ["-- Sin Créditos Activos --"]
    else:
        opciones_prestamo = ["-- Seleccione Crédito para Cobro --"]
        mapa_prestamos = {}
        for p in prestamos_activos:
            cliente_info = p.get("clientes", {})
            nombre_c = cliente_info.get("nombre_completo", "Deudor Desconocido")
            etiqueta = f"{nombre_c} | Préstamo: ${p['monto_principal']:,.2f}"
            opciones_prestamo.append(etiqueta)
            mapa_prestamos[etiqueta] = p

    credito_seleccionado = st.selectbox("Expediente de Crédito:", options=opciones_prestamo)

with col_operacion:
    st.markdown("#### Cuota Quincenal por Recaudar")
    if credito_seleccionado in ["-- Sin Créditos Activos --", "-- Seleccione Crédito para Cobro --"]:
        dictamen("alerta", "Selección Pendiente", "Seleccione un expediente vigente en el panel izquierdo para visualizar el siguiente vencimiento y procesar el pago.")
    else:
        datos_p = mapa_prestamos[credito_seleccionado]
        id_p = datos_p["id_prestamo"]
        
        res_cuota = supabase.table("plan_amortizacion").select("*").eq("id_prestamo", id_p).eq("estatus_pago", "PENDIENTE").order("numero_cuota", desc=False).limit(1).execute()
        
        if res_cuota.data and len(res_cuota.data) > 0:
            cuota_pend = res_cuota.data[0]
            id_cuota = cuota_pend["id_cuota"]
            num_q = cuota_pend["numero_cuota"]
            fecha_venc = cuota_pend["fecha_vencimiento"]
            monto_cuota = float(cuota_pend["cuota_fija"])
            abono_cap = float(cuota_pend["abono_capital"])
            interes_q = float(cuota_pend["interes_cobrado"])
            
            comision_calc = round(interes_q * 0.20, 2)
            reserva_calc = round(interes_q * 0.15, 2)
            utilidad_calc = round(interes_q * 0.65 + abono_cap, 2)
            
            with st.form("form_cobranza_transaccional"):
                st.info(f"**Vencimiento Detectado:** Quincena N° **{num_q}** | Fecha límite: **{fecha_venc}**")
                
                c_a, c_b, c_c = st.columns(3)
                c_a.text_input("Monto Cuota ($):", value=f"${monto_cuota:,.2f}", disabled=True)
                c_b.text_input("Abono Capital ($):", value=f"${abono_cap:,.2f}", disabled=True)
                c_c.text_input("Interés Quincena ($):", value=f"${interes_q:,.2f}", disabled=True)
                
                st.markdown("---")
                st.markdown("#### Desglose Automático de Retribución Operativa")
                r1, r2, r3 = st.columns(3)
                r1.metric("Comisión Operador (20%)", f"${comision_calc:,.2f}")
                r2.metric("Reserva Riesgo (15%)", f"${reserva_calc:,.2f}")
                r3.metric("Dividendo Socios (65%+Cap)", f"${utilidad_calc:,.2f}")
                
                monto_recibido_real = st.number_input("Confirmar Monto Real Recibido en Caja ($):", min_value=1.0, value=monto_cuota, step=100.0)
                
                procesar = st.form_submit_button("Registrar Pago y Ejecutar Reparto Contable", use_container_width=True)
                
                if procesar:
                    with st.spinner("Actualizando tablas transaccionales en servidor..."):
                        try:
                            supabase.table("plan_amortizacion").update({"estatus_pago": "PAGADO"}).eq("id_cuota", id_cuota).execute()
                            
                            payload_pago = {
                                "id_cuota": id_cuota,
                                "monto_recibido": monto_recibido_real,
                                "interes_real_cobrado": interes_q,
                                "comision_operador": comision_calc,
                                "reserva_riesgo": reserva_calc,
                                "utilidad_socios": utilidad_calc
                            }
                            supabase.table("cobranza_y_comisiones").insert(payload_pago).execute()
                            
                            dictamen("exito", "Pago Registrado Exitosamente", f"Quincena N° {num_q} abonada en base de datos. Comisión operativa de ${comision_calc:,.2f} asignada.")
                            st.rerun()
                        except Exception as e:
                            dictamen("peligro", "Error de Transacción", f"Fallo al procesar la cobranza en el servidor: {str(e)}")
        else:
            dictamen("exito", "Crédito Liquidado", "¡Este expediente se encuentra completamente pagado! No existen quincenas pendientes en el servidor.")

st.divider()

# -----------------------------------------------------------------------------
# SECCIÓN 3: BITÁCORA DE AUDITORÍA Y MOVIMIENTOS RECIENTES
# -----------------------------------------------------------------------------
titulo_seccion("documento", "3. Bitácora Institucional de Recaudación")
try:
    res_bitacora = supabase.table("cobranza_y_comisiones").select("fecha_pago_real, monto_recibido, interes_real_cobrado, comision_operador, utilidad_socios").order("fecha_pago_real", desc=True).limit(15).execute()
    if res_bitacora.data and len(res_bitacora.data) > 0:
        df_bitacora = pd.DataFrame(res_bitacora.data)
        df_bitacora["fecha_pago_real"] = pd.to_datetime(df_bitacora["fecha_pago_real"]).dt.strftime("%Y-%m-%d %H:%M")
        df_bitacora.columns = ["Fecha / Hora Pago", "Monto Recibido ($)", "Interés Cobrado ($)", "Tu Comisión 20% ($)", "Flujo Socios ($)"]
        st.dataframe(df_bitacora, use_container_width=True)
    else:
        st.info("No hay transacciones de pago registradas en la bitácora del servidor.")
except Exception as e:
    dictamen("peligro", "Error de Consulta", "No se pudo cargar el historial transaccional.")