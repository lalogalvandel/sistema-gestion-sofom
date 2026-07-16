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
    subtitulo="Control de accesos corporativos, altas de personal y asignación de roles institucionales.",
    nombre_icono="escudo",
    insignia="SEGURIDAD INTERNA"
)

col_alta, col_lista = st.columns([1, 1.5])

with col_alta:
    titulo_seccion("personas", "1. Alta de Nuevo Usuario")
    with st.form("form_crear_usuario"):
        new_email = st.text_input("Correo Electrónico:", placeholder="cobranza1@sofom.com")
        new_pwd = st.text_input("Contraseña Temporal:", type="password")
        new_rol = st.selectbox("Rol Institucional:", ["COBRANZA", "AUDITOR", "ADMIN"])
        
        btn_crear = st.form_submit_button("Crear Usuario y Encriptar", use_container_width=True)
        
        if btn_crear:
            if not new_email or len(new_pwd) < 6:
                st.error("El correo es obligatorio y la contraseña debe tener al menos 6 caracteres.")
            else:
                with st.spinner("Hasheando contraseña y registrando en Supabase..."):
                    try:
                        # Hasheo automático sin tocar la terminal
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
                        dictamen("peligro", "Error de Registro", f"Es probable que el correo ya esté registrado. Detalle: {str(e)}")

with col_lista:
    titulo_seccion("documento_check", "2. Directorio de Personal Activo")
    try:
        res_usr = supabase.table("usuarios").select("id, email, rol").execute()
        if res_usr.data:
            df_usr = pd.DataFrame(res_usr.data)
            st.dataframe(df_usr[["email", "rol"]], use_container_width=True)
        else:
            st.info("No hay usuarios registrados en el sistema.")
    except Exception as e:
        st.error(f"No se pudo consultar el directorio: {str(e)}")