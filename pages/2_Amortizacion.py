import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.db import supabase, formalizar_credito_y_amortización

st.set_page_config(page_title="Amortización y Formalización | SOFOM", layout="wide")

st.title("Motor de Amortización y Formalización de Contratos")
st.markdown("Generación de calendarios bajo el Sistema Francés y registro transaccional en PostgreSQL.")
st.divider()

# Consulta de deudores aprobados o condicionados desde Supabase
def obtener_clientes_aprobados():
    try:
        res = supabase.table("clientes").select("id_cliente, nombre_completo, rfc, estatus_admision").in_("estatus_admision", ["APROBADO", "CONDICIONADO"]).order("fecha_registro", desc=True).execute()
        return res.data if res.data else []
    except Exception:
        return []

clientes_db = obtener_clientes_aprobados()

# Construir opciones del selector dinámico
opciones_selector = ["-- Seleccione un Deudor Aprobado --"]
mapa_clientes = {}
for c in clientes_db:
    etiqueta = f"{c['nombre_completo']} | RFC: {c['rfc']} ({c['estatus_admision']})"
    opciones_selector.append(etiqueta)
    mapa_clientes[etiqueta] = c

col_param, col_resumen = st.columns([1, 1.5])

with col_param:
    st.subheader("Parámetros del Crédito")
    
    # Pre-seleccionar si el usuario viene redirigido del Módulo de Admisión
    index_defecto = 0
    if "expediente_activo" in st.session_state and st.session_state["expediente_activo"]:
        id_activo = st.session_state["expediente_activo"].get("id_cliente")
        for i, et in enumerate(opciones_selector[1:], start=1):
            if mapa_clientes[et]["id_cliente"] == id_activo:
                index_defecto = i
                break

    seleccion = st.selectbox("Expediente en Evaluación:", options=opciones_selector, index=index_defecto)
    
    with st.form("form_parametros_credito"):
        if seleccion != "-- Seleccione un Deudor Aprobado --":
            cliente_sel = mapa_clientes[seleccion]
            id_cliente = cliente_sel["id_cliente"]
            nombre_mostrar = cliente_sel["nombre_completo"]
            rfc_mostrar = cliente_sel["rfc"]
            
            # Recuperar parámetros previos si existen en sesión
            monto_init = 15000.0
            tasa_init = 6.0
            if "expediente_activo" in st.session_state and st.session_state["expediente_activo"].get("id_cliente") == id_cliente:
                monto_init = float(st.session_state["expediente_activo"].get("monto_aprobado", 15000.0))
                tasa_init = float(st.session_state["expediente_activo"].get("tasa_mensual", 0.06)) * 100.0
                
            st.text_input("Nombre del Deudor:", value=nombre_mostrar, disabled=True)
            st.text_input("RFC / ID Institucional:", value=f"{rfc_mostrar} | {id_cliente}", disabled=True)
            monto_principal = st.number_input("Monto a Otorgar ($):", min_value=1000.0, max_value=150000.0, value=monto_init, step=1000.0)
            tasa_mensual = st.number_input("Tasa de Interés Mensual (%):", min_value=1.0, max_value=15.0, value=tasa_init, step=0.5) / 100.0
            plazo_quincenas = st.selectbox("Número de Quincenas:", options=[6, 12, 18, 24], index=1)
            fecha_desembolso = st.date_input("Fecha Programada de Desembolso:", value=datetime.today())
        else:
            id_cliente = None
            st.info("Seleccione un expediente en el listado superior para habilitar los parámetros de cálculo.")
            monto_principal = st.number_input("Monto a Otorgar ($):", value=0.0, disabled=True)
            tasa_mensual = 0.0
            plazo_quincenas = 12
            fecha_desembolso = datetime.today()
            
        calcular = st.form_submit_button("Calculadora de Amortización Exacta", use_container_width=True)

with col_resumen:
    st.subheader("Dictamen Matemático y Contable")
    
    if seleccion == "-- Seleccione un Deudor Aprobado --":
        st.warning("Debe seleccionar un cliente aprobado para generar la tabla y proceder a la formalización.")
    else:
        # 1. Tasa proporcional quincenal
        tasa_quincenal = tasa_mensual / 2.0
        
        # 2. Fórmula de Anualidad Ordinaria
        if tasa_quincenal > 0:
            cuota_teorica = monto_principal * (tasa_quincenal * (1 + tasa_quincenal)**plazo_quincenas) / ((1 + tasa_quincenal)**plazo_quincenas - 1)
        else:
            cuota_teorica = monto_principal / plazo_quincenas
            
        cuota_fija = round(cuota_teorica, 2)
        
        # 3. Construcción iterativa con ajuste exacto a $0.00 al cierre
        saldo = round(float(monto_principal), 2)
        fecha_iter = datetime.combine(fecha_desembolso, datetime.min.time())
        
        tabla_pagos = []
        total_interes = 0.0
        total_capital = 0.0
        
        for q in range(1, plazo_quincenas + 1):
            fecha_iter += timedelta(days=15)
            interes_quincena = round(saldo * tasa_quincenal, 2)
            
            if q == plazo_quincenas:
                abono_capital = saldo
                cuota_real = round(abono_capital + interes_quincena, 2)
                saldo = 0.00
            else:
                cuota_real = cuota_fija
                abono_capital = round(cuota_real - interes_quincena, 2)
                saldo = round(saldo - abono_capital, 2)
                
            total_interes = round(total_interes + interes_quincena, 2)
            total_capital = round(total_capital + abono_capital, 2)
            
            tabla_pagos.append({
                "No. Quincena": q,
                "Fecha de Vencimiento": fecha_iter.strftime("%Y-%m-%d"),
                "Saldo Inicial ($)": f"{round(saldo + abono_capital, 2):,.2f}",
                "Cuota Fija ($)": f"{cuota_real:,.2f}",
                "Interés Cobrado ($)": f"{interes_quincena:,.2f}",
                "Abono a Capital ($)": f"{abono_capital:,.2f}",
                "Saldo Insoluto ($)": f"{saldo:,.2f}"
            })
            
        df_amortizacion = pd.DataFrame(tabla_pagos)
        total_recaudar = round(total_capital + total_interes, 2)
        
        # Exposición de KPIs
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Capital Otorgado", f"${total_capital:,.2f}")
        m2.metric("Interés Total Proyectado", f"${total_interes:,.2f}")
        m3.metric("Monto Total a Recaudar", f"${total_recaudar:,.2f}")
        m4.metric("Cuota Quincenal Base", f"${cuota_fija:,.2f}")
        
        st.markdown("---")
        
        if total_capital == round(monto_principal, 2):
            st.success("Verificación Contable Exitosa: Conciliación de capital exacta. Saldo insoluto al cierre liquidado a $0.00.")
        else:
            st.error("Discrepancia contable detectada en el redondeo.")
            
        # Preparar paquete de datos para formalización transaccional
        st.session_state["credito_calculado"] = {
            "id_cliente": id_cliente,
            "monto_principal": float(monto_principal),
            "tasa_interes_mensual": float(tasa_mensual),
            "plazo_quincenas": int(plazo_quincenas),
            "cuota_fija_proyectada": float(cuota_fija),
            "monto_total_recaudar": float(total_recaudar),
            "fecha_desembolso": fecha_desembolso.strftime("%Y-%m-%d"),
            "estatus_credito": "VIGENTE",
            "tabla_df": df_amortizacion
        }

st.divider()

# Sección de Exportación y Escritura Transaccional en Servidor
st.subheader("Calendario Detallado de Obligaciones (Anexo al Contrato)")

if "credito_calculado" in st.session_state and st.session_state["credito_calculado"]:
    df_mostrar = st.session_state["credito_calculado"]["tabla_df"]
    st.dataframe(df_mostrar, use_container_width=True)
    
    col_acc1, col_acc2 = st.columns([1, 1])
    with col_acc1:
        csv_export = df_mostrar.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Descargar Anexo Contable (CSV)",
            data=csv_export,
            file_name="tabla_amortizacion_legal.csv",
            mime="text/csv",
            use_container_width=True
        )
    with col_acc2:
        if st.button("Formalizar Contrato en Base de Datos (Supabase)", type="primary", use_container_width=True):
            with st.spinner("Ejecutando transacción contable en servidor..."):
                datos_c = st.session_state["credito_calculado"]
                payload_prestamo = {
                    "id_cliente": datos_c["id_cliente"],
                    "monto_principal": datos_c["monto_principal"],
                    "tasa_interes_mensual": datos_c["tasa_interes_mensual"],
                    "plazo_quincenas": datos_c["plazo_quincenas"],
                    "cuota_fija_proyectada": datos_c["cuota_fija_proyectada"],
                    "monto_total_recaudar": datos_c["monto_total_recaudar"],
                    "fecha_desembolso": datos_c["fecha_desembolso"],
                    "estatus_credito": datos_c["estatus_credito"]
                }
                try:
                    id_prestamo_gen = formalizar_credito_y_amortización(payload_prestamo, datos_c["tabla_df"])
                    st.success(f"Contrato formalizado exitosamente en el servidor. ID Institucional del Préstamo: {id_prestamo_gen}")
                    st.info("El calendario completo de pagos ha quedado registrado en la base de datos. Puede proceder al Módulo Legal o de Cobranza.")
                except Exception as e:
                    st.error(f"Fallo en la transacción de formalización: {str(e)}")
else:
    st.info("Configure los parámetros y presione el botón de cálculo para visualizar el calendario formal.")