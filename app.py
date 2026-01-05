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

ASPECTOS = {
    0: "Conjunção", 30: "Semi-sêxtil", 60: "Sêxtil", 90: "Quadratura", 
    120: "Trígono", 150: "Quincúncio", 180: "Oposição"
}

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

def calcular_aspecto(long1, long2):
    diff = abs(long1 - long2) % 360
    if diff > 180: diff = 360 - diff
    for angulo, nome in ASPECTOS.items():
        if abs(diff - angulo) <= 5: # Orbe de 5 graus
            return nome
    return "Outro"

# --- INTERFACE LATERAL (Sidebar) ---
st.sidebar.header("Configurações")
ano = st.sidebar.number_input("Ano da Análise", min_value=1900, max_value=2100, value=2026)
grau_input = st.sidebar.text_input("Grau Natal (0 a 30°)", value="27.0")

planeta_selecionado = st.sidebar.selectbox(
    "Planeta", 
    options=["Escolha um planeta"] + LISTA_PLANETAS_UI,
    index=0
)

signo_selecionado = st.sidebar.selectbox(
    "Signo do Zodíaco", 
    options=["Escolha um signo"] + SIGNOS,
    index=0
)

# Validação do Grau
grau_decimal = dms_to_dec(grau_input)

# Funcionalidade da Lua
incluir_lua = st.sidebar.checkbox("Quero analisar a Lua", value=False)
mes_selecionado = None
if incluir_lua:
    mes_selecionado = st.sidebar.slider("Mês da Lua", min_value=1, max_value=12, value=1)

if grau_decimal is None:
    st.error("⚠️ Erro: Por favor, insira um valor numérico válido entre 0 e 30.")
    st.stop()

# Ajuste do texto do cabeçalho
p_texto = planeta_selecionado if planeta_selecionado != "Escolha um planeta" else "Planeta"
s_texto = signo_selecionado if signo_selecionado != "Escolha um signo" else "Signo"

st.markdown(f"""
    <div style='text-align: left;'>
        <h1 style='font-size: 2.5rem; margin-bottom: 0;'>🔭 Revolução Planetária {ano}</h1>
        <p style='font-size: 1.2rem; color: #555;'>Ponto Natal: <b>{p_texto} a {grau_input}° de {s_texto}</b></p>
    </div>
""", unsafe_allow_html=True)

# --- PROCESSAMENTO DE DADOS ---
@st.cache_data
def get_planetary_data(ano_ref, grau_ref_val, analisar_lua, mes_unico):
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
            
            pos_no_signo = long_abs % 30
            dist = abs(((pos_no_signo - grau_ref_val + 15) % 30) - 15)
            
            val = np.exp(-0.5 * (dist / 1.7)**2)
            row[p["nome"]] = val if dist <= 5.0 else 0 # Mudado para 0 para facilitar lógica da tabela
            row[f"{p['nome']}_long"] = long_abs
            row[f"{p['nome']}_status"] = "Retrógrado" if velocidade < 0 else "Direto"
            row[f"{p['nome']}_info"] = f"{get_signo(long_abs)}{mov}"
            
        all_data.append(row)
    
    return pd.DataFrame(all_data).infer_objects(copy=False), planetas_cfg

df, lista_planetas = get_planetary_data(ano, grau_decimal, incluir_lua, mes_selecionado)

# --- CONSTRUÇÃO DO GRÁFICO ---
fig = go.Figure()

for p in lista_planetas:
    # Filtra para o gráfico não exibir linhas em zero
    df_plot = df.copy()
    df_plot.loc[df_plot[p['nome']] == 0, p['nome']] = None

    fig.add_trace(go.Scatter(
        x=df_plot['date'], y=df_plot[p['nome']],
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
        serie_p = df[p['nome']].fillna(0)
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

# --- GERAÇÃO DA TABELA DE ASPECTOS ---
st.write("### 📅 Tabela de Trânsitos e Aspectos")

eventos = []
# Só gera a tabela se ambos os campos estiverem selecionados
if planeta_selecionado != "Escolha um planeta" and signo_selecionado != "Escolha um signo":
    # Cálculo da longitude absoluta natal do usuário para o cálculo do aspecto
    idx_signo_natal = SIGNOS.index(signo_selecionado)
    long_natal_absoluta = (idx_signo_natal * 30) + grau_decimal

    for p in lista_planetas:
        nome_p = p["nome"]
        serie_tabela = df[nome_p].values
        
        for i in range(1, len(serie_tabela) - 1):
            if serie_tabela[i] > 0.98 and serie_tabela[i] > serie_tabela[i-1] and serie_tabela[i] > serie_tabela[i+1]:
                
                # Encontrar Início
                idx_ini = i
                while idx_ini > 0 and serie_tabela[idx_ini] > 0.01:
                    idx_ini -= 1
                
                # Encontrar Término
                idx_fim = i
                while idx_fim < len(serie_tabela) - 1 and serie_tabela[idx_fim] > 0.01:
                    idx_fim += 1
                
                row_pico = df.iloc[i]
                long_trans = row_pico[f"{nome_p}_long"]
                
                eventos.append({
                    "Início": df.iloc[idx_ini]['date'].strftime('%d/%m/%Y %H:%M'),
                    "Pico": row_pico['date'].strftime('%d/%m/%Y %H:%M'),
                    "Término": df.iloc[idx_fim]['date'].strftime('%d/%m/%Y %H:%M'),
                    "Grau Natal": f"{grau_input}°",
                    "Planeta e Signo Natal": f"{planeta_selecionado} em {signo_selecionado}",
                    "Planeta e Signo em Trânsito": f"{nome_p.capitalize()} em {get_signo(long_trans)}",
                    "Status": row_pico[f"{nome_p}_status"],
                    "Aspecto": calcular_aspecto(long_trans, long_natal_absoluta)
                })

df_eventos = pd.DataFrame(eventos)
st.dataframe(df_eventos, use_container_width=True)

# --- DOWNLOADS ---
st.divider()
col1, col2, col3 = st.columns(3)

p_file = p_texto.replace(" ", "_")
s_file = s_texto.replace(" ", "_")
grau_limpo = str(grau_input).replace('.', '_')
nome_arquivo_base = f"revolucao_{p_file}_{s_file}_{ano}_grau_{grau_limpo}"

with col1:
    html_buffer = io.StringIO()
    fig.write_html(html_buffer, config={'scrollZoom': True})
    st.download_button("📥 Baixar Gráfico (HTML)", html_buffer.getvalue(), f"{nome_arquivo_base}.html", "text/html")

with col2:
    if not df_eventos.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_eventos.to_excel(writer, index=False)
        st.download_button("📂 Baixar Tabela (Excel)", output.getvalue(), f"tabela_{nome_arquivo_base}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.button("📂 Baixar Tabela (Excel)", disabled=True, help="Selecione os dados na lateral para habilitar")

with col3:
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button("📊 Baixar Dados Brutos (CSV)", csv_data, f"dados_{nome_arquivo_base}.csv", "text/csv")