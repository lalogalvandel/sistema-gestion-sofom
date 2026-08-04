# =============================================================================
# Copyright (c) 2026 Eduardo Galván del Rio. Todos los derechos reservados.
# 
# Este código fuente es propiedad exclusiva y confidencial. Queda estrictamente
# prohibida su reproducción, distribución, comercialización o modificación
# sin autorización expresa y por escrito del autor.
# =============================================================================

import streamlit as st
import pandas as pd
import bcrypt
import re
from datetime import datetime, timedelta, timezone
from src.db import supabase
from src.theme import (
    aplicar_identidad_visual, encabezado_modulo, titulo_seccion,
    dictamen, tarjeta_kpi
)
from src.auth import verificar_acceso

st.set_page_config(page_title="Gestión de Usuarios | SOFOM", layout="wide")

# --- BLINDAJE INSTITUCIONAL RBAC ---
# SOLO EL ADMIN GLOBAL PUEDE ENTRAR A ESTE MÓDULO
verificar_acceso("ADMIN_GLOBAL")
# -----------------------------------

aplicar_identidad_visual()

st.markdown("""
<style>
    [data-testid="stMetricValue"], .stDataFrame {
        font-family: 'JetBrains Mono', 'Courier New', monospace !important;
    }
</style>
""", unsafe_allow_html=True)

encabezado_modulo(
    titulo="Directorio Activo y Control de Accesos (RBAC)",
    subtitulo="Administración granular de perfiles, políticas de contraseñas y auditoría de sesiones corporativas.",
    nombre_icono="escudo",
    insignia="SEGURIDAD INFORMÁTICA"
)

usuario_admin_actual = st.session_state.get("user_email", "admin@sofom.com")

# -----------------------------------------------------------------------------
# 1. EXTRACCIÓN DEL DIRECTORIO
# -----------------------------------------------------------------------------
@st.cache_data(ttl=10)
def obtener_directorio():
    try:
        res = supabase.table("usuarios").select("id, email, rol, intentos_fallidos, bloqueado_hasta, ultimo_login, ultimo_cambio_password, debe_cambiar_password").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

df_usuarios = obtener_directorio()

# -----------------------------------------------------------------------------
# 2. VALIDACIONES DE SEGURIDAD REGEX (NIVEL BANCARIO)
# -----------------------------------------------------------------------------
def validar_email(email):
    patron = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(patron, email) is not None

def validar_password_fuerte(password):
    """Mínimo 8 caracteres, 1 mayúscula, 1 minúscula, 1 número, 1 carácter especial"""
    patron = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
    return re.match(patron, password) is not None

# -----------------------------------------------------------------------------
# 3. INTERFAZ: DIRECTORIO Y AUDITORÍA
# -----------------------------------------------------------------------------
titulo_seccion("personas", "1. Directorio Activo de Usuarios")

if not df_usuarios.empty:
    df_ver = df_usuarios.copy()
    ahora = datetime.now(timezone.utc)
    
    # Calcular inactividad y estado de bloqueo
    def determinar_estado(row):
        estado = "🟢 ACTIVO"
        
        # Bloqueo por Fuerza Bruta
        if pd.notna(row.get("bloqueado_hasta")):
            bloqueo_dt = datetime.fromisoformat(str(row["bloqueado_hasta"]).replace('Z', '+00:00'))
            if ahora < bloqueo_dt:
                return "🔴 BLOQUEADO (Fuerza Bruta)"
                
        # Bloqueo por Inactividad (Regla 90 días del Auditor)
        if pd.notna(row.get("ultimo_login")):
            ultimo_login_dt = datetime.fromisoformat(str(row["ultimo_login"]).replace('Z', '+00:00'))
            dias_inactivo = (ahora - ultimo_login_dt).days
            if dias_inactivo > 90:
                return f"🟡 INACTIVO ({dias_inactivo} días)"
                
        if row.get("debe_cambiar_password"):
            return "🟠 REQUIERE CAMBIO DE CLAVE"
            
        return estado

    df_ver["Estado de Seguridad"] = df_ver.apply(determinar_estado, axis=1)
    df_ver["Último Acceso"] = df_ver["ultimo_login"].apply(lambda x: str(x)[:10] if pd.notna(x) else "Nunca")
    
    st.dataframe(df_ver[["email", "rol", "Estado de Seguridad", "intentos_fallidos", "Último Acceso"]], width="stretch", hide_index=True)
else:
    st.info("No hay usuarios registrados en el sistema.")

st.divider()

# -----------------------------------------------------------------------------
# 4. GESTIÓN: ALTA Y RESETEO
# -----------------------------------------------------------------------------
col_alta, col_reset = st.columns([1, 1])

with col_alta:
    titulo_seccion("herramienta", "2. Alta de Perfil Granular")
    
    with st.form("form_alta_usuario"):
        nuevo_email = st.text_input("Correo Institucional:")
        nuevo_pwd = st.text_input("Contraseña Temporal:", type="password")
        
        st.markdown("**Asignación de Rol (RBAC):**")
        nuevo_rol = st.selectbox("Nivel de Privilegios:", [
            "ADMIN_GLOBAL",         # Acceso total a todo
            "ORIGINACION_MESA",     # Puede crear créditos y subir KYC (Módulo 1)
            "COBRANZA_ESCRITURA",   # Puede registrar pagos y generar contratos (Módulo 3 y 4)
            "COBRANZA_LECTURA",     # Solo puede ver la tabla de amortización (Módulo 2)
            "AUDITOR_RIESGOS"       # Solo lectura de métricas y VaR (Módulo 8)
        ])
        
        btn_crear = st.form_submit_button("Crear Usuario y Cifrar", type="primary", width="stretch")
        
        if btn_crear:
            if not validar_email(nuevo_email):
                st.error("Formato de correo electrónico inválido.")
            elif not validar_password_fuerte(nuevo_pwd):
                st.error("La contraseña es muy débil. Requiere: 8 caracteres, 1 mayúscula, 1 minúscula, 1 número y 1 símbolo (@$!%*?&).")
            else:
                with st.spinner("Generando Hash bcrypt..."):
                    try:
                        # Cifrado robusto
                        salt = bcrypt.gensalt(rounds=12)
                        hash_pwd = bcrypt.hashpw(nuevo_pwd.encode('utf-8'), salt).decode('utf-8')
                        
                        payload_usr = {
                            "email": nuevo_email.strip().lower(),
                            "password": hash_pwd,
                            "rol": nuevo_rol,
                            "debe_cambiar_password": True # Obligamos a que la cambie al entrar
                        }
                        
                        supabase.table("usuarios").insert(payload_usr).execute()
                        
                        # Pista de auditoría inmutable
                        supabase.table("bitacora_cobranza").insert({
                            "id_credito_ref": "SEGURIDAD_TI",
                            "tipo_accion": "ALTA DE USUARIO",
                            "notas": f"Se creó el usuario {nuevo_email} con rol {nuevo_rol}.",
                            "usuario_gestor": usuario_admin_actual
                        }).execute()
                        
                        st.success(f"Usuario {nuevo_email} creado exitosamente.")
                        st.rerun()
                    except Exception as e:
                        if "duplicate key" in str(e).lower():
                            st.error("Ese correo ya existe en el sistema.")
                        else:
                            st.error(f"Fallo en base de datos: {str(e)}")

with col_reset:
    titulo_seccion("candado", "3. Auditoría y Reseteo")
    
    if not df_usuarios.empty:
        with st.form("form_reset_usuario"):
            st.markdown("Seleccione un usuario para forzar el restablecimiento de su clave o desbloquear su cuenta tras un ataque de fuerza bruta.")
            usuario_sel = st.selectbox("Cuenta Objetivo:", df_usuarios["email"].tolist())
            
            pwd_reset = st.text_input("Nueva Contraseña Temporal:", type="password")
            
            c_btn1, c_btn2 = st.columns(2)
            btn_reset = c_btn1.form_submit_button("Restablecer Clave")
            btn_desbloqueo = c_btn2.form_submit_button("Quitar Bloqueo de Seguridad")
            
            if btn_reset:
                if not validar_password_fuerte(pwd_reset):
                    st.error("La nueva contraseña debe cumplir con las políticas de complejidad (Mayúscula, número, símbolo, min. 8 caracteres).")
                else:
                    with st.spinner("Actualizando Hash..."):
                        try:
                            salt = bcrypt.gensalt(rounds=12)
                            hash_pwd = bcrypt.hashpw(pwd_reset.encode('utf-8'), salt).decode('utf-8')
                            
                            # Forzamos que la cambie en el siguiente login
                            supabase.table("usuarios").update({
                                "password": hash_pwd,
                                "debe_cambiar_password": True,
                                "ultimo_cambio_password": datetime.now(timezone.utc).isoformat()
                            }).eq("email", usuario_sel).execute()
                            
                            supabase.table("bitacora_cobranza").insert({
                                "id_credito_ref": "SEGURIDAD_TI", "tipo_accion": "RESETEO CLAVE",
                                "notas": f"Clave de {usuario_sel} restablecida por Admin.", "usuario_gestor": usuario_admin_actual
                            }).execute()
                            
                            st.success("Clave restablecida. El usuario será obligado a cambiarla en su próximo inicio de sesión.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Fallo en actualización: {str(e)}")
                            
            if btn_desbloqueo:
                with st.spinner("Restaurando accesos..."):
                    try:
                        supabase.table("usuarios").update({
                            "intentos_fallidos": 0,
                            "bloqueado_hasta": None
                        }).eq("email", usuario_sel).execute()
                        
                        supabase.table("bitacora_cobranza").insert({
                            "id_credito_ref": "SEGURIDAD_TI", "tipo_accion": "DESBLOQUEO CUENTA",
                            "notas": f"Cuenta {usuario_sel} desbloqueada por Admin.", "usuario_gestor": usuario_admin_actual
                        }).execute()
                        
                        st.success(f"La cuenta {usuario_sel} ha sido desbloqueada (Strikes en 0).")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fallo de servidor: {str(e)}")
    else:
        st.info("Sin usuarios para auditar.")