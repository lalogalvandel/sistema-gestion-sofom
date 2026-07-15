import streamlit as st
import pandas as pd
from src.db import supabase, registrar_cliente
from src.theme import (
    aplicar_identidad_visual, encabezado_modulo, titulo_seccion,
    dictamen, tarjeta_kpi
)

st.set_page_config(page_title="Motor de Scoring | SOFOM", layout="wide")

# 1. Inyectar identidad visual y encabezado modular
aplicar_identidad_visual()

encabezado_modulo(
    titulo="Motor Cuantitativo de Admisión y Scoring",
    subtitulo="Evaluación algorítmica de riesgo de liquidez y registro transaccional de solicitantes en base de datos.",
    nombre_icono="balanza",
    insignia="SCORING ALGORÍTMICO"
)

col_form, col_res = st.columns([1, 1.4])

with col_form:
    titulo_seccion("personas", "1. Expediente del Solicitante")
    with st.form("form_admision", clear_on_submit=False):
        nombre = st.text_input("Nombre Completo del Deudor:", placeholder="Ej. Juan Pérez López")
        rfc = st.text_input("RFC con Homoclave (13 dígitos):", max_chars=13, placeholder="PELJ800101XYZ").upper()
        
        st.markdown("---")
        st.markdown("#### Parámetros Financieros Comprobados")
        ingreso = st.number_input("Ingreso Neto Comprobado ($):", min_value=0.0, value=0.0, step=1000.0)
        gastos = st.number_input("Gastos Fijos Estimados ($):", min_value=0.0, value=0.0, step=500.0)
        deudas = st.number_input("Pago Mensual de Deudas en Buró ($):", min_value=0.0, value=0.0, step=500.0)
        puntaje = st.slider("Puntaje en Buró de Crédito (Score):", min_value=300, max_value=850, value=650, step=10)
        
        st.markdown("---")
        st.markdown("#### Solicitud de Crédito")
        monto = st.number_input("Monto Solicitado ($):", min_value=1000.0, max_value=150000.0, value=15000.0, step=1000.0)
        plazo_quincenas = st.selectbox("Plazo de Pago (Quincenas):", options=[6, 12, 18, 24], index=1)
        tasa_mensual = st.number_input("Tasa de Interés Mensual (%):", min_value=1.0, max_value=15.0, value=6.0, step=0.5) / 100.0
        
        evaluar = st.form_submit_button("Ejecutar Evaluación Algorítmica", use_container_width=True)

with col_res:
    titulo_seccion("escudo", "2. Dictamen del Motor y Registro")
    
    if evaluar:
        if not nombre or len(rfc) < 12:
            dictamen("alerta", "Datos Incompletos", "Por favor ingrese un Nombre válido y un RFC de al menos 12 caracteres para proceder con la evaluación.")
        elif ingreso <= 0:
            dictamen("alerta", "Ingreso Inválido", "El ingreso neto comprobado debe ser mayor a $0.00 para calcular la capacidad de pago.")
        else:
            flujo_libre = ingreso - gastos - deudas
            capacidad_pago_quincenal = (flujo_libre * 0.30) / 2.0
            
            tasa_quincenal = tasa_mensual / 2.0
            cuota_proyectada = monto * (tasa_quincenal * (1 + tasa_quincenal)**plazo_quincenas) / ((1 + tasa_quincenal)**plazo_quincenas - 1)
            ratio_compromiso = cuota_proyectada / (flujo_libre / 2.0) if flujo_libre > 0 else 1.0
            
            # Cuadrícula 2x2 sin cortes de texto
            c1, c2 = st.columns(2)
            with c1:
                tarjeta_kpi("billetera", "Flujo Libre Real (Mes)", f"${flujo_libre:,.2f}", "Ingreso neto menos gastos y buró", "marino_800")
            with c2:
                tarjeta_kpi("balanza", "Capacidad Máxima (Quincena)", f"${capacidad_pago_quincenal:,.2f}", "Límite del 30% institucional", "azul_600")
                
            st.markdown("<br>", unsafe_allow_html=True)
            
            c3, c4 = st.columns(2)
            with c3:
                tarjeta_kpi("calendario", "Cuota Proyectada (Quincena)", f"${cuota_proyectada:,.2f}", f"Pago amortizado a {plazo_quincenas} quincenas", "dorado_600")
            with c4:
                tarjeta_kpi("porcentaje", "Ratio de Compromiso Real", f"{ratio_compromiso*100:.1f}%", "Endeudamiento sobre flujo libre", "verde_lago")
            
            st.markdown("---")
            
            if flujo_libre <= 0 or ratio_compromiso > 0.40 or puntaje < 600:
                estatus_code = "RECHAZADO"
                dictamen("peligro", "DICTAMEN: RECHAZADO — ALTO RIESGO", f"El compromiso de cuota ({ratio_compromiso*100:.1f}%) excede el límite permisible del 40% o el puntaje en buró ({puntaje}) es insuficiente.")
            elif ratio_compromiso <= 0.30 and puntaje >= 650:
                estatus_code = "APROBADO"
                dictamen("exito", "DICTAMEN: APROBADO — RIESGO BAJO", f"El crédito compromete el {ratio_compromiso*100:.1f}% del flujo libre quincenal, cumpliendo óptimamente la Regla del 30%. Viable para pase a formalización.")
            else:
                estatus_code = "CONDICIONADO"
                dictamen("alerta", "DICTAMEN: CONDICIONADO — RIESGO MEDIO", f"Compromiso del {ratio_compromiso*100:.1f}%. Al situarse entre 30% y 40%, se requiere obligatoriamente firma de aval solidario o garantía prendaria.")
            
            st.divider()
            
            if estatus_code in ["APROBADO", "CONDICIONADO"]:
                with st.spinner("Registrando expediente en servidor institucional..."):
                    datos_nuevo_cliente = {
                        "nombre_completo": nombre.strip(),
                        "rfc": rfc.strip(),
                        "ingreso_neto_mensual": float(ingreso),
                        "deuda_buro_mensual": float(deudas),
                        "puntaje_buro": int(puntaje),
                        "estatus_admision": estatus_code
                    }
                    try:
                        id_generado = registrar_cliente(datos_nuevo_cliente)
                        
                        st.session_state["expediente_activo"] = {
                            "id_cliente": id_generado,
                            "nombre": nombre,
                            "rfc": rfc,
                            "monto_aprobado": monto,
                            "tasa_mensual": tasa_mensual,
                            "plazos": plazo_quincenas,
                            "cuota": cuota_proyectada
                        }
                        
                        dictamen("exito", "Expediente Registrado en Supabase", f"UUID Institucional: {id_generado}. El expediente se encuentra disponible en el módulo de Amortización para emisión contractual.")
                    except Exception as e:
                        dictamen("peligro", "Error de Transacción", f"No se pudo completar el registro en base de datos: {str(e)}")

st.divider()

titulo_seccion("documento", "Catálogo Institucional de Clientes Registrados en Servidor")
try:
    res_clientes = supabase.table("clientes").select("id_cliente, nombre_completo, rfc, ingreso_neto_mensual, puntaje_buro, estatus_admision, fecha_registro").order("fecha_registro", desc=True).limit(10).execute()
    if res_clientes.data:
        df_db = pd.DataFrame(res_clientes.data)
        df_db.columns = ["UUID", "Nombre", "RFC", "Ingreso Neto ($)", "Puntaje Buró", "Estatus", "Fecha Registro"]
        st.dataframe(df_db, use_container_width=True)
    else:
        st.info("No hay registros en la base de datos de Supabase aún. Realice la primera evaluación en el formulario superior.")
except Exception as e:
    dictamen("peligro", "Error de Consulta", "No se pudo obtener el catálogo de clientes desde el servidor.")