import streamlit as st

def verificar_acceso(rol_requerido):
    """
    Verifica que exista una sesión activa y que el usuario tenga
    el nivel de privilegios necesario. Si falla, detiene la ejecución.
    """
    # 1. Validar sesión activa (AQUÍ ESTÁ EL CAMBIO DE RUTA )
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        st.switch_page("pages/0_Login.py")
        
    # 2. Jerarquía institucional de accesos
    jerarquia = {
        "ADMIN": 3,      # Acceso total: Capital, Socios, Legal, Usuarios
        "COBRANZA": 2,   # Acceso operativo: Dashboard, Ventanilla de Cobros
        "AUDITOR": 1     # Acceso de consulta: Expedientes PLD/KYC, Reportes
    }
    
    rol_actual = st.session_state.get("user_role", "AUDITOR")
    
    # 3. Evaluación de privilegios
    if jerarquia.get(rol_actual, 0) < jerarquia.get(rol_requerido, 0):
        st.error("Acceso Denegado: Su usuario no cuenta con los privilegios institucionales necesarios para visualizar este módulo.")
        st.stop()