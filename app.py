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
pd.set_option('future.no_silent_downcasting', True)

# --- CONSTANTES ---
SIGNOS = ["Áries", "Touro", "Gêmeos", "Câncer", "Leão", "Virgem", 
          "Libra", "Escorpião", "Sagitário", "Capricórnio", "Aquário", "Peixes"]

LISTA_PLANETAS_UI = ["Sol", "Lua", "Mercúrio", "Vênus", "Marte", "Júpiter", "Saturno", "Urano", "Netuno", "Plutão"]

ASPECTOS = {
    0: "Conjunção", 30: "Semi-sêxtil", 60: "Sêxtil", 90: "Quadratura", 
    120: "Trígono", 150: "Quincúncio", 180: "Oposição"
}

# --- FUNÇÕES AUXILIARES ---
def get_signo(longitude):
    return SIGNOS[int(longitude / 30) % 12]

def dms_to_dec(dms_str):
    if isinstance(dms_str, (int, float)): return float(dms_str)
    try:
        if not re.match(r"^\d+(\.\d+)?$", str(dms_str)): return None
        parts = str(dms_str).split('.')
        degrees = float(parts[0])
        minutes = float(parts[1]) if len(parts) > 1 else 0
        return degrees + (minutes / 60)
    except: return None

def hex_to_rgba(hex_color, opacity):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({r}, {g}, {b}, {opacity})'

def calcular_aspecto(long1, long2):
    diff = abs(long1 - long2) % 360
    if diff > 180: diff = 360 - diff
    for angulo, nome in ASPECTOS.items():
        if abs(diff - angulo) <= 5: # Orbe de 5 graus
            return nome
    return "Outro"

# --- INTERFACE LATERAL ---
st.sidebar.header("Configurações")
ano = st.sidebar.number_input("Ano da Análise", min_value=1900, max_value=2100, value=2026)
grau_input = st.sidebar.text_input("Grau Natal (0 a 30°)", value="27.0")

planeta_sel = st.sidebar.selectbox("Planeta", options=["Escolha um planeta"] + LISTA_PLANETAS_UI)
signo_sel = st.sidebar.selectbox("Signo do Zodíaco", options=["Escolha um signo"] + SIGNOS)

grau_decimal = dms_to_dec(grau_input)
incluir_lua = st.sidebar.checkbox("Quero analisar a Lua", value=False)
mes_selecionado = st.sidebar.slider("Mês da Lua", 1, 12, 1) if incluir_lua else None

if grau_decimal is None:
    st.error("⚠️ Insira um grau válido.")
    st.stop()

# Lógica Cosmética para Tabela
p_label = planeta_sel if planeta_sel != "Escolha um planeta" else "Planeta"
s_label = signo_sel if signo_sel != "Escolha um signo" else "Signo"
idx_signo_natal = SIGNOS.index(signo_sel) if signo_sel in SIGNOS else 0
long_natal_fake = (idx_signo_natal * 30) + grau_decimal

# --- PROCESSAMENTO ---
@st.cache_data
def get_data(ano_ref, grau_ref, analisar_lua, mes_unico):
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
    if analisar_lua: planetas_cfg.insert(1, {"id": swe.MOON, "nome": "LUA", "cor": "#A6A6A6"})

    jd_start = swe.julday(ano_ref, mes_unico if mes_unico else 1, 1)
    jd_end = swe.julday(ano_ref + (0 if mes_unico else 1), (mes_unico + 1) if mes_unico and mes_unico < 12 else (1 if mes_unico else 1), 1)
    
    steps = np.arange(jd_start, jd_end, 0.005 if analisar_lua else 0.05)
    all_data = []
    
    for jd in steps:
        y, m, d, h = swe.revjul(jd)
        dt = datetime(y, m, d, int(h), int((h%1)*60))
        row = {'date': dt}
        for p in planetas_cfg:
            res, _ = swe.calc_ut(jd, p['id'], swe.FLG_SWIEPH | swe.FLG_SPEED)
            long_abs, vel = res[0], res[3]
            dist = abs(((long_abs % 30 - grau_ref + 15) % 30) - 15)
            val = np.exp(-0.5 * (dist / 1.7)**2)
            row[p['nome']] = val if dist <= 5.0 else 0
            row[f"{p['nome']}_long"] = long_abs
            row[f"{p['nome']}_ret"] = "Retrógrado" if vel < 0 else "Direto"
        all_data.append(row)
    return pd.DataFrame(all_data), planetas_cfg

df, planetas_cfg = get_data(ano, grau_decimal, incluir_lua, mes_selecionado)

# --- GERAÇÃO DA TABELA DE EVENTOS ---
eventos = []
for p in planetas_cfg:
    nome = p['nome']
    serie = df[nome].values
    for i in range(1, len(serie)-1):
        if serie[i] > 0.98 and serie[i] > serie[i-1] and serie[i] > serie[i+1]:
            # Achar início e fim (onde a intensidade zera)
            idx_ini = i
            while idx_ini > 0 and serie[idx_ini] > 0.01: idx_ini -= 1
            idx_fim = i
            while idx_fim < len(serie)-1 and serie[idx_fim] > 0.01: idx_fim += 1
            
            row_pico = df.iloc[i]
            long_trans = row_pico[f"{nome}_long"]
            
            eventos.append({
                "Início": df.iloc[idx_ini]['date'].strftime('%d/%m/%Y %H:%M'),
                "Pico": row_pico['date'].strftime('%d/%m/%Y %H:%M'),
                "Término": df.iloc[idx_fim]['date'].strftime('%d/%m/%Y %H:%M'),
                "Grau Natal": f"{grau_input}°",
                "Planeta e Signo Natal": f"{p_label} em {s_label}",
                "Planeta e Signo em Trânsito": f"{nome} em {get_signo(long_trans)}",
                "Status": row_pico[f"{nome}_ret"],
                "Aspecto": calcular_aspecto(long_trans, long_natal_fake)
            })

df_eventos = pd.DataFrame(eventos)

# --- LAYOUT SUPERIOR ---
st.markdown(f"<h1>🔭 Revolução Planetária {ano}</h1>", unsafe_allow_html=True)
st.markdown(f"Ponto Natal: **{p_label} a {grau_input}° de {s_label}**")

# BOTÕES ACIMA DO GRÁFICO
st.write("### 📥 Downloads")
c1, c2, c3 = st.columns(3)
with c1:
    csv_ev = df_eventos.to_csv(index=False).encode('utf-8')
    st.download_button("📊 Baixar Tabela (CSV)", csv_ev, "tabela_eventos.csv", "text/csv")
with c2:
    csv_raw = df.to_csv(index=False).encode('utf-8')
    st.download_button("📈 Baixar Dados Brutos (CSV)", csv_raw, "dados_grafico.csv", "text/csv")
with c3:
    html_buffer = io.StringIO()
    # Gráfico será gerado abaixo, mas o botão precisa do objeto 'fig'
    pass # Definido após gerar fig

# --- GRÁFICO ---
fig = go.Figure()
for p in planetas_cfg:
    # Filtra zeros para o gráfico ficar limpo
    df_plot = df[df[p['nome']] > 0]
    fig.add_trace(go.Scatter(
        x=df['date'], y=df[p['nome']], name=p['nome'],
        line=dict(color=p['cor'], width=2),
        fill='tozeroy', fillcolor=hex_to_rgba(p['cor'], 0.1),
        hovertemplate="<b>%{x|%d/%m/%Y %H:%M}</b><br>Intensidade: %{y:.2f}<extra></extra>"
    ))
    # Datas nos picos (cinza para dark mode)
    picos_plot = df[(df[p['nome']] > 0.98) & (df[p['nome']] > df[p['nome']].shift(1)) & (df[p['nome']] > df[p['nome']].shift(-1))]
    fig.add_trace(go.Scatter(
        x=picos_plot['date'], y=picos_plot[p['nome']]+0.05,
        mode='text', text=picos_plot['date'].dt.strftime('%d/%m'),
        textfont=dict(color="#CCCCCC", size=10), showlegend=False
    ))

fig.update_layout(
    height=600, template='plotly_white', hovermode='x unified',
    xaxis=dict(rangeslider=dict(visible=True), hoverformat='%d/%m/%Y %H:%M'),
    yaxis=dict(range=[0, 1.3])
)

st.plotly_chart(fig, use_container_width=True)

# --- EXIBIÇÃO DA TABELA ---
st.write("### 📅 Tabela de Trânsitos")
st.dataframe(df_eventos, use_container_width=True)