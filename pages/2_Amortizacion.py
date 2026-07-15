import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Configuración institucional de la página
st.set_page_config(page_title="Motor de Amortizacion | SOFOM", layout="wide")

st.title("Motor de Amortización y Calendario de Pagos")
st.markdown("Generación de tablas de cobro bajo el Sistema Francés (cuotas fijas) y conciliación de saldos insolutos.")
st.divider()

# Verificación y carga de cartera aprobada desde memoria o base de datos
if 'cartera_temporal' not in st.session_state or not st.session_state.cartera_temporal:
    st.info("No hay créditos en memoria temporal en esta sesión. Puede utilizar el modo de simulación manual a continuación.")
    clientes_disponibles = ["Simulación Manual de Crédito"]
else:
    clientes_disponibles = ["Simulación Manual de Crédito"] + [f"{c['Cliente']} | {c['Monto']}" for c in st.session_state.cartera_temporal]

# Panel de Configuración del Préstamo
col_param, col_resumen = st.columns([1, 1.5])

with col_param:
    st.subheader("Parámetros de Cálculo")
    seleccion = st.selectbox("Seleccione Expediente o Modo de Operación:", options=clientes_disponibles)
    
    with st.form("form_amortizacion"):
        if seleccion == "Simulación Manual de Crédito":
            nombre_cliente = st.text_input("Nombre del Deudor / Solicitante:", value="Cliente de Prueba")
            monto_principal = st.number_input("Monto del Préstamo ($):", min_value=1000.0, value=15000.0, step=500.0)
            tasa_mensual = st.number_input("Tasa de Interés Mensual (%):", min_value=1.0, value=6.0, step=0.5) / 100.0
            plazo_quincenas = st.selectbox("Número de Quincenas:", options=[6, 12, 18, 24], index=1)
        else:
            # Extraer datos de la sesión temporal si se seleccionó un cliente previamente aprobado
            idx_cliente = clientes_disponibles.index(seleccion) - 1
            data_cliente = st.session_state.cartera_temporal[idx_cliente]
            nombre_cliente = data_cliente["Cliente"]
            monto_limpio = float(data_cliente["Monto"].replace("$", "").replace(",", ""))
            
            st.text_input("Nombre del Deudor / Solicitante:", value=nombre_cliente, disabled=True)
            monto_principal = st.number_input("Monto del Préstamo ($):", value=monto_limpio, disabled=True)
            tasa_mensual = st.number_input("Tasa de Interés Mensual (%):", min_value=1.0, value=6.0, step=0.5) / 100.0
            plazo_quincenas = st.selectbox("Número de Quincenas:", options=[6, 12, 18, 24], index=1)
            
        fecha_desembolso = st.date_input("Fecha Programada de Desembolso:", value=datetime.today())
        calcular = st.form_submit_button("Generar Calendario de Pagos", use_container_width=True)

# Motor de Álgebra Financiera y Conciliación
with col_resumen:
    st.subheader("Resumen Ejecutivo de Obligaciones")
    
    # 1. Tasa proporcional quincenal
    tasa_quincenal = tasa_mensual / 2.0
    
    # 2. Fórmula de Anualidad Ordinaria
    if tasa_quincenal > 0:
        cuota_teorica = monto_principal * (tasa_quincenal * (1 + tasa_quincenal)**plazo_quincenas) / ((1 + tasa_quincenal)**plazo_quincenas - 1)
    else:
        cuota_teorica = monto_principal / plazo_quincenas
        
    cuota_fija = round(cuota_teorica, 2)
    
    # 3. Construcción iterativa de la tabla con ajuste exacto al final
    saldo = round(float(monto_principal), 2)
    fecha_iteracion = datetime.combine(fecha_desembolso, datetime.min.time())
    
    tabla_pagos = []
    total_interes = 0.0
    total_capital = 0.0
    
    for q in range(1, plazo_quincenas + 1):
        fecha_iteracion += timedelta(days=15)
        interes_quincena = round(saldo * tasa_quincenal, 2)
        
        # Algoritmo de ajuste en el último periodo para evitar arrastre de centavos
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
            "Fecha de Vencimiento": fecha_iteracion.strftime("%Y-%m-%d"),
            "Saldo Inicial ($)": f"{round(saldo + abono_capital, 2):,.2f}",
            "Cuota Fija ($)": f"{cuota_real:,.2f}",
            "Interés Cobrado ($)": f"{interes_quincena:,.2f}",
            "Abono a Capital ($)": f"{abono_capital:,.2f}",
            "Saldo Insoluto ($)": f"{saldo:,.2f}",
            "Estatus Contable": "PENDIENTE"
        })
        
    df_amortizacion = pd.DataFrame(tabla_pagos)
    total_a_pagar = round(total_capital + total_interes, 2)
    
    # Exposición de KPIs Financieros del Crédito
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Capital Otorgado", f"${total_capital:,.2f}")
    m2.metric("Interés Total Proyectado", f"${total_interes:,.2f}")
    m3.metric("Monto Total a Recaudar", f"${total_a_pagar:,.2f}")
    m4.metric("Cuota Quincenal Base", f"${cuota_fija:,.2f}")
    
    st.markdown("---")
    
    # Validación de Integridad Contable
    if total_capital == round(monto_principal, 2):
        st.success("Verificación Contable Exitosa: La suma del capital amortizado coincide exactamente con el principal otorgado. Saldo insoluto liquidado a $0.00.")
    else:
        st.error("Alerta Contable: Discrepancia detectada en el redondeo del capital.")

st.divider()

# Sección 3: Desglose Tabular y Exportación
st.subheader("Calendario Detallado de Amortización (Contrato Legal)")
st.dataframe(df_amortizacion, use_container_width=True)

col_exp1, col_exp2 = st.columns(2)
with col_exp1:
    csv_export = df_amortizacion.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Descargar Tabla de Amortización (CSV)",
        data=csv_export,
        file_name=f"Amortizacion_{nombre_cliente.replace(' ', '_')}.csv",
        mime="text/csv",
        use_container_width=True
    )
with col_exp2:
    st.button("Preparar Datos para Emisión de Pagaré Legal", type="primary", use_container_width=True)