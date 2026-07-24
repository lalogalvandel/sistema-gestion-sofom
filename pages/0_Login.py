
# Copyright (c) 2026 Eduardo Galván del Rio. Todos los derechos reservados.
# 
# Este código fuente es propiedad exclusiva y confidencial. Queda estrictamente
# prohibida su reproducción, distribución, comercialización o modificación
# sin autorización expresa y por escrito del autor.

import streamlit as st
import bcrypt
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
# =====================================================================
# BOTÓN TEMPORAL PARA INYECTAR USUARIOS (BORRAR DESPUÉS DE USAR)
if st.button("🚨 FORZAR CREACIÓN DE USUARIOS DE PRUEBA"):
    try:
        # Generamos el hash nativo con TU propia computadora
        hash_pass = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Inyectamos directamente a Supabase
        supabase.table("usuarios").insert({"email": "auditor@sofom.com", "password": hash_pass, "rol": "AUDITOR"}).execute()
        supabase.table("usuarios").insert({"email": "cobranza@sofom.com", "password": hash_pass, "rol": "COBRANZA"}).execute()
        
        st.success("✅ ¡Cuentas inyectadas con éxito! Ya puedes iniciar sesión y borrar este botón de tu código.")
    except Exception as e:
        st.error(f"Fallo al inyectar: {str(e)}")
# =====================================================================
with st.form("form_login_institucional"):
    email = st.text_input("Correo Electrónico Institucional:", placeholder="usuario@sofom.com")
    pwd = st.text_input("Contraseña de Acceso:", type="password")
    
    submit = st.form_submit_button("Iniciar Sesión", width='stretch')

if submit:
    if not email or not pwd:
        st.warning("Por favor, ingrese sus credenciales completas.")
    else:
        with st.spinner("Validando credenciales en servidor central..."):
            try:
                # Consulta en Supabase
                res = supabase.table("usuarios").select("*").eq("email", email.strip()).execute()
                usuario = res.data[0] if (res.data and len(res.data) > 0) else None
                
                if usuario and bcrypt.checkpw(pwd.encode('utf-8'), usuario['password'].encode('utf-8')):
                    st.session_state["logged_in"] = True
                    st.session_state["user_role"] = usuario['rol']
                    st.session_state["user_email"] = usuario['email']
                    
                    st.success(f"Bienvenido. Sesión iniciada con perfil: {usuario['rol']}")
                    # Redirigir al dashboard principal después de loguear
                    st.switch_page("app.py")
                else:
                    dictamen("peligro", "Error de Autenticación", "Las credenciales ingresadas no son válidas o el usuario no existe.")
            except Exception as e:
                dictamen("peligro", "Fallo de Servidor", f"No se pudo establecer conexión con la base de datos: {str(e)}")
