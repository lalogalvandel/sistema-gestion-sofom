import streamlit as st
import pandas as pd
import plotly.express as px
from src.db import supabase
from src.theme import (
    PALETA, aplicar_identidad_visual, encabezado_modulo,
    tarjeta_kpi, titulo_seccion, tarjeta_protocolo, plantilla_plotly,
    SECUENCIA_GRAFICAS
)

# Configuración institucional de página
st.set_page_config(
    page_title="Sistema de Gestión SOFOM - Core Engine",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 1. Inyectar el motor visual institucional
aplicar_identidad_visual()

# 2. Encabezado editorial sin emojis, con icono SVG lineal e insignia
encabezado_modulo(
    titulo="Suite Operativa y Gestión de Crédito",
    subtitulo="Fase de Validación — Control Institucional en Tiempo Real y Trazabilidad en Servidor",
    nombre_icono="banco",
    insignia="SOFOM E.N.R."
)

# 3. Consulta transaccional en tiempo real para KPIs (BLINDADA)
@st.cache_data(ttl=30)
def obtener_kpis_cartera():
    try:
        # 1. Traemos todo de 'prestamos' para evitar errores si la columna se llama diferente
        res_prestamos = supabase.table("prestamos").select("*").execute()
        
        if not res_prestamos.data:
            return 0, 0.0, 0, 0.0
            
        df_p = pd.DataFrame(res_prestamos.data)
        
        # 2. Conteo real de expedientes únicos basándonos en los préstamos existentes
        col_id = "rfc" if "rfc" in df_p.columns else ("id_cliente" if "id_cliente" in df_p.columns else None)
        total_clientes = len(df_p[col_id].unique()) if col_id else len(df_p)
        
        # 3. Mapeo seguro del Monto Colocado
        col_monto = "monto_principal" if "monto_principal" in df_p.columns and df_p["monto_principal"].sum() > 0 else ("monto" if "monto" in df_p.columns else None)
        df_p["monto_calc"] = pd.to_numeric(df_p[col_monto], errors="coerce").fillna(0.0) if col_monto else 0.0
        capital_colocado = float(df_p["monto_calc"].sum())
        
        # 4. Conteo flexible de créditos activos (busca en 'estatus' o 'estatus_credito')
        col_estatus = "estatus" if "estatus" in df_p.columns else ("estatus_credito" if "estatus_credito" in df_p.columns else None)
        if col_estatus:
            df_p["estatus_norm"] = df_p[col_estatus].astype(str).str.upper().str.strip()
            prestamos_activos = len(df_p[df_p["estatus_norm"].isin(["VIGENTE", "ACTIVO", "ESTRUCTURADO", "APROBADO"])])
        else:
            prestamos_activos = len(df_p)
            
        # 5. Mapeo seguro de Tasa y cálculo de Interés (ajustando decimales automáticamente)
        col_tasa = "tasa_mensual" if "tasa_mensual" in df_p.columns else ("tasa_interes_mensual" if "tasa_interes_mensual" in df_p.columns else ("tasa" if "tasa" in df_p.columns else None))
        df_p["tasa_calc"] = pd.to_numeric(df_p[col_tasa], errors="coerce").fillna(6.0) if col_tasa else 6.0
        
        # Si la tasa está en formato entero (ej. 6.0 en vez de 0.06), la convertimos a porcentaje
        if df_p["tasa_calc"].mean() > 1.0:
            df_p["tasa_calc"] = df_p["tasa_calc"] / 100.0
            
        interes_mensual_proyectado = float((df_p["monto_calc"] * df_p["tasa_calc"]).sum())
        
        return total_clientes, capital_colocado, prestamos_activos, interes_mensual_proyectado
    except Exception:
        return 0, 0.0, 0, 0.0

total_cli, cap_colocado, prest_activos, int_proyectado = obtener_kpis_cartera()
fondo_prueba_total = 150000.0
capital_disponible = fondo_prueba_total - cap_colocado
comision_proyectada = int_proyectado * 0.20

titulo_seccion("tendencia", "Estado General del Fondo y Métricas de Cartera")

# 4. Cuadrícula 2x2 para evitar recortes numéricos en montos grandes
col1, col2 = st.columns(2)
with col1:
    tarjeta_kpi(
        nombre_icono="billetera",
        etiqueta="Capital Colocado (Activo)",
        valor=f"${cap_colocado:,.2f}",
        contexto=f"Fondo Disponible: ${capital_disponible:,.2f} MXN",
        acento="marino_800"
    )
with col2:
    tarjeta_kpi(
        nombre_icono="documento_check",
        etiqueta="Créditos Formalizados",
        valor=f"{prest_activos} contratos",
        contexto=f"Respaldados por {total_cli} expedientes en base de datos",
        acento="azul_600"
    )

st.markdown("<br>", unsafe_allow_html=True)

col3, col4 = st.columns(2)
with col3:
    tarjeta_kpi(
        nombre_icono="porcentaje",
        etiqueta="Interés Bruto Proyectado / Mes",
        valor=f"${int_proyectado:,.2f}",
        contexto="Rendimiento sobre cartera vigente en rotación",
        acento="dorado_600"
    )
with col4:
    tarjeta_kpi(
        nombre_icono="escudo",
        etiqueta="Comisión Operativa Proyectada (20%)",
        valor=f"${comision_proyectada:,.2f}",
        contexto="Retribución mensual por administración de cartera",
        acento="verde_lago"
    )

st.divider()

# 5. Sección inferior: Protocolo y Gráfica con Plantilla Institucional
col_left, col_right = st.columns([1.1, 0.9])

with col_left:
    items_protocolo = [
        ("Evaluación Paramétrica Estricta", "Todo crédito otorgado aprueba el filtro algorítmico de liquidez (Regla del 30%) en el Módulo de Admisión antes de su pase a firma."),
        ("Conciliación Matemáticamente Exacta", "Los calendarios de amortización operan con ajuste al cierre, eliminando descuadres contables de centavos en el saldo insoluto final."),
        ("Trazabilidad Inmutable", "Cada pagaré, anexo de pago y evento de cobranza se respalda transaccionalmente en el servidor relacional PostgreSQL.")
    ]
    tarjeta_protocolo(
        titulo="Protocolo de Control y Cumplimiento Normativo",
        items=items_protocolo,
        nombre_icono="balanza"
    )

with col_right:
    titulo_seccion("porcentaje", "Distribución del Retorno por Intereses")
    labels = ['Dividendos Socios (65%)', 'Comisión Operadora (20%)', 'Reserva Morosidad (15%)']
    values = [65, 20, 15]
    
    fig = px.pie(
        names=labels, 
        values=values, 
        color_discrete_sequence=[PALETA["marino_800"], PALETA["azul_600"], PALETA["dorado_600"]]
    )
    fig.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='#FFFFFF', width=2)))
    fig = plantilla_plotly(fig, altura=240, leyenda=False)
    
    st.plotly_chart(fig, use_container_width=True)