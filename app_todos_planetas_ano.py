import streamlit as st
import swisseph as swe
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Revolução Planetária", layout="wide")

# Silencia avisos do Pandas
pd.set_option('future.no_silent_downcasting', True)

# --- CONSTANTES ---
SIGNOS = ["Áries", "Touro", "Gêmeos", "Câncer", "Leão", "Virgem", 
          "Libra", "Escorpião", "Sagitário", "Capricórnio", "Aquário", "Peixes"]

ASPECTOS = {
    0: ("Conjunção", "☌"), 30: ("Semi-sêxtil", "⚺"), 60: ("Sêxtil", "✶"), 
    90: ("Quadratura", "□"), 120: ("Trígono", "△"), 150: ("Quincúncio", "⚻"), 180: ("Oposição", "☍")
}

# --- FUNÇÕES AUXILIARES ---
def get_signo(longitude):
    return SIGNOS[int(longitude / 30) % 12]

def dms_to_dec(dms_str):
    if isinstance(dms_str, (int, float)): return float(dms_str)
    try:
        parts = str(dms_str).split('.')
        return float(parts[0]) + (float(parts[1])/60 if len(parts) > 1 else 0)
    except: return 0.0

def hex_to_rgba(hex_color, opacity):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({r}, {g}, {b}, {opacity})'

def calcular_aspecto(long1, long2):
    diff = abs(long1 - long2) % 360
    if diff > 180: diff = 360 - diff
    for angulo, (nome, simbolo) in ASPECTOS.items():
        if abs(diff - angulo) <= 5: return nome
    return "Outro"

def obter_simbolo_aspecto(long1, long2):
    diff = abs(long1 - long2) % 360
    if diff > 180: diff = 360 - diff
    for angulo, (nome, simbolo) in ASPECTOS.items():
        if abs(diff - angulo) <= 5: return simbolo
    return ""

# --- INTERFACE LATERAL ---
st.sidebar.title("🪐 Configurações")
ano_analise = st.sidebar.number_input("Ano da Revolução", 1900, 2100, 2026)

planetas_monitorados = [
    {"id": swe.SUN, "nome": "SOL", "cor": "#FFF12E"},
    {"id": swe.MERCURY, "nome": "MERCÚRIO", "cor": "#F3A384"},
    {"id": swe.VENUS, "nome": "VÊNUS", "cor": "#0A8F11"},
    {"id": swe.MARS, "nome": "MARTE", "cor": "#F10808"},
    {"id": swe.JUPITER, "nome": "JÚPITER", "cor": "#1746C9"},
    {"id": swe.SATURN, "nome": "SATURNO", "cor": "#381094"},
    {"id": swe.URANUS, "nome": "URANO", "cor": "#FF00FF"},
    {"id": swe.NEPTUNE, "nome": "NETUNO", "cor": "#1EFF00"},
    {"id": swe.PLUTO, "nome": "PLUTÃO", "cor": "#14F1F1"}
]

st.sidebar.subheader("Dados Natais")
ponto_inicial = [
    {"p": "Sol", "s": "Virgem", "g": "27.0"}, {"p": "Lua", "s": "Leão", "g": "6.2"},
    {"p": "Mercúrio", "s": "Libra", "g": "19.59"}, {"p": "Vênus", "s": "Libra", "g": "5.16"},
    {"p": "Marte", "s": "Escorpião", "g": "8.48"}, {"p": "Júpiter", "s": "Sagitário", "g": "8.57"},
    {"p": "Saturno", "s": "Peixes", "g": "20.53"}, {"p": "Urano", "s": "Capricórnio", "g": "26.37"},
    {"p": "Netuno", "s": "Capricórnio", "g": "22.50"}, {"p": "Plutão", "s": "Escorpião", "g": "28.19"}
]

alvos_input = []
for i, alvo in enumerate(ponto_inicial):
    with st.sidebar.expander(f"{alvo['p']} Natal"):
        s = st.selectbox("Signo", SIGNOS, index=SIGNOS.index(alvo['s']), key=f"s{i}")
        g = st.text_input("Grau", value=alvo['g'], key=f"g{i}")
        alvos_input.append({"planeta": alvo['p'], "signo": s, "grau": g})

# --- PROCESSAMENTO ---
if st.sidebar.button("Calcular Revolução", use_container_width=True):
    with st.spinner("Sincronizando efemérides..."):
        
        fig = make_subplots(
            rows=len(alvos_input), cols=1,
            subplot_titles=[f"<b>{a['planeta']} Natal em {a['signo']} {a['grau']}°</b>" for a in alvos_input],
            vertical_spacing=0.025,
            shared_xaxes=True
        )

        jd_start = swe.julday(ano_analise, 1, 1)
        jd_end = swe.julday(ano_analise + 1, 1, 1)
        steps = np.arange(jd_start, jd_end, 0.1)
        flags = swe.FLG_SWIEPH | swe.FLG_SPEED

        for idx_alvo, alvo in enumerate(alvos_input):
            grau_decimal = dms_to_dec(alvo["grau"])
            idx_signo_natal = SIGNOS.index(alvo["signo"])
            long_natal_absoluta = (idx_signo_natal * 30) + grau_decimal
            
            all_data = []
            for jd in steps:
                y, m, d, h = swe.revjul(jd)
                dt = datetime(y, m, d, int(h), int((h%1)*60))
                row = {'date': dt}
                
                for p in planetas_monitorados:
                    res, _ = swe.calc_ut(jd, p["id"], flags)
                    long_abs, velocidade = res[0], res[3]
                    status = "Retrógrado" if velocidade < 0 else "Direto"
                    mov_abrev = " (R)" if velocidade < 0 else " (D)"
                    
                    pos_no_signo = long_abs % 30
                    grau = int(pos_no_signo)
                    minutos = int((pos_no_signo % 1) * 60)

                    dist = abs(((pos_no_signo - grau_decimal + 15) % 30) - 15)
                    val = np.exp(-0.5 * (dist / 1.7)**2)
                    
                    intensidade_txt = "Forte" if dist <= 1.0 else "Médio" if dist <= 2.5 else "Fraco"
                    simbolo = obter_simbolo_aspecto(long_abs, long_natal_absoluta)
                    simbolo_html = f"<span style='font-size: 18px;'><b>{simbolo}</b></span>" if simbolo else ""
                    
                    row[p["nome"]] = val if dist <= 5.0 else None
                    row[f"{p['nome']}_long"] = long_abs
                    row[f"{p['nome']}_status"] = status
                    row[f"{p['nome']}_info"] = f"{get_signo(long_abs)}{mov_abrev} {grau:02d}°{minutos:02d}' - {intensidade_txt} {simbolo_html}"
            
            all_data.append(row)

            df = pd.DataFrame(all_data).infer_objects(copy=False)
            
        
            for p in planetas_monitorados:
                if f"{p['nome']}_info" not in df.columns: df[f"{p['nome']}_info"] = ""

            for p in planetas_monitorados:
            # Gráfico de Área (Intensidade)
                fig.add_trace(go.Scatter(
                    x=df['date'], y=df[p['nome']],
                    mode='lines', name=p['nome'],
                    legendgroup=p['nome'],
                    showlegend=(idx_alvo == 0), # Mostra legenda apenas no primeiro subplot
                    line=dict(color=p['cor'], width=2.5),
                    fill='tozeroy',
                    fillcolor=hex_to_rgba(p['cor'], 0.15),
                    customdata=df[f"{p['nome']}_info"],
                    hovertemplate="<b>%{customdata}</b><extra></extra>",
                    connectgaps=False
                ), row=idx_alvo+1, col=1)

                # Marcadores de Picos
                serie_p = df[p['nome']].fillna(0)
                peak_mask = (serie_p > 0.98) & (serie_p > serie_p.shift(1)) & (serie_p > serie_p.shift(-1))
                picos = df[peak_mask]
            
                if not picos.empty:
                    fig.add_trace(go.Scatter(
                        x=picos['date'], y=picos[p['nome']] + 0.04,
                        mode='markers+text',
                        text=picos['date'].dt.strftime('%d/%m'),
                        textposition="top center",
                        textfont=dict(family="Arial", size=10, color="black"),
                        marker=dict(symbol="triangle-down", color=p['cor'], size=8),
                        legendgroup=p['nome'], showlegend=False, hoverinfo='skip'
                    ), row=idx_alvo+1, col=1)

        # Layout Final Dark
        fig.update_layout(
            height=520 * len(alvos_input), # Altura proporcional ao número de alvos
            title=dict(text=f"<b>Revolução Planetária {ano_analise}</b>", x=0.5, y=0.98, yanchor="top", font = dict(size = 24)),
            template='plotly_white',
            hovermode='x unified', dragmode='pan', margin=dict(t=240, b=50, l=50, r=50),
            legend=dict(orientation="h", yanchor="top", y=0.97, yref="container", xanchor="center", x=0.5)
        )

        fig.update_xaxes(type='date', tickformat='%d/%m\n%Y', hoverformat='%d/%m/%Y %H:%M', showticklabels=True, visible=True)
        fig.update_yaxes(title='Intensidade', range=[0, 1.3], fixedrange=True)
        fig.update_annotations(patch=dict(font=dict(size=14), yshift=20))

        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Utilize o menu lateral para configurar os dados e clique em 'Calcular Revolução'.")