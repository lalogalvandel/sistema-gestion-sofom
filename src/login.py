import streamlit as st
import bcrypt
from src.db import supabase
from src.theme import aplicar_identidad_visual, dictamen

st.set_page_config(page_title="Acceso | SOFOM E.N.R.", layout="centered")
aplicar_identidad_visual()

st.markdown("<br><br>", unsafe_allow_html=True)
st.title("Acceso Institucional SOFOM")
st.markdown("---")

with st.form("form_login_institucional"):
    email = st.text_input("Correo Electrónico Institucional:", placeholder="usuario@sofom.com")
    pwd = st.text_input("Contraseña de Acceso:", type="password")
    
    submit = st.form_submit_button("Iniciar Sesión", use_container_width=True)

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
                    st.switch_page("pages/3_Dashboard.py")
                else:
                    dictamen("peligro", "Error de Autenticación", "Las credenciales ingresadas no son válidas o el usuario no existe.")
            except Exception as e:
                dictamen("peligro", "Fallo de Servidor", f"No se pudo establecer conexión con la base de datos: {str(e)}")