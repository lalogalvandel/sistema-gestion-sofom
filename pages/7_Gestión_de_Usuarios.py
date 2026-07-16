import streamlit as st
import pandas as pd
import bcrypt
from src.auth import verificar_acceso
from src.db import supabase
from src.theme import (
    aplicar_identidad_visual, encabezado_modulo, titulo_seccion,
    dictamen
)

st.set_page_config(page_title="Gestión de Usuarios | SOFOM", layout="wide")
aplicar_identidad_visual()

# --- BLINDAJE DE SEGURIDAD (SOLO ADMIN) ---
verificar_acceso("ADMIN")
# ------------------------------------------

encabezado_modulo(
    titulo="Administración de Usuarios y Privilegios RBAC",
    subtitulo="Control de accesos corporativos, altas de personal, directorio y restablecimiento de credenciales.",
    nombre_icono="escudo",
    insignia="SEGURIDAD INTERNA"
)

# Consulta de usuarios existentes para usar en las listas desplegables
try:
    res_usr = supabase.table("usuarios").select("id, email, rol").execute()
    lista_usuarios = res_usr.data if res_usr.data else []
    df_usr = pd.DataFrame(lista_usuarios) if lista_usuarios else pd.DataFrame(columns=["id", "email", "rol"])
except Exception:
    lista_usuarios = []
    df_usr = pd.DataFrame(columns=["id", "email", "rol"])

col_operaciones, col_directorio = st.columns([1.2, 1.3])

with col_operaciones:
    titulo_seccion("personas", "1. Centro de Control de Credenciales")
    pestaña_alta, pestaña_reset = st.tabs(["Alta de Usuario", "Restablecer Contraseña"])
    
    with pestaña_alta:
        with st.form("form_crear_usuario"):
            new_email = st.text_input("Correo Electrónico Institucional:", placeholder="cobranza1@sofom.com")
            new_pwd = st.text_input("Contraseña Temporal:", type="password")
            new_rol = st.selectbox("Rol Institucional:", ["COBRANZA", "AUDITOR", "ADMIN"])
            
            btn_crear = st.form_submit_button("Crear Usuario y Encriptar", use_container_width=True)
            
            if btn_crear:
                if not new_email or len(new_pwd) < 6:
                    st.error("El correo es obligatorio y la contraseña debe tener al menos 6 caracteres.")
                else:
                    with st.spinner("Hasheando contraseña y registrando en Supabase..."):
                        try:
                            salt = bcrypt.gensalt()
                            hashed_pwd = bcrypt.hashpw(new_pwd.encode('utf-8'), salt).decode('utf-8')
                            
                            payload = {
                                "email": new_email.strip(),
                                "password": hashed_pwd,
                                "rol": new_rol
                            }
                            supabase.table("usuarios").insert(payload).execute()
                            dictamen("exito", "Usuario Creado", f"El usuario {new_email} ha sido dado de alta con perfil {new_rol}.")
                            st.rerun()
                        except Exception as e:
                            dictamen("peligro", "Error de Registro", f"No se pudo completar la operación. Detalle: {str(e)}")

    with pestaña_reset:
        st.markdown("*Use esta herramienta cuando un empleado de Cobranza o Auditoría pierda su acceso.*")
        if not df_usr.empty:
            with st.form("form_reset_password"):
                email_a_resetear = st.selectbox("Seleccione el Usuario a Modificar:", options=df_usr["email"].tolist())
                pwd_temp = st.text_input("Nueva Contraseña Temporal:", type="password", placeholder="Mínimo 6 caracteres")
                
                btn_reset = st.form_submit_button("Sobreescribir Contraseña", use_container_width=True)
                
                if btn_reset:
                    if len(pwd_temp) < 6:
                        st.error("La nueva contraseña debe tener al menos 6 caracteres por seguridad.")
                    else:
                        with st.spinner("Actualizando credencial en el servidor..."):
                            try:
                                salt = bcrypt.gensalt()
                                nuevo_hash = bcrypt.hashpw(pwd_temp.encode('utf-8'), salt).decode('utf-8')
                                
                                # Actualizar contraseña en Supabase donde el email coincida
                                supabase.table("usuarios").update({"password": nuevo_hash}).eq("email", email_a_resetear).execute()
                                dictamen("exito", "Contraseña Restablecida", f"La credencial de acceso para {email_a_resetear} fue actualizada correctamente.")
                            except Exception as e:
                                dictamen("peligro", "Fallo de Actualización", f"Error al sobreescribir en la base de datos: {str(e)}")
        else:
            st.info("No hay usuarios registrados para modificar.")

with col_directorio:
    titulo_seccion("documento_check", "2. Directorio de Personal Activo")
    if not df_usr.empty:
        st.dataframe(df_usr[["email", "rol"]], use_container_width=True)
        st.caption("Nota: Por protocolos de seguridad institucional de la SOFOM, las contraseñas no se muestran en pantalla ni se almacenan en texto plano en la base de datos.")
    else:
        st.info("No hay usuarios registrados en el sistema.")