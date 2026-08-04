# =============================================================================
# Copyright (c) 2026 Eduardo Galván del Rio. Todos los derechos reservados.
# 
# Este código fuente es propiedad exclusiva y confidencial. Queda estrictamente
# prohibida su reproducción, distribución, comercialización o modificación
# sin autorización expresa y por escrito del autor.
# =============================================================================

import streamlit as st
import bcrypt
from datetime import datetime, timedelta, timezone
from src.db import supabase
from src.theme import aplicar_identidad_visual, dictamen

st.set_page_config(page_title="Acceso | SOFOM E.N.R.", layout="centered", initial_sidebar_state="collapsed")

# Inyección de CSS para desaparecer el botón de abrir el menú lateral
st.markdown("""
    <style>
        [data-testid="collapsedControl"] {display: none;}
        [data-testid="stSidebar"] {display: none;}
    </style>
""", unsafe_allow_html=True)

aplicar_identidad_visual()

st.markdown("<br><br>", unsafe_allow_html=True)
st.title("Acceso Institucional SOFOM")
st.markdown("---")

with st.form("form_login_institucional"):
    email = st.text_input("Correo Electrónico Institucional:", placeholder="usuario@sofom.com")
    pwd = st.text_input("Contraseña de Acceso:", type="password")
    
    submit = st.form_submit_button("Iniciar Sesión", width='stretch')

if submit:
    if not email or not pwd:
        st.warning("Por favor, ingrese sus credenciales completas.")
    else:
        with st.spinner("Ejecutando protocolo de validación y seguridad..."):
            try:
                correo_limpio = email.strip().lower()
                ahora_utc = datetime.now(timezone.utc)
                
                # 1. Buscamos al usuario en la base de datos
                res = supabase.table("usuarios").select("*").eq("email", correo_limpio).execute()
                usuario = res.data[0] if (res.data and len(res.data) > 0) else None
                
                # Si el usuario no existe, registramos el intento anónimo en la caja negra y rechazamos
                if not usuario:
                    supabase.table("log_accesos").insert({
                        "email_usuario": correo_limpio, 
                        "exito": False, 
                        "ip_address": "CLIENTE_WEB", 
                        "detalles": "Usuario no encontrado en sistema"
                    }).execute()
                    dictamen("peligro", "Error de Autenticación", "Las credenciales ingresadas no son válidas.")
                    st.stop()

                # 2. EVALUACIÓN DE BLOQUEO (Protección Anti-Fuerza Bruta)
                bloqueado_hasta_str = usuario.get("bloqueado_hasta")
                if bloqueado_hasta_str:
                    # Convertimos la fecha de Supabase a un objeto datetime de Python comparando en UTC
                    bloqueado_hasta_dt = datetime.fromisoformat(bloqueado_hasta_str.replace('Z', '+00:00'))
                    if ahora_utc < bloqueado_hasta_dt:
                        minutos_restantes = int((bloqueado_hasta_dt - ahora_utc).total_seconds() / 60) + 1
                        
                        # Registro de auditoría del intento bloqueado
                        supabase.table("log_accesos").insert({
                            "email_usuario": correo_limpio, "exito": False, "ip_address": "CLIENTE_WEB", 
                            "detalles": f"Intento rechazado. Cuenta sellada por {minutos_restantes} min."
                        }).execute()
                        
                        dictamen("peligro", "Alerta de Seguridad", f"Múltiples intentos fallidos detectados. La cuenta está bloqueada por seguridad. Intente de nuevo en {minutos_restantes} minutos.")
                        st.stop()

                # 3. VALIDACIÓN CRIPTOGRÁFICA DE CONTRASEÑA
                password_correcta = False
                try:
                    # El auditor señaló validar el formato correcto del hash para evitar crashes
                    password_correcta = bcrypt.checkpw(pwd.encode('utf-8'), usuario['password'].encode('utf-8'))
                except ValueError:
                    password_correcta = False # Hash corrupto o formato inválido

                if password_correcta:
                    # A) RESETEO Y REGISTRO DE ÉXITO
                    supabase.table("usuarios").update({
                        "intentos_fallidos": 0,
                        "bloqueado_hasta": None,
                        "ultimo_login": ahora_utc.isoformat()
                    }).eq("id", usuario["id"]).execute()
                    
                    supabase.table("log_accesos").insert({
                        "email_usuario": correo_limpio, "exito": True, "ip_address": "CLIENTE_WEB", "detalles": "Login exitoso"
                    }).execute()
                    
                    # B) CREACIÓN DE SESIÓN (JWT Lógico)
                    st.session_state["logged_in"] = True
                    st.session_state["user_role"] = usuario['rol']
                    st.session_state["user_email"] = usuario['email']
                    
                    st.success(f"Protocolo de seguridad superado. Perfil de acceso: {usuario['rol']}")
                    st.switch_page("app.py")
                    
                else:
                    # C) CASTIGO Y REGISTRO DE FALLO (Strikes)
                    intentos_actuales = usuario.get("intentos_fallidos", 0) + 1
                    payload_castigo = {"intentos_fallidos": intentos_actuales}
                    detalles_log = f"Contraseña incorrecta. Intento {intentos_actuales}/5"
                    
                    # Si llega a 5 strikes, sellamos la puerta por 15 minutos
                    if intentos_actuales >= 5:
                        tiempo_desbloqueo = ahora_utc + timedelta(minutes=15)
                        payload_castigo["bloqueado_hasta"] = tiempo_desbloqueo.isoformat()
                        detalles_log = "CUENTA SELLADA por posible ataque de fuerza bruta."
                        
                    # Actualizamos castigo en perfil de usuario y lo documentamos en caja negra
                    supabase.table("usuarios").update(payload_castigo).eq("id", usuario["id"]).execute()
                    supabase.table("log_accesos").insert({
                        "email_usuario": correo_limpio, "exito": False, "ip_address": "CLIENTE_WEB", "detalles": detalles_log
                    }).execute()
                    
                    if intentos_actuales >= 5:
                        dictamen("peligro", "Bloqueo de Seguridad Institucional", "Ha excedido el número máximo de intentos permitidos (5). Su cuenta ha sido bloqueada temporalmente.")
                    else:
                        dictamen("peligro", "Error de Autenticación", f"Credenciales inválidas. Le quedan {5 - intentos_actuales} intentos antes del bloqueo de cuenta.")
                        
            except Exception as e:
                dictamen("peligro", "Fallo de Servidor Central", f"No se pudo establecer conexión segura con el core bancario: {str(e)}")