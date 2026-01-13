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
        if abs(diff - angulo) <= 8:  # Orbe de tolerância
            return simbolo
    return ""

def criar_mandala_astrologica(ano, mes, dia, hora_decimal):
    # Cálculo do Julian Day (Apenas argumentos posicionais para evitar TypeError)
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

    # Lógica anti-sobreposição (ajuste visual dos símbolos)
    posicoes.sort(key=lambda x: x['long'])
    for _ in range(5):
        for i in range(len(posicoes)):
            next_idx = (i + 1) % len(posicoes)
            diff = (posicoes[next_idx]['long_visual'] - posicoes[i]['long_visual']) % 360
            if diff < 10:
                posicoes[next_idx]['long_visual'] = (posicoes[i]['long_visual'] + 10) % 360

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

    # --- 2. ANEL DOS SIGNOS E RÉGUA ---
    for i, signo in enumerate(SIGNOS):
        centro_polar = i * 30 + 15
        fig.add_trace(go.Barpolar(r=[2], theta=[centro_polar], width=[30], base=8, 
                                  marker_color="white", marker_line_color="black", marker_line_width=1, showlegend=False, hoverinfo='skip'))

        fig.add_trace(go.Barpolar(
            r=[2], theta=[i * 30 + 15], width=[30], base=8, 
            marker_color="white", marker_line_color="#333", marker_line_width=1,
            opacity=0.1, showlegend=False, hoverinfo='skip'))
        
        # Nomes dos Signos
        fig.add_trace(go.Scatterpolar(
            r=[9.2], theta=[i * 30 + 15], mode='text', text=[SIGNOS[i][:3]],
            textfont=dict(size=12, color="#555", family="Arial Black"), showlegend=False))

    fig.add_trace(go.Scatterpolar(r=[10] * 361, theta=list(range(361)), mode='lines', 
                                  line=dict(color="black", width=2), showlegend=False, hoverinfo='skip'))

    # --- 3. PLANETAS E GRAUS ---
    for p in posicoes:
        hover_template = f"<b>{p['nome']}</b><br>{p['signo']} {p['grau_int']}°{p['min_int']}'<extra></extra>"
        
        # Símbolo do Planeta (Centralizado no long_visual)
        fig.add_trace(go.Scatterpolar(
            r=[7.3], theta=[p["long_visual"]], mode='text', 
            text=[f"<b>{p['sym']}</b>"],
            textfont=dict(size=38, color=p["cor"], family="Arial Black"),
            hovertext=hover_template, hoverinfo="text", showlegend=False))
        
        # Grau e Minuto (Abaixo do símbolo)
        fig.add_trace(go.Scatterpolar(
            r=[6.0], theta=[p["long_visual"]], mode='text', 
            text=[f"{p['grau_int']}°{p['min_int']}'"],
            textfont=dict(size=14, color="black", family="Trebuchet MS"), 
            hoverinfo='skip', showlegend=False))
        
        # Marcador na régua (Posição real exata)
        fig.add_trace(go.Scatterpolar(
            r=[8.0], theta=[p["long"]], mode='markers', 
            marker=dict(size=8, color=p["cor"], line=dict(color='black', width=1)),
            hoverinfo='skip', showlegend=False))

    # --- LAYOUT FINAL ---
    fig.update_layout(
        width=700, height=700,
        polar=dict(
            radialaxis=dict(visible=False, range=[0, 10]),
            angularaxis=dict(
                direction="counterclockwise", 
                rotation=180, # Áries à esquerda
                showgrid=True, 
                gridcolor="rgba(0,0,0,0.1)",
                showticklabels=False
            )
        ),
        margin=dict(t=50, b=50, l=50, r=50),
        paper_bgcolor="black",
        dragmode=False
    )
    return fig

# --- INTERFACE STREAMLIT ---
st.sidebar.title("🪐 Configurações")
data_escolhida = st.sidebar.date_input("Data de Referência", datetime.now())
hora_escolhida = st.sidebar.time_input("Hora de Referência", datetime.now())

# Conversão de hora para decimal
hora_decimal = hora_escolhida.hour + (hora_escolhida.minute / 60.0)

st.title(f"🔭 Mandala Astrológica Interativa")
st.subheader(f"{data_escolhida.strftime('%d/%m/%Y')} às {hora_escolhida.strftime('%H:%M')}")

col1, col2 = st.columns([1.5, 1])

with col1:
    fig_mandala = criar_mandala_astrologica(data_escolhida.year, data_escolhida.month, data_escolhida.day, hora_decimal)
    st.plotly_chart(fig_mandala, use_container_width=False)

with col2:
    st.write("### Posições Detalhadas")
    jd = swe.julday(data_escolhida.year, data_escolhida.month, data_escolhida.day, hora_decimal)
    ids = {"Sol": 0, "Lua": 1, "Mercúrio": 2, "Vênus": 3, "Marte": 4, "Júpiter": 5, "Saturno": 6, "Urano": 7, "Netuno": 8, "Plutão": 9}
    
    dados = []
    for nome, pid in ids.items():
        res, _ = swe.calc_ut(jd, pid, swe.FLG_SWIEPH)
        long_abs = res[0]
        grau_s = long_abs % 30
        min_i = int(round((grau_s % 1) * 60))
        grau_i = int(grau_s)
        if min_i == 60: min_i = 0; grau_i += 1
        
        dados.append({
            "Planeta": nome,
            "Signo": SIGNOS[int(long_abs / 30)],
            "Posição": f"{grau_i:02d}°{min_i:02d}'"
        })
    
    st.table(pd.DataFrame(dados))