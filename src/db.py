import streamlit as st
from supabase import create_client, Client
from typing import Dict, Any, List, Optional
import pandas as pd

@st.cache_resource
def obtener_cliente_supabase() -> Client:
    """Inicializa y almacena en caché la conexión única al servidor de Supabase."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = obtener_cliente_supabase()

def registrar_cliente(datos_cliente: Dict[str, Any]) -> str:
    """Inserta un nuevo solicitante y retorna su ID único (UUID)."""
    respuesta = supabase.table("clientes").insert(datos_cliente).execute()
    if respuesta.data:
        return respuesta.data[0]["id_cliente"]
    raise Exception("Fallo en el registro del cliente en la base de datos.")

def formalizar_credito_completo(datos_prestamo: Dict[str, Any], tabla_amortizacion: pd.DataFrame) -> str:
    """
    Ejecuta una transacción en dos etapas: registra el préstamo principal
    e inserta en bloque (batch insert) todo el calendario de amortización.
    """
    # 1. Insertar expediente principal
    res_prestamo = supabase.table("prestamos").insert(datos_prestamo).execute()
    if not res_prestamo.data:
        raise Exception("Error al formalizar el contrato principal en base de datos.")
    
    id_prestamo = res_prestamo.data[0]["id_prestamo"]
    
    # 2. Formatear y asociar el UUID del préstamo a cada cuota
    registros_cuotas = []
    for _, fila in tabla_amortizacion.iterrows():
        registros_cuotas.append({
            "id_prestamo": id_prestamo,
            "numero_cuota": int(fila["No. Quincena"]),
            "fecha_vencimiento": fila["Fecha de Vencimiento"],
            "saldo_inicial": float(fila["Saldo Inicial ($)"].replace(",", "")),
            "cuota_fija": float(fila["Cuota Fija ($)"].replace(",", "")),
            "interes_cobrado": float(fila["Interés Cobrado ($)"].replace(",", "")),
            "abono_capital": float(fila["Abono a Capital ($)"].replace(",", "")),
            "saldo_insoluto": float(fila["Saldo Insoluto ($)"].replace(",", "")),
            "estatus_pago": "PENDIENTE"
        })
        
    # 3. Inserción en bloque (Batch Insert) para máxima eficiencia y coherencia
    res_cuotas = supabase.table("plan_amortizacion").insert(registros_cuotas).execute()
    if not res_cuotas.data:
        # En una arquitectura corporativa, aquí se ejecutaría un ROLLBACK del préstamo
        raise Exception("Error al registrar el calendario de amortización en bloque.")
        
    return id_prestamo

def consultar_cartera_activa() -> pd.DataFrame:
    """Consulta la vista consolidada de créditos vigentes y saldos insolutos."""
    res = supabase.table("prestamos").select("*, clientes(nombre_completo, rfc)").eq("estatus_credito", "VIGENTE").execute()
    if res.data:
        df = pd.json_normalize(res.data)
        return df
    return pd.DataFrame()
