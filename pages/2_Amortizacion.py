import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.db import supabase, formalizar_credito_y_amortización
from src.theme import (
    aplicar_identidad_visual, encabezado_modulo, titulo_seccion,
    dictamen, tarjeta_kpi
)

st.set_page_config(page_title="Amortización y Formalización | SOFOM", layout="wide")
from src.auth import verificar_acceso
verificar_acceso("COBRANZA")
# 1. Inyectar identidad visual
aplicar_identidad_visual()

encabezado_modulo(
    titulo="Motor de Amortización y Formalización",
    subtitulo="Generación de calendarios bajo el Sistema Francés y registro transaccional en PostgreSQL.",
    nombre_icono="calendario",
    insignia="SISTEMA FRANCÉS"
)

def obtener_clientes_aprobados():
    try:
        # 1. Leemos directamente de la tabla 'prestamos' donde guardamos las colocaciones del Módulo 1
        res = supabase.table("prestamos").select("*").in_("estatus", ["ACTIVO", "VIGENTE", "APROBADO", "APROBADO PREFERENCIAL", "APROBADO CONDICIONADO"]).execute()
        
        if not res.data:
            return []
            
        # 2. Mapeamos las columnas de 'prestamos' al formato que espera este módulo de amortización
        clientes_formateados = []
        for p in res.data:
            clientes_formateados.append({
                "id_cliente": p.get("id_cliente") or p.get("rfc") or p.get("id_prestamo", "SIN-ID"),
                "nombre_completo": p.get("cliente", "Deudor sin nombre"),
                "rfc": p.get("rfc", "XAXX010101000"),
                "estatus_admision": p.get("estatus", "ACTIVO"),
                # Extraemos también el monto y la tasa para que el formulario se llene solo:
                "monto_aprobado": p.get("monto", p.get("saldo_pendiente", 15000.0)),
                "tasa_mensual": p.get("tasa_mensual", 6.0)
            })
        return clientes_formateados
    except Exception as e:
        # Si algo falla en la red, devolvemos lista vacía sin romper la pantalla
        return []

clientes_db = obtener_clientes_aprobados()

opciones_selector = ["-- Seleccione un Deudor Aprobado --"]
mapa_clientes = {}
for c in clientes_db:
    etiqueta = f"{c['nombre_completo']} | RFC: {c['rfc']} ({c['estatus_admision']})"
    opciones_selector.append(etiqueta)
    mapa_clientes[etiqueta] = c

col_param, col_resumen = st.columns([1, 1.4])

with col_param:
    titulo_seccion("personas", "1. Parámetros del Crédito")
    
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
            
            # Tomamos los valores directos que vienen de la base de datos de colocación
            monto_init = float(cliente_sel.get("monto_aprobado", 15000.0))
            
            # Ajustamos la tasa por si viene en decimal (0.015) o en porcentaje directo (1.5)
            val_tasa = float(cliente_sel.get("tasa_mensual", 6.0))
            tasa_init = val_tasa if val_tasa > 1.0 else round(val_tasa * 100.0, 2)
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
    titulo_seccion("balanza", "2. Dictamen Matemático y Contable")
    
    if seleccion == "-- Seleccione un Deudor Aprobado --":
        dictamen("alerta", "Selección Pendiente", "Debe seleccionar un cliente aprobado en el menú desplegable para generar la tabla de amortización y proceder a la formalización contractual.")
    else:
        tasa_quincenal = tasa_mensual / 2.0
        
        if tasa_quincenal > 0:
            cuota_teorica = monto_principal * (tasa_quincenal * (1 + tasa_quincenal)**plazo_quincenas) / ((1 + tasa_quincenal)**plazo_quincenas - 1)
        else:
            cuota_teorica = monto_principal / plazo_quincenas
            
        cuota_fija = round(cuota_teorica, 2)
        
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
        
        # Cuadrícula simétrica 2x2 con tarjetas KPI institucionales
        m1, m2 = st.columns(2)
        with m1:
            tarjeta_kpi("billetera", "Capital Otorgado", f"${total_capital:,.2f}", "Monto original del desembolso", "marino_800")
        with m2:
            tarjeta_kpi("porcentaje", "Interés Total Proyectado", f"${total_interes:,.2f}", "Costo financiero a lo largo del plazo", "dorado_600")
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        m3, m4 = st.columns(2)
        with m3:
            tarjeta_kpi("banco", "Monto Total a Recaudar", f"${total_recaudar:,.2f}", "Suma exacta del pagaré ejecutivo", "azul_600")
        with m4:
            tarjeta_kpi("calendario", "Cuota Quincenal Base", f"${cuota_fija:,.2f}", "Pago recurrente constante", "verde_lago")
        
        st.markdown("---")
        
        if total_capital == round(monto_principal, 2):
            dictamen("exito", "Verificación Contable Exitosa", "Conciliación de capital exacta bajo el Sistema Francés. Saldo insoluto al cierre liquidado matemáticamente a $0.00.")
        else:
            dictamen("peligro", "Discrepancia Contable", "Se ha detectado una diferencia en el redondeo de centavos del capital. Revise las tasas aplicadas.")
            
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

titulo_seccion("documento", "3. Calendario Detallado de Obligaciones (Anexo al Contrato)")

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
                    dictamen("exito", "Contrato Formalizado Exitosamente en Supabase", f"ID Institucional del Préstamo: {id_prestamo_gen}. El calendario completo de pagos ha quedado registrado en la base de datos. Puede proceder al Módulo Legal o de Cobranza.")
                except Exception as e:
                    dictamen("peligro", "Fallo en Transacción", f"No se pudo completar la formalización contractual en el servidor: {str(e)}")
else:
    st.info("Configure los parámetros y presione el botón de cálculo para visualizar el calendario formal.")