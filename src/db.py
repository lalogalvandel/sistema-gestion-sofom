import streamlit as st
from supabase import create_client, Client
import pandas as pd

@st.cache_resource
def obtener_cliente_supabase() -> Client:
    """
    Se conecta a Supabase leyendo las variables de seguridad de Streamlit Cloud.
    No requiere ningún archivo local .toml si se ejecuta en la nube.
    """
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("🚨 Error de conexión: No se encontraron las credenciales en los Secrets de Streamlit.")
        st.stop()

# Cliente global para importar en cualquier página
supabase: Client = obtener_cliente_supabase()

def registrar_cliente(datos_cliente: dict) -> str:
    """Inserta un cliente evaluado en Supabase y devuelve su UUID."""
    res = supabase.table("clientes").insert(datos_cliente).execute()
    if res.data:
        return res.data[0]["id_cliente"]
    raise Exception("No se pudo registrar al cliente en la base de datos.")

def formalizar_credito_y_amortización(datos_prestamo: dict, tabla_amortizacion: pd.DataFrame) -> str:
    """
    Guarda el préstamo principal e inserta todas las cuotas de amortización en un solo paso.
    """
    # 1. Guardar expediente principal
    res_prestamo = supabase.table("prestamos").insert(datos_prestamo).execute()
    if not res_prestamo.data:
        raise Exception("Error al guardar el expediente del préstamo.")
    
    id_prestamo = res_prestamo.data[0]["id_prestamo"]
    
    # 2. Preparar las cuotas asociadas al ID del préstamo
    cuotas = []
    for _, fila in tabla_amortizacion.iterrows():
        cuotas.append({
            "id_prestamo": id_prestamo,
            "numero_cuota": int(fila["No. Quincena"]),
            "fecha_vencimiento": fila["Fecha de Vencimiento"],
            "saldo_inicial": float(str(fila["Saldo Inicial ($)"]).replace(",", "")),
            "cuota_fija": float(str(fila["Cuota Fija ($)"]).replace(",", "")),
            "interes_cobrado": float(str(fila["Interés Cobrado ($)"]).replace(",", "")),
            "abono_capital": float(str(fila["Abono a Capital ($)"]).replace(",", "")),
            "saldo_insoluto": float(str(fila["Saldo Insoluto ($)"]).replace(",", "")),
            "estatus_pago": "PENDIENTE"
        })
        
    # 3. Guardar todo el calendario en Supabase
    res_cuotas = supabase.table("plan_amortizacion").insert(cuotas).execute()
    if not res_cuotas.data:
        raise Exception("Error al guardar el calendario de amortización.")
        
    return id_prestamo