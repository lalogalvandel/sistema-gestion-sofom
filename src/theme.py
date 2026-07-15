import streamlit as st

# =============================================================================
# 1. PALETA DE COLORES INSTITUCIONAL
# =============================================================================
PALETA = {
    "marino_900": "#0F2942",
    "marino_800": "#1A365D",
    "marino_700": "#2C4A73",
    "azul_600":   "#2B6CB0",
    "azul_100":   "#EBF4FB",
    "verde_lago": "#3E8E7E",
    "turquesa":   "#81E6D9",
    "dorado_600": "#A9812F",
    "dorado_100": "#F6EFDE",
    "exito":      "#2F7A52",
    "exito_bg":   "#EAF6EF",
    "alerta":     "#B7791F",
    "alerta_bg":  "#FDF3E0",
    "peligro":    "#B42318",
    "peligro_bg": "#FDECEA",
    "tinta_900":  "#1A202C",
    "tinta_600":  "#4A5568",
    "tinta_400":  "#718096",
    "linea_200":  "#E2E8F0",
    "linea_100":  "#EDF1F5",
    "superficie": "#FFFFFF",
    "lienzo":     "#F7F9FB",
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
        margin=dict(t=28, b=10, l=6, r=6),
        showlegend=leyenda,
        font=dict(family="Inter, sans-serif", size=12.5, color=PALETA["tinta_600"]),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(bgcolor=PALETA["marino_900"], font_color="white", font_family="Inter, sans-serif"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.28, xanchor="center", x=0.5),
    )
    fig.update_xaxes(gridcolor=PALETA["linea_100"], zeroline=False)
    fig.update_yaxes(gridcolor=PALETA["linea_100"], zeroline=False)
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
        f'stroke-linejoin="round" style="vertical-align:-3px;margin-right:7px;flex-shrink:0">'
        f'{contenido}</svg>'
    )

# =============================================================================
# 3. HOJA DE ESTILOS CSS
# =============================================================================
def aplicar_identidad_visual():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,500;8..60,600;8..60,700&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"] {{ font-family: {FUENTE_BASE}; }}
    .block-container {{ padding-top: 2.2rem; }}

    .sofom-topbar {{
        display: flex; align-items: center; justify-content: space-between;
        flex-wrap: wrap; gap: 10px;
        padding-bottom: 16px; margin-bottom: 4px;
        border-bottom: 1px solid {PALETA['linea_200']};
    }}
    .sofom-titulo {{
        font-family: {FUENTE_TITULOS}; font-size: 26px; font-weight: 600;
        color: {PALETA['marino_900']}; margin: 0; letter-spacing: -0.2px;
    }}
    .sofom-subtitulo {{
        font-family: {FUENTE_BASE}; font-size: 13.5px; color: {PALETA['tinta_400']};
        margin-top: 4px;
    }}
    .sofom-insignia {{
        display: inline-flex; align-items: center; gap: 7px;
        font-size: 11px; font-weight: 600; letter-spacing: 0.4px; text-transform: uppercase;
        color: {PALETA['exito']}; background: {PALETA['exito_bg']};
        border: 1px solid {PALETA['exito']}40; border-radius: 20px;
        padding: 6px 13px; white-space: nowrap;
    }}
    .sofom-insignia .punto {{
        width: 6px; height: 6px; border-radius: 50%; background: {PALETA['exito']};
        box-shadow: 0 0 0 3px {PALETA['exito']}25;
    }}

    .sofom-kpi {{
        background: {PALETA['superficie']};
        border: 1px solid {PALETA['linea_200']};
        border-left: 3px solid var(--acento, {PALETA['marino_800']});
        border-radius: 10px; padding: 15px 17px; height: 100%;
        box-shadow: 0 1px 2px rgba(15,41,66,0.05);
    }}
    .sofom-kpi-etiqueta {{
        display: flex; align-items: center; font-size: 11.8px; font-weight: 600;
        color: {PALETA['tinta_600']}; text-transform: uppercase; letter-spacing: 0.3px;
        margin-bottom: 11px;
    }}
    .sofom-kpi-valor {{
        font-family: {FUENTE_DATOS}; font-size: 24px; font-weight: 500;
        color: {PALETA['marino_900']}; line-height: 1.15;
    }}
    .sofom-kpi-contexto {{ font-size: 11.8px; color: {PALETA['tinta_400']}; margin-top: 7px; }}

    .sofom-tarjeta {{
        background: {PALETA['superficie']}; border: 1px solid {PALETA['linea_200']};
        border-radius: 10px; padding: 19px 21px; height: 100%;
    }}
    .sofom-tarjeta h4 {{
        font-family: {FUENTE_BASE}; font-size: 14px; font-weight: 700;
        color: {PALETA['marino_900']}; margin: 0 0 2px 0;
        display: flex; align-items: center;
    }}
    .sofom-tarjeta-item {{
        display: flex; gap: 11px; padding: 11px 0;
        border-top: 1px solid {PALETA['linea_100']};
        font-size: 13px; color: {PALETA['tinta_600']}; line-height: 1.55;
    }}
    .sofom-tarjeta-item:first-of-type {{ border-top: none; }}
    .sofom-tarjeta-item b {{ color: {PALETA['tinta_900']}; }}
    .sofom-num {{
        flex-shrink: 0; width: 20px; height: 20px; border-radius: 50%;
        background: {PALETA['marino_800']}; color: white; font-size: 10.5px; font-weight: 700;
        display: flex; align-items: center; justify-content: center; margin-top: 1px;
    }}

    .sofom-seccion {{
        display: flex; align-items: center; font-family: {FUENTE_BASE};
        font-size: 15px; font-weight: 700; color: {PALETA['marino_900']};
        margin: 2px 0 13px 0;
    }}

    .sofom-dictamen {{
        border-radius: 10px; padding: 15px 17px;
        display: flex; gap: 12px; align-items: flex-start; border: 1px solid;
    }}
    .sofom-dictamen-titulo {{ font-size: 12.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.4px; margin-bottom: 3px; }}
    .sofom-dictamen-texto {{ font-size: 13.3px; line-height: 1.55; color: {PALETA['tinta_600']}; }}
    .sofom-dictamen.exito {{ background: {PALETA['exito_bg']}; border-color: {PALETA['exito']}45; }}
    .sofom-dictamen.exito .sofom-dictamen-titulo {{ color: {PALETA['exito']}; }}
    .sofom-dictamen.alerta {{ background: {PALETA['alerta_bg']}; border-color: {PALETA['alerta']}45; }}
    .sofom-dictamen.alerta .sofom-dictamen-titulo {{ color: {PALETA['alerta']}; }}
    .sofom-dictamen.peligro {{ background: {PALETA['peligro_bg']}; border-color: {PALETA['peligro']}45; }}
    .sofom-dictamen.peligro .sofom-dictamen-titulo {{ color: {PALETA['peligro']}; }}

    div[data-testid="metric-container"] {{
        background: {PALETA['superficie']}; border: 1px solid {PALETA['linea_200']};
        border-radius: 10px; padding: 5% 5% 5% 8%; border-left: 4px solid {PALETA['marino_800']};
    }}
    .stButton > button, .stFormSubmitButton > button {{
        background: {PALETA['marino_800']}; color: white; border: none;
        border-radius: 7px; font-weight: 600; letter-spacing: 0.2px; padding: 10px 0;
        transition: background 0.15s ease;
    }}
    .stButton > button:hover, .stFormSubmitButton > button:hover {{ background: {PALETA['marino_900']}; color: white; }}
    .stButton > button[kind="primary"] {{ background: {PALETA['dorado_600']}; }}
    .stButton > button[kind="primary"]:hover {{ background: #8C6A26; }}
    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}
    </style>
    """, unsafe_allow_html=True)

# =============================================================================
# 4. COMPONENTES REUTILIZABLES
# =============================================================================
def encabezado_modulo(titulo, subtitulo, nombre_icono=None, insignia=None):
    icono_html = icono(nombre_icono, color=PALETA["marino_800"], size=27) if nombre_icono else ""
    insignia_html = f'<span class="sofom-insignia"><span class="punto"></span>{insignia}</span>' if insignia else ""
    st.markdown(f"""
    <div class="sofom-topbar">
        <div style="display:flex; align-items:center; gap:13px;">
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
        <div class="sofom-kpi-etiqueta">{icono(nombre_icono, color=PALETA['tinta_400'], size=14)}{etiqueta}</div>
        <div class="sofom-kpi-valor">{valor}</div>
        <div class="sofom-kpi-contexto">{contexto}</div>
    </div>
    """, unsafe_allow_html=True)

def titulo_seccion(nombre_icono, texto):
    st.markdown(f'<div class="sofom-seccion">{icono(nombre_icono, size=18)}{texto}</div>', unsafe_allow_html=True)

def tarjeta_protocolo(titulo, items, nombre_icono=None):
    icono_html = icono(nombre_icono, color=PALETA["marino_800"], size=16) if nombre_icono else ""
    filas = "".join(
        f'<div class="sofom-tarjeta-item"><span class="sofom-num">{i + 1}</span>'
        f'<span><b>{h}.</b> {t}</span></div>'
        for i, (h, t) in enumerate(items)
    )
    st.markdown(f'<div class="sofom-tarjeta"><h4>{icono_html}{titulo}</h4>{filas}</div>', unsafe_allow_html=True)

def dictamen(estatus, titulo_txt, texto_txt):
    icon_map = {"exito": "verificado", "alerta": "alerta_triangulo", "peligro": "cancelado"}
    color_map = {"exito": PALETA["exito"], "alerta": PALETA["alerta"], "peligro": PALETA["peligro"]}
    st.markdown(f"""
    <div class="sofom-dictamen {estatus}">
        {icono(icon_map[estatus], color=color_map[estatus], size=22)}
        <div>
            <div class="sofom-dictamen-titulo">{titulo_txt}</div>
            <div class="sofom-dictamen-texto">{texto_txt}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)