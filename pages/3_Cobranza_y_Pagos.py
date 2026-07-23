# 
# Copyright (c) 2026 Eduardo Galván del Rio. Todos los derechos reservados.
# 
# Este código fuente es propiedad exclusiva y confidencial. Queda estrictamente
# prohibida su reproducción, distribución, comercialización o modificación
# sin autorización expresa y por escrito del autor.
# 
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

encabezado_modulo(
    titulo="Ventanilla de Cobranza y Recaudación",
    subtitulo="Ingreso de abonos quincenales/mensuales, amortización contable de saldo insoluto y liberación de pagarés.",
    nombre_icono="banco",  # <--- CORREGIDO: aquí decía titulo_icono="banco"
    insignia="TESORERÍA Y CAJA"
)

usuario_actual = st.session_state.get("user_email", "Ejecutivo de Caja")

# -----------------------------------------------------------------------------
# 1. LECTURA DE CARTERA VIVA (ESTATUS: VIGENTE)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=10)
def obtener_cartera_viva():
    try:
        # Traemos estrictamente los créditos que ya pasaron por el Módulo 4 (Jurídico)
        res = supabase.table("prestamos").select("*").in_("estatus", ["VIGENTE", "ACTIVO", "MORA"]).order("cliente", desc=False).execute()
        return res.data if res.data else []
    except Exception:
        return []

cartera = obtener_cartera_viva()

titulo_seccion("personas", "1. Selección de Deudor y Consulta de Saldo Exigible")

if not cartera:
    st.info("No hay créditos en estatus **VIGENTE** en el servidor. Ve al módulo **4. Contratos y Legal** y formaliza un expediente para habilitar su cobranza.")
    st.stop()

# Selector inteligente con resumen financiero
opciones_caja = ["-- Seleccione un Deudor para Registro de Pago --"]
mapa_deudores = {}
for c in cartera:
    nom = c.get("cliente", "Sin nombre")
    rfc = c.get("rfc", "SIN-RFC")
    saldo = float(c.get("saldo_pendiente", c.get("monto", 0.0)))
    etiqueta = f"{nom} | RFC: {rfc} | Deuda Exigible: ${saldo:,.2f} MXN"
    opciones_caja.append(etiqueta)
    mapa_deudores[etiqueta] = c

cliente_sel = st.selectbox("Expediente en Ventanilla de Cobranza:", opciones_caja)

if cliente_sel != "-- Seleccione un Deudor para Registro de Pago --":
    datos_deudor = mapa_deudores[cliente_sel]
    
    # Extracción segura de variables numéricas
    saldo_actual = float(pd.to_numeric(datos_deudor.get("saldo_pendiente", datos_deudor.get("monto", 0.0)), errors="coerce"))
    cuota_fija = float(pd.to_numeric(datos_deudor.get("cuota_fija_proyectada", datos_deudor.get("monto", 0.0)/12), errors="coerce"))
    tasa_mes = float(pd.to_numeric(datos_deudor.get("tasa_mensual", 6.0), errors="coerce"))
    frec = str(datos_deudor.get("frecuencia", "Mensual"))
    prox_venc = str(datos_deudor.get("proximo_vencimiento", datetime.now().strftime("%Y-%m-%d")))
    target_id = str(datos_deudor.get("rfc", "")).strip()

    st.divider()
    titulo_seccion("estadisticas", "2. Radiografía de la Obligación y Estado de Cuenta")
    
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        tarjeta_kpi("Saldo Insoluto Actual", f"${saldo_actual:,.2f}", "Capital pendiente de liquidar")
    with k2:
        tarjeta_kpi("Cuota Fija Pactada", f"${cuota_fija:,.2f}", f"Periodicidad: {frec}")
    with k3:
        tarjeta_kpi("Tasa Ordinaria", f"{tasa_mes:.2f}% mensual", "Aplicable sobre saldo insoluto")
    with k4:
        # Cálculo simple de días de vencimiento
        try:
            fech_v = datetime.strptime(prox_venc, "%Y-%m-%d")
            dias_dif = (fech_v - datetime.now()).days
            txt_venc = f"En {dias_dif} días" if dias_dif >= 0 else f"¡Vencido por {abs(dias_dif)} días!"
        except:
            txt_venc = prox_venc
        tarjeta_kpi("Próximo Vencimiento", prox_venc, txt_venc)

    st.markdown("<br>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # 2. MOTOR DE RECAUDACIÓN Y APLICACIÓN DE ABONOS
    # -------------------------------------------------------------------------
    titulo_seccion("banco", "3. Ingesta de Pago y Aplicación Contable")
    
    with st.form("form_registro_pago"):
        st.markdown(f"**Registrando abono a la cuenta de: `{datos_deudor.get('cliente')}` (RFC: {target_id})**")
        
        c_pago1, c_pago2, c_pago3 = st.columns(3)
        with c_pago1:
            monto_ingresado = st.number_input("Monto Recibido en Ventanilla ($ MXN):", min_value=1.0, max_value=float(saldo_actual * 1.5), value=float(cuota_fija), step=500.0)
        with c_pago2:
            metodo_pago = st.selectbox("Forma de Pago / Canal:", ["Transferencia Electrónica (SPEI)", "Depósito en Efectivo / Ventanilla", "Cheque Salvo Buen Cobro", "Domiciliación Bancaria"])
        with c_pago3:
            referencia_bancaria = st.text_input("Clave de Rastreo SPEI / No. Autorización:", value=f"SPEI-{datetime.now().strftime('%m%d%H%M%S')}")
            
        st.markdown("---")
        st.markdown("**Prelación Legal del Abono (Cláusula Segunda del Contrato):**")
        
        # Simulación de reparto: primero intereses del periodo, luego reducción de capital
        tasa_periodo = (tasa_mes / 100.0) / (2.0 if frec == "Quincenal" else 1.0)
        interes_cobrado = round(saldo_actual * tasa_periodo, 2)
        if monto_ingresado >= saldo_actual:
            abono_capital = saldo_actual
            interes_cobrado = round(monto_ingresado - saldo_actual, 2)
        else:
            abono_capital = max(round(monto_ingresado - interes_cobrado, 2), 0.0)
            
        c_sim1, c_sim2 = st.columns(2)
        with c_sim1:
            st.caption(f"▪️ Interés devengado cubierto: **${interes_cobrado:,.2f} MXN**")
            st.caption(f"▪️ Abono directo a reducción de capital: **${abono_capital:,.2f} MXN**")
        with c_sim2:
            nuevo_saldo_sim = max(round(saldo_actual - abono_capital, 2), 0.0)
            st.caption(f"▪️ **Nuevo Saldo Insoluto tras el pago: `${nuevo_saldo_sim:,.2f} MXN`**")

        st.markdown("<br>", unsafe_allow_html=True)
        btn_cobrar = st.form_submit_button("Confirmar Abono y Aplicar a Saldo en Servidor", type="primary", width="stretch")

    # Ejecución transaccional al presionar el botón
    if btn_cobrar:
        with st.spinner("Procesando transacción bancaria y actualizando tabla de préstamos..."):
            try:
                nuevo_saldo_real = max(round(saldo_actual - abono_capital, 2), 0.0)
                
                # Determinamos si con este abono el cliente ya liquidó su pagaré
                nuevo_estatus = "LIQUIDADO" if nuevo_saldo_real <= 0.01 else "VIGENTE"
                
                # Calculamos el siguiente periodo de cobro
                dias_sumar = 15 if frec == "Quincenal" else 30
                nueva_fecha_venc = (datetime.now() + timedelta(days=dias_sumar)).strftime("%Y-%m-%d")
                
                payload_pago = {
                    "saldo_pendiente": nuevo_saldo_real,
                    "estatus": nuevo_estatus,
                    "proximo_vencimiento": nueva_fecha_venc
                }
                
                # Actualizamos en Supabase
                res_upd = supabase.table("prestamos").update(payload_pago).eq("rfc", target_id).execute()
                if not res_upd.data:
                    res_upd = supabase.table("prestamos").update(payload_pago).eq("cliente", datos_deudor.get("cliente")).execute()
                    
                st.toast(f"Pago por ${monto_ingresado:,.2f} registrado.", icon="✅")
                
                if nuevo_estatus == "LIQUIDADO":
                    dictamen("exito", "¡CRÉDITO LIQUIDADO EN SU TOTALIDAD!", f"El deudor **{datos_deudor.get('cliente')}** ha cubierto el 100% de su saldo insoluto. El pagaré mercantil queda liberado y su estatus cambió a **LIQUIDADO**.")
                else:
                    dictamen("exito", "Abono Aplicado Correctamente", f"Se aplicaron **${abono_capital:,.2f}** a capital. El nuevo saldo exigible de **{datos_deudor.get('cliente')}** es de **${nuevo_saldo_real:,.2f} MXN**. Próximo vencimiento programado para el {nueva_fecha_venc}.")
                
                st.info("**Dato operativo:** Refresca o selecciona otro cliente en el menú superior para continuar con la gestión de cobranza del día.")
                
            except Exception as e:
                st.error(f"Error en la transacción bancaria: {str(e)}")
else:
    st.info("Seleccione un expediente en la parte superior para habilitar la ventanilla de cobro.")