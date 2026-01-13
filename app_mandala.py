import streamlit as st
import swisseph as swe
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import math

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Mandala Astrológica Viva", layout="wide")

# --- CONSTANTES ---
SIGNOS = ["Áries", "Touro", "Gêmeos", "Câncer", "Leão", "Virgem", 
          "Libra", "Escorpião", "Sagitário", "Capricórnio", "Aquário", "Peixes"]

ASPECTOS = {
    0: ("Conjunção", "☌"), 
    60: ("Sêxtil", "✶"), 
    90: ("Quadratura", "□"), 
    120: ("Trígono", "△"), 
    180: ("Oposição", "☍")
}

SIMBOLOS_PLANETAS = {
    "SOL": "☉", "LUA": "☽", "MERCÚRIO": "☿", "VÊNUS": "♀", 
    "MARTE": "♂", "JÚPITER": "♃", "SATURNO": "♄", "URANO": "♅", 
    "NETUNO": "♆", "PLUTÃO": "♇"
}

# --- FUNÇÕES AUXILIARES ---
def obter_simbolo_aspecto(long1, long2):
    diff = abs(long1 - long2) % 360
    if diff > 180: diff = 360 - diff
    for angulo, (nome, simbolo) in ASPECTOS.items():
        if abs(diff - angulo) <= 8: # Orbe ligeiramente maior para visualização
            return simbolo
    return ""

def criar_mandala_astrologica(ano, mes, dia, hora_decimal):
    jd = swe.julday(ano, mes, dia, hora_decimal)
    
    planetas_cfg = [
        {"id": swe.SUN, "nome": "Sol", "cor": "#FFD700", "sym": "☉"},
        {"id": swe.MOON, "nome": "Lua", "cor": "#A6A6A6", "sym": "☽"},
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
    raio_interno = 4.5
    
    # --- POSIÇÕES ---
    posicoes = []
    for p in planetas_cfg:
        res, _ = swe.calc_ut(jd, p["id"], swe.FLG_SWIEPH)
        long_abs = res[0]
        id_signo = int(long_abs / 30)
        grau_no_signo = long_abs % 30
        min_f, gr_i = math.modf(grau_no_signo)
        min_i = int(round(min_f * 60))
        
        posicoes.append({
            "nome": p["nome"], "long": long_abs, "cor": p["cor"], 
            "sym": p["sym"], "grau_int": int(gr_i), "min_int": min_i,
            "signo": SIGNOS[id_signo % 12], "long_visual": long_abs 
        })

    # Lógica simples anti-sobreposição
    posicoes.sort(key=lambda x: x['long'])
    for _ in range(3):
        for i in range(len(posicoes)):
            next_idx = (i + 1) % len(posicoes)
            diff = (posicoes[next_idx]['long_visual'] - posicoes[i]['long_visual']) % 360
            if diff < 8:
                posicoes[next_idx]['long_visual'] = (posicoes[i]['long_visual'] + 8) % 360

    # --- ASPECTOS ---
    CORES_ASPECTOS = {"☌": "#2ecc71", "☍": "#e74c3c", "□": "#e74c3c", "△": "#3498db", "✶": "#3498db"}
    for i in range(len(posicoes)):
        for j in range(i + 1, len(posicoes)):
            p1, p2 = posicoes[i], posicoes[j]
            simbolo_asp = obter_simbolo_aspecto(p1['long'], p2['long'])
            
            if simbolo_asp:
                cor_asp = CORES_ASPECTOS.get(simbolo_asp, "gray")
                fig.add_trace(go.Scatterpolar(
                    r=[raio_interno, raio_interno], theta=[p1['long'], p2['long']],
                    mode='lines', line=dict(color=cor_asp, width=1), opacity=0.4, showlegend=False))

    # --- SIGNOS ---
    for i, signo in enumerate(SIGNOS):
        # Fatias coloridas ao fundo para os signos
        fig.add_trace(go.Barpolar(
            r=[2], theta=[i * 30 + 15], width=[30], base=8, 
            marker_color="white", marker_line_color="#ddd", opacity=0.1, showlegend=False))
        
        # Símbolo do Signo na borda
        fig.add_trace(go.Scatterpolar(
            r=[9.2], theta=[i * 30 + 15], mode='text', text=[SIGNOS[i][:3]],
            textfont=dict(size=12, color="gray"), showlegend=False))

    # --- PLANETAS ---
    for p in posicoes:
        # Símbolo do Planeta
        fig.add_trace(go.Scatterpolar(
            r=[7.2], theta=[p["long_visual"]], mode='text', 
            text=[f"<b>{p['sym']}</b>"],
            textfont=dict(size=35, color=p["cor"], family="Arial Black"),
            hovertext=f"{p['nome']}: {p['grau_int']}°{p['min_int']}' {p['signo']}",
            hoverinfo="text", showlegend=False))
        
        # Grau do Planeta
        fig.add_trace(go.Scatterpolar(
            r=[6.0], theta=[p["long_visual"]], mode='text', 
            text=[f"{p['grau_int']}°"],
            textfont=dict(size=18, color="black"), showlegend=False))

    # --- LAYOUT ---
    fig.update_layout(
        width=800, height=800,
        polar=dict(
            radialaxis=dict(visible=False, range=[0, 10]),
            angularaxis=dict(direction="counterclockwise", rotation=180, showgrid=True, showticklabels=False)
        ),
        margin=dict(t=30, b=30, l=30, r=30),
        paper_bgcolor="white"
    )
    return fig

# --- INTERFACE STREAMLIT ---
st.sidebar.title("🪐 Configurações")
data_escolhida = st.sidebar.date_input("Selecione a Data", datetime.now())
hora_escolhida = st.sidebar.time_input("Selecione a Hora", datetime.now())

# Conversão de hora para decimal
hora_decimal = hora_escolhida.hour + (hora_escolhida.minute / 60.0)

st.title(f"Mandala Astrológica: {data_escolhida.strftime('%d/%m/%Y')} às {hora_escolhida.strftime('%H:%M')}")

# Renderização
fig_mandala = criar_mandala_astrologica(data_escolhida.year, data_escolhida.month, data_escolhida.day, hora_decimal)
st.plotly_chart(fig_mandala, use_container_width=True)

# Tabela de Posições
with st.expander("Ver Posições Detalhadas"):
    # Re-executar cálculo simples para tabela
    jd = swe.julday(data_ref=data_escolhida.year, month=data_escolhida.month, day=data_escolhida.day, hour=hora_decimal)
    # (Lógica simplificada apenas para exemplo)
    st.write("Dados calculados via Swiss Ephemeris (Alta Precisão)")