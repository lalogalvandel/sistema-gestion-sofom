# =============================================================================
# Copyright (c) 2026 Eduardo Galván del Rio. Todos los derechos reservados.
# 
# Este código fuente es propiedad exclusiva y confidencial. Queda estrictamente
# prohibida su reproducción, distribución, comercialización o modificación
# sin autorización expresa y por escrito del autor.
# =============================================================================
import streamlit as st
import re

# =============================================================================
# 1. PALETA DE COLORES INSTITUCIONAL
# =============================================================================
PALETA = {
    "marino_900": "#0F172A",  # Pizarra oscuro para textos principales (máxima legibilidad)
    "marino_800": "#1A365D",  # Azul institucional para bordes y acentos
    "marino_700": "#2C4A73",  # Tono secundario
    "azul_600":   "#2B6CB0",  # Azul rey brillante para métricas activas
    "azul_100":   "#EFF6FF",  # Fondo suave
    "verde_lago": "#0D9488",  # Tono financiero estable
    "turquesa":   "#14B8A6",  # Acento secundario
    "dorado_600": "#D97706",  # Ámbar/Dorado para comisiones y retornos
    "dorado_100": "#FEF3C7",  # Fondo de alerta/dorado
    "exito":      "#16A34A",  # Verde confirmación
    "exito_bg":   "#DCFCE7",  # Fondo verde suave
    "alerta":     "#D97706",  # Ámbar advertencia
    "alerta_bg":  "#FEF3C7",  # Fondo ámbar suave
    "peligro":    "#DC2626",  # Rojo rechazo
    "peligro_bg": "#FEE2E2",  # Fondo rojo suave
    "tinta_900":  "#0F172A",  # Texto primario
    "tinta_600":  "#475569",  # Texto descriptivo (alta legibilidad)
    "tinta_400":  "#64748B",  # Texto secundario / etiquetas
    "linea_200":  "#CBD5E1",  # Bordes definidos
    "linea_100":  "#E2E8F0",  # Bordes ligeros
    "superficie": "#FFFFFF",  # Blanco puro para tarjetas
    "lienzo":     "#F8FAFC",  # Fondo global
}

FUENTE_TITULOS = "'Source Serif 4', Georgia, 'Times New Roman', serif"
FUENTE_BASE = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
FUENTE_DATOS = "'IBM Plex Mono', 'SFMono-Regular', Consolas, monospace"

SECUENCIA_GRAFICAS = [
    PALETA["marino_800"], PALETA["azul_600"], PALETA["dorado_600"],
    PALETA["verde_lago"], PALETA["turquesa"], PALETA["tinta_400"],
]

def plantilla_plotly(fig, altura=300, leyenda=False):
    fig.update_layout(
        height=altura,
        margin=dict(t=30, b=10, l=10, r=10),
        showlegend=leyenda,
        font=dict(family="Inter, sans-serif", size=13, color=PALETA["tinta_600"]),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(bgcolor=PALETA["marino_900"], font_color="white", font_family="Inter, sans-serif"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.28, xanchor="center", x=0.5),
    )
    fig.update_xaxes(gridcolor=PALETA["linea_100"], zeroline=False, tickfont=dict(color=PALETA["tinta_600"]))
    fig.update_yaxes(gridcolor=PALETA["linea_100"], zeroline=False, tickfont=dict(color=PALETA["tinta_600"]))
    return fig

# =============================================================================
# 2. ICONOGRAFÍA LINEAL SVG
# =============================================================================
ICONOS = {
    "banco": '<polygon points="12,3 21,9 3,9"/><line x1="4" y1="21" x2="20" y2="21"/><line x1="5" y1="10" x2="5" y2="21"/><line x1="9" y1="10" x2="9" y2="21"/><line x1="15" y1="10" x2="15" y2="21"/><line x1="19" y1="10" x2="19" y2="21"/>',
    "billetera": '<rect x="2.5" y="6.5" width="19" height="13" rx="2"/><path d="M2.5 10h19"/><circle cx="17" cy="14.5" r="1.4" fill="currentColor" stroke="none"/>',
    "personas": '<circle cx="8.5" cy="8" r="3"/><path d="M2.5 20c0-3.5 2.7-6 6-6s6 2.5 6 6"/><circle cx="17" cy="9" r="2.3"/><path d="M14.8 20c0-2.6 1.1-4.6 3-5.6"/>',
    "porcentaje": '<circle cx="12" cy="12" r="9.3"/><line x1="8" y1="16" x2="16" y2="8"/><circle cx="9" cy="9" r="1.15" fill="currentColor" stroke="none"/><circle cx="15" cy="15" r="1.15" fill="currentColor" stroke="none"/>',
    "balanza": '<line x1="12" y1="3" x2="12" y2="20"/><line x1="5" y1="7" x2="19" y2="7"/><path d="M5 7l-3.2 6.8a3.2 3.2 0 0 0 6.4 0z"/><path d="M19 7l-3.2 6.8a3.2 3.2 0 0 0 6.4 0z"/><line x1="9" y1="21" x2="15" y2="21"/>',
    "escudo": '<path d="M12 2.5 4.5 5.3V11c0 5.2 3.3 9.4 7.5 10.8 4.2-1.4 7.5-5.6 7.5-10.8V5.3Z"/>',
    "documento": '<path d="M6.5 2.5h8l4 4v14a1 1 0 0 1-1 1h-11a1 1 0 0 1-1-1v-17a1 1 0 0 1 1-1Z"/><path d="M14.5 2.5v4h4"/><line x1="9" y1="12" x2="15" y2="12"/><line x1="9" y1="15.5" x2="15" y2="15.5"/>',
    "documento_check": '<path d="M6.5 2.5h8l4 4v14a1 1 0 0 1-1 1h-11a1 1 0 0 1-1-1v-17a1 1 0 0 1 1-1Z"/><path d="M14.5 2.5v4h4"/><path d="m9 13.2 1.8 1.8 3.7-3.7"/>',
    "calendario": '<rect x="3" y="5" width="18" height="16" rx="2"/><line x1="3" y1="10" x2="21" y2="10"/><line x1="8" y1="3" x2="8" y2="7"/><line x1="16" y1="3" x2="16" y2="7"/>',
    "tendencia": '<polyline points="3,17 9,11 13,15 21,6"/><polyline points="15,6 21,6 21,12"/>',
    "verificado": '<circle cx="12" cy="12" r="9.3"/><path d="m7.8 12.3 2.6 2.6 5.3-5.6"/>',
    "alerta_triangulo": '<path d="M12 3 22 20H2Z"/><line x1="12" y1="9.5" x2="12" y2="14"/><circle cx="12" cy="16.8" r="0.6" fill="currentColor" stroke="none"/>',
    "cancelado": '<circle cx="12" cy="12" r="9.3"/><line x1="8.3" y1="8.3" x2="15.7" y2="15.7"/><line x1="15.7" y1="8.3" x2="8.3" y2="15.7"/>',
    "candado": '<rect x="4.5" y="10.5" width="15" height="10" rx="1.5"/><path d="M7.5 10.5V7a4.5 4.5 0 0 1 9 0v3.5"/>',
    "caja": '<path d="M3 8.5 12 4l9 4.5-9 4.5-9-4.5Z"/><path d="M3 8.5v7L12 20l9-4.5v-7"/><line x1="12" y1="13" x2="12" y2="20"/>',
    "reloj": '<circle cx="12" cy="12" r="9.3"/><path d="M12 7v5.3l3.6 2.1"/>',
}

def icono(nombre, color=None, size=18):
    color = color or PALETA["marino_800"]
    contenido = ICONOS.get(nombre, "")
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" color="{color}" stroke-width="1.7" stroke-linecap="round" '
        f'stroke-linejoin="round" style="vertical-align:-3px;margin-right:8px;flex-shrink:0">'
        f'{contenido}</svg>'
    )

# =============================================================================
# 3. HOJA DE ESTILOS ARMONIZADA Y BLINDADA
# =============================================================================
def aplicar_identidad_visual():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,500;8..60,600;8..60,700&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"], p, span, div {{
        font-family: {FUENTE_BASE};
        color: {PALETA['tinta_900']};
    }}
    
    /* Evitar cortes de palabras en el techo de la app */
    .block-container {{
        padding-top: 3.8rem !important;
        padding-bottom: 4rem !important;
        max-width: 95% !important;
    }}

    /* Estilar la barra lateral para que sea elegante y sobria */
    section[data-testid="stSidebar"] {{
        border-right: 1px solid {PALETA['linea_200']} !important;
    }}
    section[data-testid="stSidebar"] a {{
        font-weight: 500 !important;
        color: {PALETA['tinta_600']} !important;
    }}
    section[data-testid="stSidebar"] a:hover {{
        color: {PALETA['marino_800']} !important;
        background-color: {PALETA['azul_100']} !important;
    }}

    /* ---------- Barra superior de módulo ---------- */
    .sofom-topbar {{
        display: flex; align-items: center; justify-content: space-between;
        flex-wrap: wrap; gap: 12px;
        padding-bottom: 18px; margin-bottom: 16px;
        border-bottom: 2px solid {PALETA['linea_200']};
    }}
    .sofom-titulo {{
        font-family: {FUENTE_TITULOS}; font-size: 28px; font-weight: 700;
        color: {PALETA['marino_900']} !important; margin: 0 !important;
        letter-spacing: -0.3px; line-height: 1.3 !important;
    }}
    .sofom-subtitulo {{
        font-family: {FUENTE_BASE}; font-size: 14px; font-weight: 500;
        color: {PALETA['tinta_600']} !important; margin-top: 4px !important;
        line-height: 1.4 !important;
    }}
    .sofom-insignia {{
        display: inline-flex; align-items: center; gap: 8px;
        font-size: 11.5px; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase;
        color: {PALETA['exito']} !important; background: {PALETA['exito_bg']} !important;
        border: 1px solid {PALETA['exito']}60; border-radius: 20px;
        padding: 6px 14px; white-space: nowrap;
    }}
    .sofom-insignia .punto {{
        width: 7px; height: 7px; border-radius: 50%; background: {PALETA['exito']};
        box-shadow: 0 0 0 3px {PALETA['exito']}30;
    }}

    /* ---------- Tarjetas KPI ---------- */
    .sofom-kpi {{
        background: {PALETA['superficie']} !important;
        border: 1px solid {PALETA['linea_200']} !important;
        border-left: 4px solid var(--acento, {PALETA['marino_800']}) !important;
        border-radius: 8px; padding: 18px 20px; height: 100%;
        box-shadow: 0 2px 4px rgba(15,23,42,0.04);
    }}
    .sofom-kpi-etiqueta {{
        display: flex; align-items: center; font-size: 12px; font-weight: 700;
        color: {PALETA['tinta_600']} !important; text-transform: uppercase; letter-spacing: 0.5px;
        margin-bottom: 12px;
    }}
    .sofom-kpi-valor {{
        font-family: {FUENTE_DATOS}; font-size: 26px; font-weight: 600;
        color: {PALETA['marino_900']} !important; line-height: 1.2;
    }}
    .sofom-kpi-contexto {{
        font-size: 12.5px; font-weight: 500; color: {PALETA['tinta_400']} !important;
        margin-top: 8px;
    }}

    /* ---------- Tarjeta de contenido genérica ---------- */
    .sofom-tarjeta {{
        background: {PALETA['superficie']} !important; border: 1px solid {PALETA['linea_200']} !important;
        border-radius: 8px; padding: 22px 24px; height: 100%;
        box-shadow: 0 2px 4px rgba(15,23,42,0.04);
    }}
    .sofom-tarjeta h4 {{
        font-family: {FUENTE_BASE}; font-size: 15px; font-weight: 700;
        color: {PALETA['marino_900']} !important; margin: 0 0 6px 0 !important;
        display: flex; align-items: center;
    }}
    .sofom-tarjeta-item {{
        display: flex; gap: 12px; padding: 12px 0;
        border-top: 1px solid {PALETA['linea_100']};
        font-size: 13.5px; color: {PALETA['tinta_600']} !important; line-height: 1.6;
    }}
    .sofom-tarjeta-item:first-of-type {{ border-top: none; }}
    .sofom-tarjeta-item b {{ color: {PALETA['tinta_900']} !important; font-weight: 600; }}
    .sofom-num {{
        flex-shrink: 0; width: 22px; height: 22px; border-radius: 50%;
        background: {PALETA['marino_800']}; color: white !important; font-size: 11px; font-weight: 700;
        display: flex; align-items: center; justify-content: center; margin-top: 2px;
    }}

    /* ---------- Encabezado de sección ---------- */
    .sofom-seccion {{
        display: flex; align-items: center; font-family: {FUENTE_BASE};
        font-size: 16px; font-weight: 700; color: {PALETA['marino_900']} !important;
        margin: 16px 0 14px 0; letter-spacing: -0.2px;
    }}

    /* ---------- Dictamen (insignia de resultado) ---------- */
    .sofom-dictamen {{
        border-radius: 8px; padding: 16px 18px;
        display: flex; gap: 14px; align-items: flex-start; border: 1px solid;
        margin: 12px 0;
    }}
    .sofom-dictamen-titulo {{ font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }}
    .sofom-dictamen-texto {{ font-size: 13.5px; line-height: 1.6; color: {PALETA['tinta_600']} !important; }}
    .sofom-dictamen.exito {{ background: {PALETA['exito_bg']} !important; border-color: {PALETA['exito']}60 !important; }}
    .sofom-dictamen.exito .sofom-dictamen-titulo {{ color: {PALETA['exito']} !important; }}
    .sofom-dictamen.alerta {{ background: {PALETA['alerta_bg']} !important; border-color: {PALETA['alerta']}60 !important; }}
    .sofom-dictamen.alerta .sofom-dictamen-titulo {{ color: {PALETA['alerta']} !important; }}
    .sofom-dictamen.peligro {{ background: {PALETA['peligro_bg']} !important; border-color: {PALETA['peligro']}60 !important; }}
    .sofom-dictamen.peligro .sofom-dictamen-titulo {{ color: {PALETA['peligro']} !important; }}

    /* ---------- Ajustes a widgets nativos de Streamlit ---------- */
    div[data-testid="metric-container"] {{
        background: {PALETA['superficie']} !important; border: 1px solid {PALETA['linea_200']} !important;
        border-radius: 8px; padding: 16px 18px !important; border-left: 4px solid {PALETA['marino_800']} !important;
        box-shadow: 0 2px 4px rgba(15,23,42,0.04);
    }}
    div[data-testid="stMetricLabel"] > label, div[data-testid="stMetricLabel"] > div {{
        color: {PALETA['tinta_600']} !important; font-weight: 600 !important;
    }}
    div[data-testid="stMetricValue"] > div {{
        color: {PALETA['marino_900']} !important; font-family: {FUENTE_DATOS} !important;
    }}
    .stButton > button, .stFormSubmitButton > button {{
        background: {PALETA['marino_800']} !important; color: white !important; border: none !important;
        border-radius: 6px; font-weight: 600; letter-spacing: 0.3px; padding: 10px 16px;
        transition: all 0.15s ease;
    }}
    .stButton > button:hover, .stFormSubmitButton > button:hover {{
        background: {PALETA['marino_900']} !important; color: white !important;
        box-shadow: 0 4px 6px rgba(15,23,42,0.15);
    }}
    .stButton > button[kind="primary"] {{ background: {PALETA['dorado_600']} !important; }}
    .stButton > button[kind="primary"]:hover {{ background: #B45309 !important; }}
    
    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}
    </style>
    """, unsafe_allow_html=True)

# =============================================================================
# 4. COMPONENTES REUTILIZABLES
# =============================================================================
def encabezado_modulo(titulo, subtitulo, nombre_icono=None, insignia=None):
    icono_html = icono(nombre_icono, color=PALETA["marino_800"], size=30) if nombre_icono else ""
    insignia_html = f'<span class="sofom-insignia"><span class="punto"></span>{insignia}</span>' if insignia else ""
    st.markdown(f"""
    <div class="sofom-topbar">
        <div style="display:flex; align-items:center; gap:14px;">
            {icono_html}
            <div>
                <p class="sofom-titulo">{titulo}</p>
                <p class="sofom-subtitulo">{subtitulo}</p>
            </div>
        </div>
        {insignia_html}
    </div>
    """, unsafe_allow_html=True)

def tarjeta_kpi(nombre_icono, etiqueta, valor, contexto="", acento="marino_800"):
    color_acento = PALETA.get(acento, PALETA["marino_800"])
    st.markdown(f"""
    <div class="sofom-kpi" style="--acento:{color_acento}">
        <div class="sofom-kpi-etiqueta">{icono(nombre_icono, color=PALETA['tinta_400'], size=15)}{etiqueta}</div>
        <div class="sofom-kpi-valor">{valor}</div>
        <div class="sofom-kpi-contexto">{contexto}</div>
    </div>
    """, unsafe_allow_html=True)

def titulo_seccion(nombre_icono, texto):
    st.markdown(f'<div class="sofom-seccion">{icono(nombre_icono, size=20)}{texto}</div>', unsafe_allow_html=True)

def tarjeta_protocolo(titulo, items, nombre_icono=None):
    icono_html = icono(nombre_icono, color=PALETA["marino_800"], size=18) if nombre_icono else ""
    filas = "".join(
        f'<div class="sofom-tarjeta-item"><span class="sofom-num">{i + 1}</span>'
        f'<span><b>{h}.</b> {t}</span></div>'
        for i, (h, t) in enumerate(items)
    )
    st.markdown(f'<div class="sofom-tarjeta"><h4>{icono_html}{titulo}</h4>{filas}</div>', unsafe_allow_html=True)


def dictamen(estatus, titulo_txt, texto_txt):
    # 1. Blindaje contra valores nulos (evita que el texto rompa la app)
    if texto_txt is None:
        texto_txt = "Sin mensaje de dictamen disponible."
    if titulo_txt is None:
        titulo_txt = "Aviso Institucional"
        
    icon_map = {"exito": "verificado", "alerta": "alerta_triangulo", "peligro": "cancelado"}
    color_map = {"exito": PALETA.get("exito", "#10B981"), "alerta": PALETA.get("alerta", "#F59E0B"), "peligro": PALETA.get("peligro", "#EF4444")}
    
    # 2. Limpieza de formato: convierte **texto** en <strong>texto</strong> para negritas HTML
    texto_seguro = str(texto_txt)
    texto_procesado = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', texto_seguro)
    
    # 3. Renderizado en Streamlit con EL PARÁMETRO CORRECTO: unsafe_allow_html=True
    st.markdown(f"""
    <div class="sofom-dictamen {estatus}">
        {icono(icon_map.get(estatus, 'alerta_triangulo'), color=color_map.get(estatus, '#000'), size=24)}
        <div>
            <div class="sofom-dictamen-titulo">{titulo_txt}</div>
            <div class="sofom-dictamen-texto">{texto_procesado}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)