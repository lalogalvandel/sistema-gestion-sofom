# =============================================================================
# Copyright (c) 2026 Eduardo Galván del Rio. Todos los derechos reservados.
# 
# Este código fuente es propiedad exclusiva y confidencial. Queda estrictamente
# prohibida su reproducción, distribución, comercialización o modificación
# sin autorización expresa y por escrito del autor.
# =============================================================================

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from src.db import supabase
from src.auth import verificar_acceso
from src.theme import (
    aplicar_identidad_visual, encabezado_modulo, titulo_seccion,
    dictamen
)

st.set_page_config(page_title="Amortización y Formalización | SOFOM", layout="wide")

# --- BLINDAJE INSTITUCIONAL RBAC ---
verificar_acceso("ORIGINACION_MESA") 
# -----------------------------------

aplicar_identidad_visual()

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
    subtitulo="Generación de corridas financieras con ajuste estricto a Días Hábiles Bancarios (CNBV) y tasas equivalentes.",
    nombre_icono="calendario",
    insignia="OPERACIONES FINANCIERAS"
)

# -----------------------------------------------------------------------------
# MOTOR DE CALENDARIO BANCARIO MÉXICO (LFT Y CNBV)
# -----------------------------------------------------------------------------
def calcular_semana_santa(anio):
    """Algoritmo de Computus para calcular Jueves y Viernes Santo (Inhábiles Bancarios)"""
    a = anio % 19
    b = anio // 100
    c = anio % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    
    domingo_pascua = date(anio, mes, dia)
    jueves_santo = domingo_pascua - timedelta(days=3)
    viernes_santo = domingo_pascua - timedelta(days=2)
    return jueves_santo, viernes_santo

def obtener_festivos_mexico(anio):
    """Genera el set de días inhábiles oficiales para un año específico"""
    festivos = set()
    
    # 1. Fijos de la LFT y CNBV
    festivos.add(date(anio, 1, 1))   # Año Nuevo
    festivos.add(date(anio, 5, 1))   # Día del Trabajo
    festivos.add(date(anio, 9, 16))  # Independencia
    festivos.add(date(anio, 11, 2))  # Día de Muertos (Inhábil Bancario)
    festivos.add(date(anio, 12, 12)) # Día del Empleado Bancario
    festivos.add(date(anio, 12, 25)) # Navidad

    # Transición del Poder Ejecutivo (1 de Octubre cada 6 años a partir de 2024)
    if (anio - 2024) % 6 == 0:
        festivos.add(date(anio, 10, 1))

    # 2. Móviles de la LFT (Lunes)
    # Primer lunes de febrero (Constitución)
    feb_1 = date(anio, 2, 1)
    dias_para_lunes = (0 - feb_1.weekday()) % 7
    festivos.add(feb_1 + timedelta(days=dias_para_lunes))
    
    # Tercer lunes de marzo (Natalicio Juárez)
    mar_1 = date(anio, 3, 1)
    dias_para_lunes = (0 - mar_1.weekday()) % 7
    festivos.add(mar_1 + timedelta(days=dias_para_lunes + 14))
    
    # Tercer lunes de noviembre (Revolución)
    nov_1 = date(anio, 11, 1)
    dias_para_lunes = (0 - nov_1.weekday()) % 7
    festivos.add(nov_1 + timedelta(days=dias_para_lunes + 14))
    
    # 3. Semana Santa (Bancario)
    jueves_santo, viernes_santo = calcular_semana_santa(anio)
    festivos.add(jueves_santo)
    festivos.add(viernes_santo)
    
    return festivos

def ajustar_a_dia_habil(fecha_evaluada):
    """Evalúa iterativamente si la fecha es fin de semana o festivo CNBV y la empuja al siguiente día hábil"""
    fecha_actual = fecha_evaluada.date() if isinstance(fecha_evaluada, datetime) else fecha_evaluada
    
    while True:
        es_fin_semana = fecha_actual.weekday() >= 5 # 5=Sábado, 6=Domingo
        festivos_del_anio = obtener_festivos_mexico(fecha_actual.year)
        es_festivo = fecha_actual in festivos_del_anio
        
        if es_fin_semana or es_festivo:
            fecha_actual += timedelta(days=1)
        else:
            break
            
    if isinstance(fecha_evaluada, datetime):
        return datetime.combine(fecha_actual, fecha_evaluada.time())
    return fecha_actual

# -----------------------------------------------------------------------------
# 1. LECTURA DE CARTERA APROBADA
# -----------------------------------------------------------------------------
@st.cache_data(ttl=15)
def obtener_clientes_aprobados():
    try:
        res = supabase.table("prestamos").select("id_prestamo, id_cliente, monto_principal, tasa_interes_mensual, estatus, clientes(nombre_completo, rfc)").in_("estatus", ["PENDIENTE_APROBACION", "APROBADO", "APROBADO PREFERENCIAL", "APROBADO CONDICIONADO"]).order("fecha_otorgamiento", desc=True).execute()
        
        if not res.data:
            return []
            
        clientes_formateados = []
        for p in res.data:
            cli_data = p.get("clientes") or {}
            clientes_formateados.append({
                "id_prestamo": p.get("id_prestamo"),
                "id_cliente": p.get("id_cliente") or cli_data.get("rfc") or "SIN-ID",
                "nombre_completo": cli_data.get("nombre_completo", "Deudor sin nombre"),
                "rfc": cli_data.get("rfc", "XAXX010101000"),
                "estatus_admision": p.get("estatus", "APROBADO"),
                "monto_aprobado": p.get("monto_principal", 15000.0),
                "tasa_mensual": p.get("tasa_interes_mensual", 6.0)
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
            
            monto_init = float(cliente_sel.get("monto_aprobado", 15000.0))
            val_tasa = float(cliente_sel.get("tasa_mensual", 6.0))
            tasa_init = val_tasa if val_tasa > 1.0 else round(val_tasa * 100.0, 2)
            
            st.text_input("Acreditado Titular:", value=nombre_mostrar, disabled=True)
            st.text_input("ID Préstamo (UUID):", value=id_prestamo_activo, disabled=True)
            monto_principal = st.number_input("Monto Principal ($):", min_value=1000.0, max_value=150000.0, value=monto_init, step=1000.0)
            tasa_mensual = st.number_input("Tasa Ordinaria Mensual (%):", min_value=1.0, max_value=15.0, value=tasa_init, step=0.5) / 100.0
            
            frecuencia_pago = st.selectbox("Periodicidad de Pago:", ["Mensual", "Quincenal", "Semanal"], index=1)
            plazo_periodos = st.number_input(f"Plazo (Número de Cuotas {frecuencia_pago}es):", min_value=1, max_value=72, value=12, step=1)
            fecha_desembolso = st.date_input("Fecha Base de Desembolso:", value=datetime.today())
        else:
            id_prestamo_activo = None
            id_cliente = None
            st.info("Seleccione un expediente en la parte superior para calibrar la estructuración.")
            monto_principal = st.number_input("Monto Principal ($):", value=0.0, disabled=True)
            tasa_mensual = 0.0
            frecuencia_pago = "Quincenal"
            plazo_periodos = 12
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
        if frecuencia_pago == "Mensual":
            tasa_periodo = tasa_mensual
            dias_sumar = 30
        elif frecuencia_pago == "Quincenal":
            tasa_periodo = (1.0 + tasa_mensual)**(1.0/2.0) - 1.0
            dias_sumar = 15
        else: # Semanal
            tasa_periodo = (1.0 + tasa_mensual)**(1.0/4.0) - 1.0
            dias_sumar = 7
            
        if tasa_periodo > 0:
            cuota_teorica = monto_principal * (tasa_periodo * (1 + tasa_periodo)**plazo_periodos) / ((1 + tasa_periodo)**plazo_periodos - 1)
        else:
            cuota_teorica = monto_principal / plazo_periodos
            
        cuota_fija = round(cuota_teorica, 2)
        saldo = round(float(monto_principal), 2)
        
        fecha_iter_base = datetime.combine(fecha_desembolso, datetime.min.time())
        
        tabla_pagos_display = []
        tabla_pagos_sql = []
        total_interes, total_capital = 0.0, 0.0
        
        for q in range(1, plazo_periodos + 1):
            fecha_iter_base += timedelta(days=dias_sumar)
            # MAGIA: Rueda automáticamente al siguiente día hábil bancario
            fecha_cobro_oficial = ajustar_a_dia_habil(fecha_iter_base)
            
            interes_quincena = round(saldo * tasa_periodo, 2)
            
            if q == plazo_periodos:
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
            fecha_str = fecha_cobro_oficial.strftime("%Y-%m-%d")
            
            tabla_pagos_display.append({
                "No.": q, "Vencimiento": fecha_str, "Saldo Inicial": f"${saldo_inicial_iter:,.2f}",
                "Cuota Fija": f"${cuota_real:,.2f}", "Interés": f"${interes_quincena:,.2f}",
                "Abono Capital": f"${abono_capital:,.2f}", "Saldo Insoluto": f"${saldo:,.2f}"
            })
            
            tabla_pagos_sql.append({
                "id_prestamo": id_prestamo_activo, "numero_cuota": q, "fecha_vencimiento": fecha_str,
                "saldo_inicial": saldo_inicial_iter, "cuota_fija": cuota_real, "interes_cobrado": interes_quincena,
                "abono_capital": abono_capital, "saldo_insoluto": saldo, "estatus_pago": "PENDIENTE"
            })
            
        df_amortizacion_display = pd.DataFrame(tabla_pagos_display)
        total_recaudar = round(total_capital + total_interes, 2)
        
        m1, m2 = st.columns(2)
        with m1: st.metric(label="Capital a Financiar", value=f"${total_capital:,.2f}")
        with m2: st.metric(label="Costo Financiero (Interés)", value=f"${total_interes:,.2f}")
            
        st.markdown("<br>", unsafe_allow_html=True)
        m3, m4 = st.columns(2)
        with m3: st.metric(label="Obligación Total a Exigir", value=f"${total_recaudar:,.2f}")
        with m4: st.metric(label=f"Cuota {frecuencia_pago} Nivelada", value=f"${cuota_fija:,.2f}")
        
        st.markdown("---")
        
        if total_capital == round(monto_principal, 2):
            dictamen("exito", "Cuadratura CNBV Exacta", "Sistema Francés validado y calibrado a días hábiles bancarios (Ley Federal del Trabajo y CNBV).")
        else:
            dictamen("peligro", "Discrepancia Detectada", "Error de redondeo exponencial. Revise los parámetros.")
            
        st.session_state["credito_calculado"] = {
            "id_prestamo": id_prestamo_activo, "id_cliente": id_cliente, "monto_principal": float(monto_principal),
            "plazo_quincenas": int(plazo_periodos), "cuota_fija_proyectada": float(cuota_fija), "monto_total_recaudar": float(total_recaudar),
            "frecuencia": frecuencia_pago, "fecha_desembolso": fecha_desembolso.strftime("%Y-%m-%d"),
            "tabla_df_display": df_amortizacion_display, "tabla_sql_raw": tabla_pagos_sql
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
        st.download_button(label="📥 Descargar Anexo CSV", data=csv_export, file_name="tabla_amortizacion_legal.csv", mime="text/csv", width="stretch")
    with col_acc2:
        if st.button("Consolidar Expediente y Turnar a Mesa Legal", type="primary", width="stretch"):
            with st.spinner("Inscribiendo plan de pagos estricto en base de datos..."):
                datos_c = st.session_state["credito_calculado"]
                id_target = datos_c["id_prestamo"]
                
                try:
                    payload_actualizacion = {
                        "plazo_quincenas": int(datos_c["plazo_quincenas"]), "cuota_fija_proyectada": float(datos_c["cuota_fija_proyectada"]),
                        "monto_total_recaudar": float(datos_c["monto_total_recaudar"]), "frecuencia": datos_c["frecuencia"],
                        "fecha_desembolso": datos_c["fecha_desembolso"], "estatus": "ESTRUCTURADO"
                    }
                    supabase.table("prestamos").update(payload_actualizacion).eq("id_prestamo", id_target).execute()
                    
                    cuotas_sql = datos_c["tabla_sql_raw"]
                    supabase.table("plan_amortizacion").delete().eq("id_prestamo", id_target).execute() 
                    supabase.table("plan_amortizacion").insert(cuotas_sql).execute()
                    
                    dictamen("exito", "Estructuración Contable Completa", "El calendario de pagos ha sido indexado. Los vencimientos evitan fines de semana y festivos oficiales.")
                    st.info("**Siguiente paso:** Proceda al módulo de 'Contratos y Legal' para emitir el Pagaré Mercantil.")
                    
                    del st.session_state["credito_calculado"]
                except Exception as e:
                    dictamen("peligro", "Fallo de Servidor", f"No se pudo completar la transacción SQL: {str(e)}")
else:
    st.info("Proyecte la corrida financiera en el panel superior para habilitar el anexo contable y las acciones legales.")