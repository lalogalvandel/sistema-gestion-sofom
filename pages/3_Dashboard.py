import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from src.db import supabase
from src.theme import (
    aplicar_identidad_visual, encabezado_modulo, titulo_seccion,
    dictamen, tarjeta_kpi
)

st.set_page_config(page_title="Control de Cobranza | SOFOM", layout="wide")
aplicar_identidad_visual()

encabezado_modulo(
    titulo="Ventanilla de Cobranza y Gestión de Capital",
    subtitulo="Procesamiento de pagos con prelación (Interés > Capital) y recálculo automático de saldos.",
    nombre_icono="banco",
    insignia="COBRANZA ACTIVA"
)

# -----------------------------------------------------------------------------
# LÓGICA DE RECALCULO DE AMORTIZACIÓN (AL REDUCIR CAPITAL)
# -----------------------------------------------------------------------------
def recalcular_calendario(id_prestamo, nuevo_saldo, tasa_mensual, cuotas_restantes, fecha_base):
    tasa_q = tasa_mensual / 2
    # Recalculamos cuota fija con el nuevo saldo y plazos restantes
    if tasa_q > 0:
        nueva_cuota = nuevo_saldo * (tasa_q * (1 + tasa_q)**cuotas_restantes) / ((1 + tasa_q)**cuotas_restantes - 1)
    else:
        nueva_cuota = nuevo_saldo / cuotas_restantes
        
    nuevas_cuotas = []
    saldo = nuevo_saldo
    fecha_iter = fecha_base
    
    for q in range(1, cuotas_restantes + 1):
        fecha_iter += timedelta(days=15)
        int_q = round(saldo * tasa_q, 2)
        if q == cuotas_restantes:
            cap_q = saldo
            cuota_real = round(cap_q + int_q, 2)
            saldo = 0.0
        else:
            cuota_real = round(nueva_cuota, 2)
            cap_q = round(cuota_real - int_q, 2)
            saldo = round(saldo - cap_q, 2)
            
        nuevas_cuotas.append({
            "numero_cuota": q,
            "fecha_vencimiento": fecha_iter.strftime("%Y-%m-%d"),
            "cuota_fija": cuota_real,
            "interes_cobrado": int_q,
            "abono_capital": cap_q,
            "saldo_insoluto": saldo,
            "estatus_pago": "PENDIENTE"
        })
    return nuevas_cuotas

# -----------------------------------------------------------------------------
# DASHBOARD COBRANZA
# -----------------------------------------------------------------------------
# (El código del dashboard sigue igual, solo modificamos el if procesar:)
# --- [REEMPLAZA SOLO ESTA PARTE EN TU CÓDIGO ACTUAL] ---

                procesar = st.form_submit_button("Registrar Pago y Ejecutar Reparto", use_container_width=True)
                
                if procesar:
                    with st.spinner("Conciliando cuenta y recalculando calendario..."):
                        try:
                            # 1. Registrar el pago en cobranza
                            payload_pago = {
                                "id_cuota": id_cuota,
                                "monto_recibido": monto_recibido_real,
                                "interes_real_cobrado": interes_real,
                                "comision_operador": comision_calc,
                                "reserva_riesgo": reserva_calc,
                                "utilidad_socios": utilidad_calc
                            }
                            supabase.table("cobranza_y_comisiones").insert(payload_pago).execute()
                            
                            # 2. Si hubo abono a capital, eliminar cuotas futuras y regenerar
                            if abono_cap_real > 0:
                                # Obtener datos del préstamo para recálculo
                                prestamo = supabase.table("prestamos").select("*").eq("id_prestamo", id_p).single().execute().data
                                
                                # Obtener cuotas pendientes (excluyendo la actual que acabamos de pagar)
                                cuotas_futuras = supabase.table("plan_amortizacion").select("*").eq("id_prestamo", id_p).eq("estatus_pago", "PENDIENTE").execute().data
                                
                                # Borrar las viejas cuotas
                                supabase.table("plan_amortizacion").delete().eq("id_prestamo", id_p).eq("estatus_pago", "PENDIENTE").execute()
                                
                                # Recalcular nuevo saldo
                                nuevo_saldo_total = float(cuota_pend["saldo_insoluto"]) - abono_cap_real
                                nuevas_filas = recalcular_calendario(id_p, nuevo_saldo_total, prestamo["tasa_interes_mensual"], len(cuotas_futuras), datetime.strptime(fecha_venc, "%Y-%m-%d"))
                                
                                # Insertar nuevas cuotas
                                for fila in nuevas_filas:
                                    fila["id_prestamo"] = id_p
                                    supabase.table("plan_amortizacion").insert(fila).execute()
                                    
                            # 3. Marcar actual como pagada
                            supabase.table("plan_amortizacion").update({"estatus_pago": "PAGADO"}).eq("id_cuota", id_cuota).execute()
                            
                            dictamen("exito", "Pago Procesado", f"Abono de ${monto_recibido_real:,.2f} aplicado. Si hubo reducción de capital, el calendario futuro ha sido recalculado automáticamente.")
                            st.rerun()
                        except Exception as e:
                            dictamen("peligro", "Error de servidor", str(e))