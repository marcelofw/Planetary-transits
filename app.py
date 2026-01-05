import streamlit as st
import swisseph as swe
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import io
import re

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Revolução Planetária Profissional", layout="wide")

# Silencia avisos de downcasting para compatibilidade futura com Pandas
pd.set_option('future.no_silent_downcasting', True)

# --- CONSTANTES E FUNÇÕES AUXILIARES ---
SIGNOS = ["Áries", "Touro", "Gêmeos", "Câncer", "Leão", "Virgem", 
          "Libra", "Escorpião", "Sagitário", "Capricórnio", "Aquário", "Peixes"]

LISTA_PLANETAS_UI = ["Sol", "Lua", "Mercúrio", "Vênus", "Marte", "Júpiter", "Saturno", "Urano", "Netuno", "Plutão"]

def get_signo(longitude):
    return SIGNOS[int(longitude / 30) % 12]

def dms_to_dec(dms_str):
    if isinstance(dms_str, (int, float)): return float(dms_str)
    try:
        if not re.match(r"^\d+(\.\d+)?$", str(dms_str)): return None
        parts = str(dms_str).split('.')
        degrees = float(parts[0])
        minutes = float(parts[1]) if len(parts) > 1 else 0
        val = degrees + (minutes / 60)
        return val if 0 <= val <= 30 else None
    except:
        return None

def hex_to_rgba(hex_color, opacity):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({r}, {g}, {b}, {opacity})'

# --- INTERFACE LATERAL (Sidebar) ---
st.sidebar.header("Configurações")
ano = st.sidebar.number_input("Ano da Análise", min_value=1900, max_value=2100, value=2026)
grau_input = st.sidebar.text_input("Grau Alvo Natal (0 a 30°)", value="27.0")

# NOVOS CAMPOS SOLICITADOS
planeta_alvo_ui = st.sidebar.selectbox("Planeta Alvo", options=LISTA_PLANETAS_UI)
signo_alvo_ui = st.sidebar.selectbox("Signo do Zodíaco", options=SIGNOS)

# Validação do Grau e Cálculo da Longitude Absoluta Alvo
grau_decimal = dms_to_dec(grau_input)
if grau_decimal is not None:
    # A longitude absoluta é (índice do signo * 30) + grau dentro do signo
    idx_signo = SIGNOS.index(signo_alvo_ui)
    longitude_alvo_absoluta = (idx_signo * 30) + grau_decimal

# Funcionalidade da Lua (Monitoramento da curva da Lua)
incluir_lua = st.sidebar.checkbox("Quero analisar a Lua", value=False)
mes_selecionado = None
if incluir_lua:
    mes_selecionado = st.sidebar.slider("Mês da Lua", min_value=1, max_value=12, value=1)

if grau_decimal is None:
    st.error("⚠️ Erro: Por favor, insira um valor numérico válido entre 0 e 30.")
    st.stop()

# Título visual atualizado com o Planeta e Signo
st.markdown(f"""
    <div style='text-align: left;'>
        <h1 style='font-size: 2.5rem; margin-bottom: 0;'>🔭 Revolução Planetária {ano}</h1>
        <p style='font-size: 1.2rem; color: #555;'>Ponto Natal: <b>{planeta_alvo_ui} a {grau_input}° de {signo_alvo_ui}</b></p>
    </div>
""", unsafe_allow_html=True)

# --- PROCESSAMENTO DE DADOS ---
@st.cache_data
def get_planetary_data(ano_ref, long_alvo_ref, analisar_lua, mes_unico):
    planetas_cfg = [
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
    
    if analisar_lua:
        planetas_cfg.insert(1, {"id": swe.MOON, "nome": "LUA", "cor": "#A6A6A6"})

    flags = swe.FLG_SWIEPH | swe.FLG_SPEED

    if analisar_lua and mes_unico:
        jd_start = swe.julday(ano_ref, mes_unico, 1)
        prox_m = mes_unico + 1 if mes_unico < 12 else 1
        prox_a = ano_ref if mes_unico < 12 else ano_ref + 1
        jd_end = swe.julday(prox_a, prox_m, 1)
        step_size = 0.005 
    else:
        jd_start = swe.julday(ano_ref, 1, 1)
        jd_end = swe.julday(ano_ref + 1, 1, 1)
        step_size = 0.05
    
    steps = np.arange(jd_start, jd_end, step_size)
    all_data = []
    
    for jd in steps:
        y, m, d, h = swe.revjul(jd)
        dt = datetime(y, m, d, int(h), int((h%1)*60))
        row = {'date': dt}
        
        for p in planetas_cfg:
            res, _ = swe.calc_ut(jd, p["id"], flags)
            long_abs, velocidade = res[0], res[3]
            mov = " (R)" if velocidade < 0 else " (D)"
            
            # Cálculo de distância circular absoluta (em relação aos 360°)
            dist = abs(((long_abs - long_alvo_ref + 180) % 360) - 180)
            
            # Intensidade Gaussiana (Sigma 1.7 para orbe de ~5 graus)
            val = np.exp(-0.5 * (dist / 1.7)**2)
            
            row[p["nome"]] = val if dist <= 5.0 else None
            row[f"{p['nome']}_info"] = f"{get_signo(long_abs)}{mov}"
            
        all_data.append(row)
    
    return pd.DataFrame(all_data).infer_objects(copy=False), planetas_cfg

df, lista_planetas = get_planetary_data(ano, longitude_alvo_absoluta, incluir_lua, mes_selecionado)

# --- CONSTRUÇÃO DO GRÁFICO ---
fig = go.Figure()

for p in lista_planetas:
    fig.add_trace(go.Scatter(
        x=df['date'], y=df[p['nome']],
        mode='lines',
        name=p['nome'],
        legendgroup=p['nome'],
        line=dict(color=p['cor'], width=2.5),
        fill='tozeroy',
        fillcolor=hex_to_rgba(p['cor'], 0.15),
        customdata=df[f"{p['nome']}_info"],
        hovertemplate="<b>%{customdata}</b><extra></extra>",
        connectgaps=False 
    ))

    if p['nome'] != "LUA" or (incluir_lua and len(df) < 10000):
        serie_p = df[p['nome']].fillna(0).infer_objects(copy=False)
        peak_mask = (serie_p > 0.98) & (serie_p > serie_p.shift(1)) & (serie_p > serie_p.shift(-1))
        picos = df[peak_mask]
        
        if not picos.empty:
            fig.add_trace(go.Scatter(
                x=picos['date'],
                y=picos[p['nome']] + 0.04,
                mode='markers+text',
                text=picos['date'].dt.strftime('%d/%m'),
                textposition="top center",
                textfont=dict(family="Arial Black", size=10, color="#CCCCCC"),
                marker=dict(symbol="triangle-down", color=p['cor'], size=8),
                legendgroup=p['nome'],
                showlegend=False,
                hoverinfo='skip'
            ))

fig.update_layout(
    height=700,
    xaxis=dict(
        title='Navegue no tempo',
        rangeslider=dict(visible=True, thickness=0.08),
        type='date', tickformat='%d/%m\n%Y',
        hoverformat='%d/%m/%Y %H:%M',
        showspikes=True, spikemode='across', spikethickness=1, spikecolor="gray"
    ),
    yaxis=dict(title='Intensidade', range=[0, 1.3], fixedrange=True),
    template='plotly_white',
    hovermode='x unified', 
    dragmode='pan',
    margin=dict(t=100)
)

st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

# --- DOWNLOADS ---
st.divider()
col1, col2 = st.columns(2)
grau_limpo = str(grau_input).replace('.', '_')
nome_arquivo_base = f"revolucao_{planeta_alvo_ui}_{signo_alvo_ui}_{ano}"

with col1:
    html_buffer = io.StringIO()
    fig.write_html(html_buffer, config={'scrollZoom': True})
    st.download_button("📥 Baixar Gráfico (HTML)", html_buffer.getvalue(), f"{nome_arquivo_base}.html", "text/html")

with col2:
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button("📊 Baixar Dados (CSV)", csv_data, f"dados_{nome_arquivo_base}.csv", "text/csv")