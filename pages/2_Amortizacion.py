# =============================================================================
# Copyright (c) 2026 Eduardo Galván del Río. Todos los derechos reservados.
# 
# Este código fuente es propiedad exclusiva y confidencial. Queda estrictamente
# prohibida su reproducción, distribución, comercialización o modificación
# sin autorización expresa y por escrito del autor.
# =============================================================================

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.db import supabase
from src.auth import verificar_acceso
from src.theme import (
    aplicar_identidad_visual, encabezado_modulo, titulo_seccion,
    dictamen
)

st.set_page_config(page_title="Amortización y Formalización | SOFOM", layout="wide")

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
    titulo="Motor de Amortización y Estructuración",
    subtitulo="Generación de corridas financieras e inscripción del plan de pagos en base de datos.",
    nombre_icono="calendario",
    insignia="OPERACIONES FINANCIERAS"
)

# -----------------------------------------------------------------------------
# 1. LECTURA DE CARTERA APROBADA
# -----------------------------------------------------------------------------
@st.cache_data(ttl=15)
def obtener_clientes_aprobados():
    try:
        res = supabase.table("prestamos").select("*").in_("estatus", ["APROBADO", "APROBADO PREFERENCIAL", "APROBADO CONDICIONADO"]).order("fecha_otorgamiento", desc=True).execute()
        
        if not res.data:
            return []
            
        clientes_formateados = []
        for p in res.data:
            clientes_formateados.append({
                "id_prestamo": p.get("id_prestamo"), # <-- CRÍTICO: La llave foránea
                "id_cliente": p.get("id_cliente") or p.get("rfc") or "SIN-ID",
                "nombre_completo": p.get("cliente", "Deudor sin nombre"),
                "rfc": p.get("rfc", "XAXX010101000"),
                "estatus_admision": p.get("estatus", "APROBADO"),
                "monto_aprobado": p.get("monto", p.get("saldo_pendiente", 15000.0)),
                "tasa_mensual": p.get("tasa_mensual", 6.0)
            })
        return clientes_formateados
    except Exception as e:
        return []

clientes_db = obtener_clientes_aprobados()

opciones_selector = ["-- Seleccione un Deudor Aprobado --"]
mapa_clientes = {}
for c in clientes_db:
    etiqueta = f"{c['nombre_completo']} | RFC: {c['rfc']} ({c['estatus_admision']})"
    opciones_selector.append(etiqueta)
    mapa_clientes[etiqueta] = c

col_param, col_resumen = st.columns([1, 1.4])

# -----------------------------------------------------------------------------
# 2. PARÁMETROS DEL CRÉDITO
# -----------------------------------------------------------------------------
with col_param:
    titulo_seccion("personas", "PARÁMETROS DE ESTRUCTURACIÓN")
    
    index_defecto = 0
    if "expediente_activo" in st.session_state and st.session_state["expediente_activo"]:
        id_activo = st.session_state["expediente_activo"].get("id_cliente")
        for i, et in enumerate(opciones_selector[1:], start=1):
            if mapa_clientes[et]["id_cliente"] == id_activo:
                index_defecto = i
                break

    seleccion = st.selectbox("Expediente Aprobado:", options=opciones_selector, index=index_defecto)
    
    with st.form("form_parametros_credito"):
        if seleccion != "-- Seleccione un Deudor Aprobado --":
            cliente_sel = mapa_clientes[seleccion]
            id_prestamo_activo = cliente_sel["id_prestamo"]
            id_cliente = cliente_sel["id_cliente"]
            nombre_mostrar = cliente_sel["nombre_completo"]
            rfc_mostrar = cliente_sel["rfc"]
            
            monto_init = float(cliente_sel.get("monto_aprobado", 15000.0))
            val_tasa = float(cliente_sel.get("tasa_mensual", 6.0))
            tasa_init = val_tasa if val_tasa > 1.0 else round(val_tasa * 100.0, 2)
            
            st.text_input("Acreditado Titular:", value=nombre_mostrar, disabled=True)
            st.text_input("ID Préstamo (UUID):", value=id_prestamo_activo, disabled=True)
            monto_principal = st.number_input("Monto Principal ($):", min_value=1000.0, max_value=150000.0, value=monto_init, step=1000.0)
            tasa_mensual = st.number_input("Tasa Ordinaria Mensual (%):", min_value=1.0, max_value=15.0, value=tasa_init, step=0.5) / 100.0
            plazo_quincenas = st.selectbox("Plazo de Amortización (Quincenas):", options=[6, 12, 18, 24], index=1)
            fecha_desembolso = st.date_input("Fecha Base de Desembolso:", value=datetime.today())
        else:
            id_prestamo_activo = None
            id_cliente = None
            st.info("Seleccione un expediente en la parte superior para calibrar la estructuración.")
            monto_principal = st.number_input("Monto Principal ($):", value=0.0, disabled=True)
            tasa_mensual = 0.0
            plazo_quincenas = 12
            fecha_desembolso = datetime.today()
            
        calcular = st.form_submit_button("Proyectar Corrida Financiera", width='stretch')

# -----------------------------------------------------------------------------
# 3. DICTAMEN MATEMÁTICO (KPIs INSTITUCIONALES)
# -----------------------------------------------------------------------------
with col_resumen:
    titulo_seccion("balanza", "CONCILIACIÓN MATEMÁTICA")
    
    if seleccion == "-- Seleccione un Deudor Aprobado --":
        st.info("El dictamen contable se generará automáticamente tras proyectar la corrida financiera.")
    else:
        tasa_quincenal = tasa_mensual / 2.0
        
        if tasa_quincenal > 0:
            cuota_teorica = monto_principal * (tasa_quincenal * (1 + tasa_quincenal)**plazo_quincenas) / ((1 + tasa_quincenal)**plazo_quincenas - 1)
        else:
            cuota_teorica = monto_principal / plazo_quincenas
            
        cuota_fija = round(cuota_teorica, 2)
        saldo = round(float(monto_principal), 2)
        fecha_iter = datetime.combine(fecha_desembolso, datetime.min.time())
        
        tabla_pagos_display = []
        tabla_pagos_sql = [] # <-- CRÍTICO: Lista pura para Inserción SQL
        total_interes, total_capital = 0.0, 0.0
        
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
            saldo_inicial_iter = round(saldo + abono_capital, 2)
            fecha_str = fecha_iter.strftime("%Y-%m-%d")
            
            # Tabla para UI (Formato Humano)
            tabla_pagos_display.append({
                "No.": q,
                "Vencimiento": fecha_str,
                "Saldo Inicial": f"${saldo_inicial_iter:,.2f}",
                "Cuota Fija": f"${cuota_real:,.2f}",
                "Interés": f"${interes_quincena:,.2f}",
                "Abono Capital": f"${abono_capital:,.2f}",
                "Saldo Insoluto": f"${saldo:,.2f}"
            })
            
            # Tabla para Base de Datos (Puros floats numéricos y strings limpios)
            tabla_pagos_sql.append({
                "id_prestamo": id_prestamo_activo,
                "numero_cuota": q,
                "fecha_vencimiento": fecha_str,
                "saldo_inicial": saldo_inicial_iter,
                "cuota_fija": cuota_real,
                "interes_cobrado": interes_quincena,
                "abono_capital": abono_capital,
                "saldo_insoluto": saldo,
                "estatus_pago": "PENDIENTE"
            })
            
        df_amortizacion_display = pd.DataFrame(tabla_pagos_display)
        total_recaudar = round(total_capital + total_interes, 2)
        
        m1, m2 = st.columns(2)
        with m1: st.metric(label="Capital a Financiar", value=f"${total_capital:,.2f}")
        with m2: st.metric(label="Costo Financiero (Interés)", value=f"${total_interes:,.2f}")
            
        st.markdown("<br>", unsafe_allow_html=True)
        m3, m4 = st.columns(2)
        with m3: st.metric(label="Obligación Total a Exigir", value=f"${total_recaudar:,.2f}")
        with m4: st.metric(label="Cuota Quincenal Nivelada", value=f"${cuota_fija:,.2f}")
        
        st.markdown("---")
        
        if total_capital == round(monto_principal, 2):
            dictamen("exito", "Cuadratura Exacta", "Sistema Francés validado. Saldo insoluto liquidado a $0.00 en la última iteración.")
        else:
            dictamen("peligro", "Discrepancia Detectada", "Error de redondeo de capital. Revise los parámetros.")
            
        # Guardamos ambas versiones en memoria
        st.session_state["credito_calculado"] = {
            "id_prestamo": id_prestamo_activo,
            "id_cliente": id_cliente,
            "monto_principal": float(monto_principal),
            "plazo_quincenas": int(plazo_quincenas),
            "cuota_fija_proyectada": float(cuota_fija),
            "monto_total_recaudar": float(total_recaudar),
            "fecha_desembolso": fecha_desembolso.strftime("%Y-%m-%d"),
            "tabla_df_display": df_amortizacion_display,
            "tabla_sql_raw": tabla_pagos_sql
        }

st.divider()

# -----------------------------------------------------------------------------
# 4. ANEXO CONTABLE E INSERCIÓN EN BD
# -----------------------------------------------------------------------------
titulo_seccion("documento", "ANEXO CONTABLE Y PASE A JURÍDICO")

if "credito_calculado" in st.session_state and st.session_state["credito_calculado"]:
    df_mostrar = st.session_state["credito_calculado"]["tabla_df_display"]
    st.dataframe(df_mostrar, width="stretch", hide_index=True)
    
    col_acc1, col_acc2 = st.columns([1, 1.2])
    with col_acc1:
        csv_export = df_mostrar.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Anexo CSV",
            data=csv_export,
            file_name="tabla_amortizacion_legal.csv",
            mime="text/csv",
            width="stretch"
        )
    with col_acc2:
        if st.button("Consolidar Expediente y Turnar a Mesa Legal", type="primary", width="stretch"):
            with st.spinner("Inscribiendo plan de pagos en base de datos..."):
                datos_c = st.session_state["credito_calculado"]
                id_target = datos_c["id_prestamo"]
                
                try:
                    # 1. Actualizamos el préstamo principal (Limpieza de duplicidades en columnas)
                    payload_actualizacion = {
                        "plazo_quincenas": int(datos_c["plazo_quincenas"]),
                        "cuota_fija_proyectada": float(datos_c["cuota_fija_proyectada"]),
                        "monto_total_recaudar": float(datos_c["monto_total_recaudar"]),
                        "fecha_desembolso": datos_c["fecha_desembolso"],
                        "estatus": "ESTRUCTURADO"
                    }
                    
                    supabase.table("prestamos").update(payload_actualizacion).eq("id_prestamo", id_target).execute()
                    
                    # 2. INSERCIÓN MASIVA DEL PLAN DE PAGOS (El corazón del sistema)
                    cuotas_sql = datos_c["tabla_sql_raw"]
                    # Limpiamos primero por si el oficial está recalculando un crédito ya guardado
                    supabase.table("plan_amortizacion").delete().eq("id_prestamo", id_target).execute() 
                    # Insertamos las cuotas frescas
                    supabase.table("plan_amortizacion").insert(cuotas_sql).execute()
                    
                    dictamen("exito", "Estructuración Contable Completa", "El calendario de pagos se talló en piedra en la tabla `plan_amortizacion`. El expediente cambió a estatus ESTRUCTURADO.")
                    st.info("**Siguiente paso:** Proceda al módulo de 'Contratos y Legal' para emitir el Pagaré Mercantil.")
                    
                    del st.session_state["credito_calculado"]
                    
                except Exception as e:
                    dictamen("peligro", "Fallo de Servidor", f"No se pudo completar la transacción SQL: {str(e)}")
else:
    st.info("Proyecte la corrida financiera en el panel superior para habilitar el anexo contable y las acciones legales.")