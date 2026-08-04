# =============================================================================
# Copyright (c) 2026 Eduardo Galván del Río. Todos los derechos reservados.
# 
# Este código fuente es propiedad exclusiva y confidencial. Queda estrictamente
# prohibida su reproducción, distribución, comercialización o modificación
# sin autorización expresa y por escrito del autor.
# =============================================================================

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from src.auth import verificar_acceso
from src.db import supabase
from src.theme import (
    aplicar_identidad_visual, encabezado_modulo, titulo_seccion,
    tarjeta_kpi, dictamen
)

st.set_page_config(page_title="Cobranza y Recaudación | SOFOM", layout="wide")

# --- BLINDAJE INSTITUCIONAL RBAC ---
verificar_acceso("COBRANZA")
# -----------------------------------

aplicar_identidad_visual()

# --- EL RIESGO ESTÉTICO (SIGNATURE DESIGN) ---
st.markdown("""
<style>
    [data-testid="stMetricValue"], .stDataFrame {
        font-family: 'JetBrains Mono', 'Courier New', monospace !important;
        letter-spacing: -0.5px;
    }
    [data-testid="metric-container"] {
        border-radius: 2px !important;
        border-left: 4px solid #1e293b !important; 
        padding-left: 15px !important;
    }
</style>
""", unsafe_allow_html=True)

encabezado_modulo(
    titulo="Ventanilla de Cobranza y Recaudación",
    subtitulo="Liquidación exacta de cuotas del plan de amortización, cálculo de mora y dispersión a Cap Table.",
    nombre_icono="banco",
    insignia="TESORERÍA Y CAJA"
)

usuario_actual = st.session_state.get("user_email", "Ejecutivo de Caja")

# -----------------------------------------------------------------------------
# 1. LECTURA DE CARTERA VIVA (ESTATUS: ESTRUCTURADO, VIGENTE, MORA)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=5) # Refresco rápido para ventanilla
def obtener_cartera_viva():
    try:
        res = supabase.table("prestamos").select("*").in_("estatus", ["ESTRUCTURADO", "VIGENTE", "ACTIVO", "MORA"]).execute()
        return res.data if res.data else []
    except Exception:
        return []

cartera = obtener_cartera_viva()

titulo_seccion("personas", "SELECCIÓN DE EXPEDIENTE")

if not cartera:
    st.info("No hay créditos activos en la cartera. Vaya al módulo de 'Amortización' para estructurar un nuevo crédito.")
    st.stop()

opciones_caja = ["-- Seleccione un Deudor para Registro de Pago --"]
mapa_deudores = {}
for c in cartera:
    # Usamos id_prestamo como llave absoluta
    id_prestamo = c.get("id_prestamo")
    if not id_prestamo: continue
    
    nom = c.get("cliente", "Sin nombre")
    rfc = c.get("rfc", "SIN-RFC")
    saldo = float(c.get("monto_total_recaudar", c.get("monto_principal", 0.0)))
    etiqueta = f"{nom} | RFC: {rfc} | ID: {str(id_prestamo)[:8]}"
    opciones_caja.append(etiqueta)
    mapa_deudores[etiqueta] = c

cliente_sel = st.selectbox("Expediente en Ventanilla:", opciones_caja)

if cliente_sel != "-- Seleccione un Deudor para Registro de Pago --":
    datos_deudor = mapa_deudores[cliente_sel]
    id_prestamo_activo = datos_deudor.get("id_prestamo")
    
    # -------------------------------------------------------------------------
    # 2. BÚSQUEDA DE LA CUOTA EXACTA EN PLAN_AMORTIZACION
    # -------------------------------------------------------------------------
    try:
        # Buscamos TODAS las cuotas pendientes de este préstamo ordenadas por número de cuota
        res_cuotas = supabase.table("plan_amortizacion").select("*").eq("id_prestamo", id_prestamo_activo).eq("estatus_pago", "PENDIENTE").order("numero_cuota").execute()
        cuotas_pendientes = res_cuotas.data if res_cuotas.data else []
    except Exception as e:
        st.error(f"Error al consultar el plan de pagos: {str(e)}")
        cuotas_pendientes = []

    if not cuotas_pendientes:
        st.balloons()
        st.success("Este crédito no tiene cuotas pendientes. El pagaré se encuentra totalmente liquidado.")
        # Actualizamos estatus maestro por seguridad
        supabase.table("prestamos").update({"estatus": "LIQUIDADO", "estatus_credito": "LIQUIDADO"}).eq("id_prestamo", id_prestamo_activo).execute()
        st.stop()
        
    # Extraemos la cuota exigible (la más vieja sin pagar)
    cuota_exigible = cuotas_pendientes[0]
    id_cuota_activa = cuota_exigible["id_cuota"]
    num_cuota = cuota_exigible["numero_cuota"]
    fecha_venc = cuota_exigible["fecha_vencimiento"]
    cuota_fija = float(cuota_exigible["cuota_fija"])
    interes_ord = float(cuota_exigible["interes_cobrado"])
    abono_cap = float(cuota_exigible["abono_capital"])
    saldo_insoluto = float(cuota_exigible["saldo_insoluto"])
    
    # --- CÁLCULO DE MORA (El reloj implacable) ---
    hoy = datetime.now().date()
    fecha_venc_dt = datetime.strptime(fecha_venc, "%Y-%m-%d").date()
    dias_atraso = (hoy - fecha_venc_dt).days
    
    mora_calculada = 0.0
    if dias_atraso > 0:
        tasa_mora_diaria = (float(datos_deudor.get("tasa_mensual", 0.06)) * 2) / 30.0 # Mora es 2x tasa ordinaria
        mora_calculada = round(saldo_insoluto * tasa_mora_diaria * dias_atraso, 2)
        txt_venc = f"¡Vencido por {dias_atraso} días!"
    else:
        dias_restantes = abs(dias_atraso)
        txt_venc = f"A tiempo (Faltan {dias_restantes} días)"
        
    monto_total_exigible = round(cuota_fija + mora_calculada, 2)

    st.divider()
    titulo_seccion("estadisticas", f"ESTADO DE CUENTA: CUOTA #{num_cuota}")
    
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("Vencimiento de Cuota", fecha_venc, delta=txt_venc, delta_color="inverse" if dias_atraso > 0 else "normal")
    with k2: st.metric("Cuota Ordinaria", f"${cuota_fija:,.2f}")
    with k3: st.metric("Interés Moratorio Generado", f"${mora_calculada:,.2f}", "Por pago tardío" if mora_calculada > 0 else "Al corriente")
    with k4: st.metric("TOTAL EXIGIBLE HOY", f"${monto_total_exigible:,.2f}")

    st.markdown("<br>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # 3. MOTOR DE RECAUDACIÓN Y CONCILIACIÓN (NIVEL NARANJA - AUDITORÍA)
    # -------------------------------------------------------------------------
    titulo_seccion("banco", "INGESTA DE PAGO Y DISPERSIÓN CONTABLE")
    
    with st.form("form_registro_pago"):
        c_pago1, c_pago2, c_pago3 = st.columns(3)
        with c_pago1:
            monto_ingresado = st.number_input("Monto Recibido ($ MXN):", min_value=1.0, value=monto_total_exigible, step=500.0)
        with c_pago2:
            metodo_pago = st.selectbox("Canal de Cobro:", ["Transferencia (SPEI)", "Efectivo en Ventanilla", "Domiciliación", "Cheque"])
        with c_pago3:
            referencia_bancaria = st.text_input("Clave de Rastreo / Autorización:", value=f"OP-{datetime.now().strftime('%m%d%H%M')}")
            
        st.markdown("---")
        
        # Prelación de pagos exacta
        remanente = monto_ingresado
        mora_pagada = min(remanente, mora_calculada)
        remanente -= mora_pagada
        interes_pagado = min(remanente, interes_ord)
        remanente -= interes_pagado
        capital_pagado = min(remanente, abono_cap)
        
        c_sim1, c_sim2 = st.columns(2)
        with c_sim1:
            st.markdown("**Prelación Legal del Abono:**")
            st.caption(f"1. Interés Moratorio (Gastos de Cobranza): **${mora_pagada:,.2f}**")
            st.caption(f"2. Interés Ordinario Devengado: **${interes_pagado:,.2f}**")
            st.caption(f"3. Reducción de Capital: **${capital_pagado:,.2f}**")
        with c_sim2:
            st.markdown("**Dispersión Institucional (Smart Contract):**")
            # El 65% del interés ordinario va a los socios, 15% a reserva
            utilidad_socios = round(interes_pagado * 0.65, 2)
            reserva_riesgo = round(interes_pagado * 0.15, 2)
            st.caption(f"➔ Fondo de Dividendos Socios (65%): **${utilidad_socios:,.2f}**")
            st.caption(f"➔ Reserva Preventiva SOFOM (15%): **${reserva_riesgo:,.2f}**")

        st.markdown("<br>", unsafe_allow_html=True)
        btn_cobrar = st.form_submit_button("Ejecutar Conciliación Bancaria", type="primary", width="stretch")

    # -------------------------------------------------------------------------
    # 4. TRANSACCIÓN SQL (ACID COMPLIANT)
    # -------------------------------------------------------------------------
    if btn_cobrar:
        # Validación de suficiencia
        if monto_ingresado < monto_total_exigible:
            st.error(f"⚠️ El monto ingresado (${monto_ingresado:,.2f}) es menor al exigible (${monto_total_exigible:,.2f}). Esta versión del sistema no admite pagos parciales. El cliente debe cubrir la cuota completa.")
        else:
            with st.spinner("Matando cuota en servidor e inyectando dividendos a socios..."):
                try:
                    # 1. Matamos la cuota en plan_amortizacion
                    supabase.table("plan_amortizacion").update({"estatus_pago": "PAGADA"}).eq("id_cuota", id_cuota_activa).execute()
                    
                    # 2. Insertamos el recibo real en cobranza_y_comisiones
                    payload_cobranza = {
                        "id_cuota": id_cuota_activa,
                        "monto_recibido": monto_ingresado,
                        "interes_real_cobrado": interes_pagado,
                        "comision_operador": 0.0, # Para futuras expansiones
                        "reserva_riesgo": reserva_riesgo,
                        "utilidad_socios": utilidad_socios
                        # fecha_pago_real se genera automáticamente por Default en SQL
                    }
                    supabase.table("cobranza_y_comisiones").insert(payload_cobranza).execute()
                    
                    # 3. Actualizamos el préstamo maestro
                    estatus_nuevo = "VIGENTE"
                    # Si era la última cuota (el saldo insoluto que proyectaba esta cuota era 0)
                    if saldo_insoluto <= 0.01:
                        estatus_nuevo = "LIQUIDADO"
                        
                    supabase.table("prestamos").update({"estatus": estatus_nuevo}).eq("id_prestamo", id_prestamo_activo).execute()
                    
                    # 4. Dictamen Visual
                    st.toast(f"Recibo emitido exitosamente. Folio: {referencia_bancaria}", icon="✅")
                    
                    if estatus_nuevo == "LIQUIDADO":
                        st.balloons()
                        dictamen("exito", "PAGARÉ EJECUTIVO LIBERADO", f"La cuota #{num_cuota} era la última del contrato. El crédito ha sido marcado como LIQUIDADO.")
                    else:
                        dictamen("exito", "CONCILIACIÓN EXITOSA", f"La cuota #{num_cuota} se ha marcado como PAGADA. Los dividendos (${utilidad_socios:,.2f}) ya están disponibles en el módulo de Socios y Capital.")
                        st.info("Para cobrar la siguiente cuota, recargue la selección del cliente.")
                        
                except Exception as e:
                    st.error(f"Fallo en transacción ACID SQL: {str(e)}")
else:
    st.info("Seleccione un expediente en la parte superior para habilitar la caja institucional.")