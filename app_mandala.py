import streamlit as st
import swisseph as swe
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import numpy as np
import math
import base64
import os

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Mandala Astrológica Viva", layout="wide")

SIGNOS = ["Áries", "Touro", "Gêmeos", "Câncer", "Leão", "Virgem", 
          "Libra", "Escorpião", "Sagitário", "Capricórnio", "Aquário", "Peixes"]

ASPECTOS = {
    0: ("Conjunção", "☌"), 
    30: ("Semi-sêxtil", "⚺"), 
    60: ("Sêxtil", "✶"), 
    90: ("Quadratura", "□"), 
    120: ("Trígono", "△"), 
    150: ("Quincúncio", "⚻"), 
    180: ("Oposição", "☍")
}

SIMBOLOS_PLANETAS = {
    "SOL": "☉", "LUA": "☽", "MERCÚRIO": "☿", "VÊNUS": "♀", 
    "MARTE": "♂", "JÚPITER": "♃", "SATURNO": "♄", "URANO": "♅", 
    "NETUNO": "♆", "PLUTÃO": "♇"
}

SIMBOLOS_SIGNOS = ["♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓"]

CORES_SIGNOS = [
    "#FF4B4B", "#FF9F4B", "#FFD34B", "#99FF4B", "#4BFF81", "#4BFFD3",
    "#4BAFFF", "#4B5BFF", "#814BFF", "#D34BFF", "#FF4B9F", "#FF4B4B"
]

# --- CÁLCULOS ASTRONÔMICOS ---
def get_signo(longitude):
    return SIGNOS[int(longitude / 30) % 12]

def dms_to_dec(dms_str):
    if isinstance(dms_str, (int, float)): return float(dms_str)
    parts = str(dms_str).split('.')
    return float(parts[0]) + (float(parts[1])/60 if len(parts) > 1 else 0)

def hex_to_rgba(hex_color, opacity):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({r}, {g}, {b}, {opacity})'

def calcular_aspecto(long1, long2):
    diff = abs(long1 - long2) % 360
    if diff > 180: diff = 360 - diff
    for angulo, (nome, simbolo) in ASPECTOS.items():
        if abs(diff - angulo) <= 5: # Orbe de 5 graus
            return nome
    return "Outro"

def obter_simbolo_aspecto(long1, long2):
    diff = abs(long1 - long2) % 360
    if diff > 180: diff = 360 - diff
    for angulo, (nome, simbolo) in ASPECTOS.items():
        if abs(diff - angulo) <= 5:
            return simbolo
    return ""

def criar_mandala_astrologica(ano, mes, dia, hora_decimal, pasta_icones):
    # --- 1. CONFIGURAÇÕES E CÁLCULOS INICIAIS ---
    jd = swe.julday(ano, mes, dia, hora_decimal)
    
    NOMES_SIGNOS = ["Áries", "Touro", "Gêmeos", "Câncer", "Leão", "Virgem", 
                    "Libra", "Escorpião", "Sagitário", "Capricórnio", "Aquário", "Peixes"]
    
    ARQUIVOS_SVG = ["aries.svg", "touro.svg", "gemeos.svg", "cancer.svg", 
                    "leao.svg", "virgem.svg", "libra.svg", "escorpiao.svg", 
                    "sagitario.svg", "capricornio.svg", "aquario.svg", "peixes.svg"]

    planetas_cfg = [
        {"id": swe.SUN, "nome": "Sol", "cor": "#FFD700", "sym": "☉"},
        {"id": swe.MOON, "nome": "Lua", "cor": "#C0C0C0", "sym": "☽"},
        {"id": swe.MERCURY, "nome": "Mercúrio", "cor": "#F3A384", "sym": "☿"},
        {"id": swe.VENUS, "nome": "Vênus", "cor": "#0A8F11", "sym": "♀"},
        {"id": swe.MARS, "nome": "Marte", "cor": "#F10808", "sym": "♂"},
        {"id": swe.JUPITER, "nome": "Júpiter", "cor": "#1746C9", "sym": "♃"},
        {"id": swe.SATURN, "nome": "Saturno", "cor": "#381094", "sym": "♄"},
        {"id": swe.URANUS, "nome": "Urano", "cor": "#FF00FF", "sym": "♅"},
        {"id": swe.NEPTUNE, "nome": "Netuno", "cor": "#1EFF00", "sym": "♆"},
        {"id": swe.PLUTO, "nome": "Plutão", "cor": "#14F1F1", "sym": "♇"}
    ]

    fig = go.Figure()
    raio_interno = 4.0
    
    # --- 2. POSIÇÕES E LÓGICA ANTI-SOBREPOSIÇÃO ---
    posicoes = []
    for p in planetas_cfg:
        res, _ = swe.calc_ut(jd, p["id"], swe.FLG_SWIEPH)
        long_abs = res[0]
        id_signo = int(long_abs / 30)
        grau_no_signo = long_abs % 30
        min_f, gr_i = math.modf(grau_no_signo)
        min_i = int(round(min_f * 60))
        if min_i == 60: min_i = 0; gr_i += 1
        
        posicoes.append({
            "nome": p["nome"], "long": long_abs, "cor": p["cor"], 
            "sym": p["sym"], "grau_int": int(gr_i), "min_int": min_i,
            "signo": NOMES_SIGNOS[id_signo % 12], "long_visual": long_abs 
        })

    posicoes.sort(key=lambda x: x['long'])
    dist_min = 7.0 
    for _ in range(5): 
        for i in range(len(posicoes)):
            for j in range(i + 1, len(posicoes)):
                d = (posicoes[j]['long_visual'] - posicoes[i]['long_visual']) % 360
                if d < dist_min:
                    posicoes[j]['long_visual'] = (posicoes[i]['long_visual'] + dist_min) % 360

    # --- 3. CÍRCULO INTERIOR (CENTRAL) ---
    fig.add_trace(go.Scatterpolar(r=[raio_interno] * 361, theta=list(range(361)), fill='toself', 
        fillcolor="rgba(245, 245, 245, 0.2)", line=dict(color="black", width=1.5), showlegend=False, hoverinfo='skip'))

    # --- 4. LINHAS DE ASPECTO COM SÍMBOLOS ---
    CORES_ASPECTOS = {"☌": "green", "☍": "red", "□": "red", "△": "blue", "✶": "blue", "⚼": "orange", "∠": "orange"}
    for i in range(len(posicoes)):
        for j in range(i + 1, len(posicoes)):
            p1, p2 = posicoes[i], posicoes[j]
            simbolo_asp = obter_simbolo_aspecto(p1['long'], p2['long'])
            
            if simbolo_asp:
                cor_asp = CORES_ASPECTOS.get(simbolo_asp, "gray")
                fig.add_trace(go.Scatterpolar(r=[raio_interno, raio_interno], theta=[p1['long'], p2['long']],
                    mode='lines', line=dict(color=cor_asp, width=1.3), opacity=0.3, showlegend=False, hoverinfo='skip'))
                
                a1, a2 = np.radians(p1['long']), np.radians(p2['long'])
                x = (np.cos(a1) + np.cos(a2)) / 2
                y = (np.sin(a1) + np.sin(a2)) / 2
                mid_theta = np.degrees(np.arctan2(y, x))
                dist_ang = abs(p1['long'] - p2['long'])
                if dist_ang > 180: dist_ang = 360 - dist_ang
                mid_r = raio_interno * np.cos(np.radians(dist_ang / 2))
                
                fig.add_trace(go.Scatterpolar(
                    r=[mid_r], theta=[mid_theta],
                    mode='text', text=[simbolo_asp],
                    textfont=dict(size=16, color=cor_asp, family="Arial Black"),
                    showlegend=False, hoverinfo='skip'
                ))

    # --- 5. SIGNOS E RÉGUA ---
    # for i, nome_arq in enumerate(ARQUIVOS_SVG):
    #     centro_polar = i * 30 + 15
    #     fig.add_trace(go.Barpolar(r=[2], theta=[centro_polar], width=[30], base=8, 
    #                               marker_color="white", marker_line_color="black", marker_line_width=1, showlegend=False, hoverinfo='skip'))
        
    #     img_data = converter_svg_para_base64(os.path.join(pasta_icones, nome_arq))
    #     if img_data:
    #         rad = np.radians(180 + centro_polar)
    #         raio_pos = 0.46
    #         fig.add_layout_image(dict(
    #             source=img_data, xref="paper", yref="paper",
    #             x=0.5 + (raio_pos * np.cos(rad)), y=0.5 + (raio_pos * np.sin(rad)),
    #             sizex=0.05, sizey=0.05, xanchor="center", yanchor="middle", layer="above"
    #         ))
    #     for g in range(30):
    #         raio_p = 8.6 if g % 10 == 0 else 8.3
    #         fig.add_trace(go.Scatterpolar(r=[8.0, raio_p], theta=[i*30+g, i*30+g], mode='lines', 
    #                                       line=dict(color="black", width=1), showlegend=False, hoverinfo='skip'))

    # fig.add_trace(go.Scatterpolar(r=[10] * 361, theta=list(range(361)), mode='lines', 
    #                               line=dict(color="black", width=2), showlegend=False, hoverinfo='skip'))

    # --- 6. PLANETAS E TEXTOS (CORREÇÃO DE TRAÇADO AQUI) ---
    for p in posicoes:
        hover_template = f"{p['nome']}<br>{p['signo']}<br>{p['grau_int']}º{p['min_int']}'<extra></extra>"
        
        fig.add_trace(go.Scatterpolar(r=[6.2], theta=[p["long_visual"]], mode='text', text=[f"{p['grau_int']}°"], 
                                      textfont=dict(size=30, color="black", family="Trebuchet MS"), 
                                      showlegend=False, hovertemplate=hover_template))
        fig.add_trace(go.Scatterpolar(r=[5.3], theta=[p["long_visual"]], mode='text', text=[f"{p['min_int']}'"], 
                                      textfont=dict(size=26, color="black", family="Trebuchet MS"), 
                                      showlegend=False, hovertemplate=hover_template))
        fig.add_trace(go.Scatterpolar(r=[raio_interno], theta=[p["long"]], mode='markers', 
                                      marker=dict(size=8, color=p["cor"], line=dict(color='black', width=0)), 
                                      showlegend=False, hovertemplate=hover_template))
        
        # AJUSTE: Símbolos dos planetas com família de fonte mais pesada para uniformizar Marte e Vênus
        fig.add_trace(go.Scatterpolar(
            r=[7.3], theta=[p["long_visual"]], 
            mode='text', 
            text=[f"<b>{p['sym']}</b>"], # Adicionado Negrito via tag HTML
            textfont=dict(size=45, color=p["cor"], family="Arial Black"), 
            showlegend=False, hovertemplate=hover_template
        ))
        
        fig.add_trace(go.Scatterpolar(r=[8.0], theta=[p["long"]], mode='markers', 
                                      marker=dict(size=10, color=p["cor"], line=dict(color='black', width=0)), 
                                      showlegend=False, hovertemplate=hover_template))

    # --- 7. LAYOUT FINAL ---
    fig.update_layout(
        width=900, height=900,
        polar=dict(
            radialaxis=dict(visible=False, range=[0, 10]),
            angularaxis=dict(direction="counterclockwise", rotation=180, showgrid=False, showticklabels=False)
        ),
        hoverlabel=dict(bgcolor="white", font_size=14, font_family="Arial"),
        showlegend=False, margin=dict(t=50, b=50, l=50, r=50), dragmode=False
    )
    return fig