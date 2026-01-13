import streamlit as st
import swisseph as swe
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Mandala Astrológica Viva", layout="wide")

SIGNOS = ["Áries", "Touro", "Gêmeos", "Câncer", "Leão", "Virgem", 
          "Libra", "Escorpião", "Sagitário", "Capricórnio", "Aquário", "Peixes"]

SIMBOLOS_PLANETAS = {
    "SOL": "☉", "LUA": "☽", "MERCÚRIO": "☿", "VÊNUS": "♀", 
    "MARTE": "♂", "JÚPITER": "♃", "SATURNO": "♄", "URANO": "♅", 
    "NETUNO": "♆", "PLUTÃO": "♇"
}

CORES_SIGNOS = [
    "#FF4B4B", "#FF9F4B", "#FFD34B", "#99FF4B", "#4BFF81", "#4BFFD3",
    "#4BAFFF", "#4B5BFF", "#814BFF", "#D34BFF", "#FF4B9F", "#FF4B4B"
]

# --- CÁLCULOS ASTRONÔMICOS ---
def obter_posicoes_atuais(jd):
    planetas_ids = {
        "SOL": swe.SUN, "LUA": swe.MOON, "MERCÚRIO": swe.MERCURY, 
        "VÊNUS": swe.VENUS, "MARTE": swe.MARS, "JÚPITER": swe.JUPITER, 
        "SATURNO": swe.SATURN, "URANO": swe.URANUS, "NETUNO": swe.NEPTUNE, "PLUTÃO": swe.PLUTO
    }
    posicoes = []
    for nome, pid in planetas_ids.items():
        res, _ = swe.calc_ut(jd, pid, swe.FLG_SWIEPH)
        long_abs = res[0]
        posicoes.append({
            "nome": nome,
            "simbolo": SIMBOLOS_PLANETAS[nome],
            "long_abs": long_abs,
            "signo": SIGNOS[int(long_abs / 30)],
            "grau": long_abs % 30
        })
    return posicoes

def polar_to_cartesian(angle_deg, radius, offset_deg=-90):
    # O offset_deg=-90 faz com que o 0° (Áries) comece no Ascendente (Esquerda/9 horas)
    rad = np.radians(angle_deg + offset_deg)
    return radius * np.cos(rad), radius * np.sin(rad)

# --- CONSTRUÇÃO DO GRÁFICO ---
def desenhar_mandala(posicoes):
    fig = go.Figure()

    # 1. Anel dos Signos (Fundo)
    for i, signo in enumerate(SIGNOS):
        # Cada signo ocupa 30 graus
        start_angle = i * 30
        end_angle = (i + 1) * 30
        angles = np.linspace(start_angle, end_angle, 50)
        
        # Coordenadas do arco externo
        outer_x = [polar_to_cartesian(a, 10)[0] for a in angles]
        outer_y = [polar_to_cartesian(a, 10)[1] for a in angles]
        # Coordenadas do arco interno
        inner_x = [polar_to_cartesian(a, 8.5)[0] for a in reversed(angles)]
        inner_y = [polar_to_cartesian(a, 8.5)[1] for a in reversed(angles)]

        fig.add_trace(go.Scatter(
            x=outer_x + inner_x, y=outer_y + inner_y,
            fill="toself", fillcolor=CORES_SIGNOS[i],
            line=dict(color="white", width=1),
            opacity=0.4, hoverinfo="text", text=signo, showlegend=False
        ))
        
        # Nome do Signo
        tx, ty = polar_to_cartesian(start_angle + 15, 9.25)
        fig.add_annotation(x=tx, y=ty, text=signo[:3], showarrow=False, font=dict(size=10, color="white"))

    # 2. Linhas de Divisão (Cúspides)
    for a in range(0, 360, 30):
        x0, y0 = polar_to_cartesian(a, 8.5)
        x1, y1 = polar_to_cartesian(a, 4)
        fig.add_shape(type="line", x0=x0, y0=y0, x1=x1, y1=y1, line=dict(color="rgba(255,255,255,0.2)"))

    # 3. Planetas
    for p in posicoes:
        px, py = polar_to_cartesian(p['long_abs'], 7)
        fig.add_trace(go.Scatter(
            x=[px], y=[py],
            mode="markers+text",
            text=[p['simbolo']],
            textfont=dict(size=20),
            marker=dict(size=12, color="white"),
            hovertext=f"<b>{p['nome']}</b><br>{p['signo']} {int(p['grau'])}°",
            hoverinfo="text", showlegend=False
        ))

    fig.update_layout(
        width=800, height=800,
        plot_bgcolor="black", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False, range=[-11, 11]),
        yaxis=dict(visible=False, range=[-11, 11]),
        margin=dict(t=20, b=20, l=20, r=20)
    )
    return fig

# --- INTERFACE ---
st.title("🔭 Mandala Planetária em Tempo Real")

with st.sidebar:
    st.header("Configurações de Tempo")
    data_ref = st.date_input("Data", datetime.now())
    hora_ref = st.time_input("Hora (Local)", datetime.now())
    fuso = st.number_input("Fuso Horário (UTC)", -12, 12, -3)

# Cálculo do Julian Day
hora_decimal = hora_ref.hour + (hora_ref.minute / 60.0) - fuso
jd = swe.julday(data_ref.year, data_ref.month, data_ref.day, hora_decimal)

posicoes = obter_posicoes_atuais(jd)

# Layout Principal
col_map, col_info = st.columns([2, 1])

with col_map:
    mandala = desenhar_mandala(posicoes)
    st.plotly_chart(mandala, use_container_width=True)



with col_info:
    st.subheader("Posições Exatas")
    df_pos = pd.DataFrame(posicoes)[["nome", "signo", "grau"]]
    df_pos["grau"] = df_pos["grau"].apply(lambda x: f"{int(x)}° {int((x%1)*60)}'")
    st.table(df_pos)