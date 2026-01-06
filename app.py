import streamlit as st
import swisseph as swe
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import io
import re

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Revolução Planetária", layout="wide")

# Silencia avisos de downcasting
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
        
        # Validação de minutos (parte decimal)
        if len(parts) > 1:
            minutos_raw = parts[1]
            minutos = float(minutos_raw)
            
            # REGRA: Minutos não podem ser 60 ou mais
            if minutos >= 60:
                return "ERRO_MINUTOS"
        else:
            minutos = 0
            
        val = degrees + (minutos / 60)
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
        if abs(diff - angulo) <= 5:
            return nome
    return "Outro"

# --- INTERFACE LATERAL ---
st.sidebar.header("Configurações")
ano = st.sidebar.number_input("Ano da Análise", min_value=1900, max_value=2100, value=2026)
grau_input = st.sidebar.text_input("Grau Natal (0 a 30°)", value="27.0", help="Exemplo: 27.59 (27 graus e 59 minutos)")

planeta_selecionado = st.sidebar.selectbox("Planeta", options=["Escolha um planeta"] + LISTA_PLANETAS_UI, index=0)
signo_selecionado = st.sidebar.selectbox("Signo do Zodíaco", options=["Escolha um signo"] + SIGNOS, index=0)

grau_decimal = dms_to_dec(grau_input)
incluir_lua = st.sidebar.checkbox("Quero analisar a Lua", value=False)
mes_selecionado = st.sidebar.slider("Mês da Lua", 1, 12, 1) if incluir_lua else None

# Verificação da Regra de Minutos < 60
if grau_decimal == "ERRO_MINUTOS":
    st.error("⚠️ Erro: Os minutos (parte decimal) não podem ser iguais ou maiores que 60. Use de .00 a .59.")
    st.stop()
elif grau_decimal is None:
    st.error("⚠️ Erro: Insira um valor numérico válido entre 0 e 30.")
    st.stop()

p_texto = planeta_selecionado if planeta_selecionado != "Escolha um planeta" else "Planeta"
s_texto = signo_selecionado if signo_selecionado != "Escolha um signo" else "Signo"

st.markdown(f"""
    <div style='text-align: left;'>
        <h1 style='font-size: 2.5rem; margin-bottom: 0;'>🔭 Revolução Planetária {ano}</h1>
        <p style='font-size: 1.2rem; color: #555;'>Ponto Natal: <b>{p_texto} a {grau_input}° de {s_texto}</b></p>
    </div>
""", unsafe_allow_html=True)

# --- PROCESSAMENTO ---
@st.cache_data
def get_annual_movements(ano_ref):
    planetas_cfg = [{"id": i, "nome": n} for i, n in zip([swe.SUN, swe.MERCURY, swe.VENUS, swe.MARS, swe.JUPITER, swe.SATURN, swe.URANUS, swe.NEPTUNE, swe.PLUTO], ["SOL", "MERCÚRIO", "VÊNUS", "MARTE", "JÚPITER", "SATURNO", "URANO", "NETUNO", "PLUTÃO"])]
    jd_start = swe.julday(ano_ref, 1, 1)
    jd_end = swe.julday(ano_ref + 1, 1, 1)
    steps = np.arange(jd_start, jd_end, 0.5)
    movs = []
    for p in planetas_cfg:
        status_atual, data_inicio = None, None
        for jd in steps:
            res, _ = swe.calc_ut(jd, p["id"], swe.FLG_SWIEPH | swe.FLG_SPEED)
            status_ponto = "Retrógrado" if res[3] < 0 else "Direto"
            if status_atual is None:
                status_atual = status_ponto
                y, m, d, _ = swe.revjul(jd)
                data_inicio = datetime(y, m, d)
            elif status_ponto != status_atual:
                y, m, d, _ = swe.revjul(jd)
                movs.append({"Planeta": p["nome"].capitalize(), "Início": data_inicio.strftime('%d/%m/%Y'), "Término": datetime(y, m, d).strftime('%d/%m/%Y'), "Trânsito": status_atual})
                status_atual, data_inicio = status_ponto, datetime(y, m, d)
        movs.append({"Planeta": p["nome"].capitalize(), "Início": data_inicio.strftime('%d/%m/%Y'), "Término": f"31/12/{ano_ref}", "Trânsito": status_atual})
    return pd.DataFrame(movs)

@st.cache_data
def get_planetary_data(ano_ref, grau_ref_val, analisar_lua, mes_unico):
    planetas_cfg = [
        {"id": swe.SUN, "nome": "SOL", "cor": "#FFF12E"}, {"id": swe.MERCURY, "nome": "MERCÚRIO", "cor": "#F3A384"},
        {"id": swe.VENUS, "nome": "VÊNUS", "cor": "#0A8F11"}, {"id": swe.MARS, "nome": "MARTE", "cor": "#F10808"},
        {"id": swe.JUPITER, "nome": "JÚPITER", "cor": "#1746C9"}, {"id": swe.SATURN, "nome": "SATURNO", "cor": "#381094"},
        {"id": swe.URANUS, "nome": "URANO", "cor": "#FF00FF"}, {"id": swe.NEPTUNE, "nome": "NETUNO", "cor": "#1EFF00"},
        {"id": swe.PLUTO, "nome": "PLUTÃO", "cor": "#14F1F1"}
    ]
    if analisar_lua: planetas_cfg.insert(1, {"id": swe.MOON, "nome": "LUA", "cor": "#A6A6A6"})
    jd_start = swe.julday(ano_ref, mes_unico if mes_unico else 1, 1)
    jd_end = swe.julday(ano_ref + (1 if not mes_unico else 0), (mes_unico + 1 if mes_unico and mes_unico < 12 else 1) if mes_unico else 1, 1)
    steps = np.arange(jd_start, jd_end, 0.005 if analisar_lua and mes_unico else 0.05)
    all_data = []
    for jd in steps:
        y, m, d, h = swe.revjul(jd)
        dt = datetime(y, m, d, int(h), int((h%1)*60))
        row = {'date': dt}
        for p in planetas_cfg:
            res, _ = swe.calc_ut(jd, p["id"], swe.FLG_SWIEPH | swe.FLG_SPEED)
            pos = res[0] % 30
            dist = abs(((pos - grau_ref_val + 15) % 30) - 15)
            row[p["nome"]] = np.exp(-0.5 * (dist / 1.7)**2) if dist <= 5.0 else 0
            row[f"{p['nome']}_long"] = res[0]
            row[f"{p['nome']}_status"] = "Retrógrado" if res[3] < 0 else "Direto"
            row[f"{p['nome']}_info"] = f"{get_signo(res[0])} {'(R)' if res[3]<0 else '(D)'} {int(pos):02d}°{int((pos%1)*60):02d}' - {'Forte' if dist <= 1.0 else 'Médio' if dist <= 2.5 else 'Fraco'}"
        all_data.append(row)
    return pd.DataFrame(all_data).infer_objects(copy=False), planetas_cfg

df_mov_anual = get_annual_movements(ano)
df, lista_planetas = get_planetary_data(ano, grau_decimal, incluir_lua, mes_selecionado)
grau_limpo_file = str(grau_input).replace('.', '_')

# --- GRÁFICO ---
fig = go.Figure()
for p in lista_planetas:
    df_p = df.copy()
    df_p.loc[df_p[p['nome']] == 0, p['nome']] = None
    fig.add_trace(go.Scatter(x=df_p['date'], y=df_p[p['nome']], name=p['nome'], mode='lines', line=dict(color=p['cor'], width=2.5),
                             fill='tozeroy', fillcolor=hex_to_rgba(p['cor'], 0.15), customdata=df[f"{p['nome']}_info"],
                             hovertemplate="<b>%{customdata}</b><extra></extra>", connectgaps=False))
    
    serie = df[p['nome']].fillna(0)
    picos = df[(serie > 0.98) & (serie > serie.shift(1)) & (serie > serie.shift(-1))]
    if not picos.empty:
        fig.add_trace(go.Scatter(x=picos['date'], y=picos[p['nome']]+0.04, mode='markers+text', text=picos['date'].dt.strftime('%d/%m'),
                                 textposition="top center", marker=dict(symbol="triangle-down", color=p['cor'], size=8), showlegend=False, hoverinfo='skip'))

fig.update_layout(height=700, xaxis=dict(rangeslider=dict(visible=True, thickness=0.08), type='date', tickformat='%d/%m\n%Y', hoverformat='%d/%m/%Y %H:%M'),
                  yaxis=dict(title='Intensidade', range=[0, 1.3], fixedrange=True), template='plotly_white', hovermode='x unified', dragmode='pan')
st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

# --- LÓGICA DA TABELA DE ASPECTOS (IGUAL AO SCRIPT PYTHON) ---
eventos_aspectos = []
if planeta_selecionado != "Escolha um planeta" and signo_selecionado != "Escolha um signo":
    idx_signo_natal = SIGNOS.index(signo_selecionado)
    long_natal_absoluta = (idx_signo_natal * 30) + grau_decimal
    
    for p in lista_planetas:
        nome_p = p["nome"]
        serie_tabela = df[nome_p].fillna(0).values
        for i in range(1, len(serie_tabela) - 1):
            if serie_tabela[i] > 0.98 and serie_tabela[i] > serie_tabela[i-1] and serie_tabela[i] > serie_tabela[i+1]:
                idx_ini = i
                while idx_ini > 0 and serie_tabela[idx_ini] > 0.01: idx_ini -= 1
                idx_fim = i
                while idx_fim < len(serie_tabela) - 1 and serie_tabela[idx_fim] > 0.01: idx_fim += 1
                
                row_pico = df.iloc[i]
                long_trans = row_pico[f"{nome_p}_long"]
                
                eventos_aspectos.append({
                    "Data e Hora Início": df.iloc[idx_ini]['date'].strftime('%d/%m/%Y %H:%M'),
                    "Data e Hora Pico": row_pico['date'].strftime('%d/%m/%Y %H:%M'),
                    "Data e Hora Término": df.iloc[idx_fim]['date'].strftime('%d/%m/%Y %H:%M'),
                    "Grau Natal": f"{grau_input}°",
                    "Planeta e Signo Natal": f"{planeta_selecionado} em {signo_selecionado}",
                    "Planeta e Signo em Trânsito": f"{nome_p.capitalize()} em {get_signo(long_trans)}",
                    "Trânsito": row_pico[f"{nome_p}_status"],
                    "Aspecto": calcular_aspecto(long_trans, long_natal_absoluta)
                })

# --- EXIBIÇÃO DAS TABELAS CENTRALIZADAS ---
st.markdown("<h3 style='text-align: center;'>📅 Tabela de Trânsitos e Aspectos (Ponto Natal)</h3>", unsafe_allow_html=True)
col_a1, col_a2, col_a3 = st.columns([0.05, 0.9, 0.05])
with col_a2:
    st.dataframe(pd.DataFrame(eventos_aspectos), use_container_width=True, hide_index=True)

st.markdown(f"<h3 style='text-align: center;'>🔄 Movimento Anual dos Planetas em {ano}</h3>", unsafe_allow_html=True)
col_m1, col_m2, col_m3 = st.columns([1, 2, 1])
with col_m2:
    st.dataframe(df_mov_anual, use_container_width=True, hide_index=True)

# --- DOWNLOADS ---
st.divider()
c1, c2, c3 = st.columns(3)
with c1:
    buf = io.StringIO()
    fig.write_html(buf, config={'scrollZoom': True})
    st.download_button("📥 Baixar Gráfico (HTML)", buf.getvalue(), f"revolucao_{ano}_grau_{grau_limpo_file}.html", "text/html")
with c2:
    if eventos_aspectos:
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as w: pd.DataFrame(eventos_aspectos).to_excel(w, index=False)
        st.download_button("📂 Baixar Tabela Aspectos (Excel)", out.getvalue(), f"tabela_transitos_{ano}_grau_{grau_limpo_file}.xlsx")
    else:
        st.button("📂 Baixar Tabela Aspectos (Excel)", disabled=True)
with c3:
    out_m = io.BytesIO()
    with pd.ExcelWriter(out_m, engine='openpyxl') as w: df_mov_anual.to_excel(w, index=False)
    st.download_button("🔄 Baixar Movimento Anual (Excel)", out_m.getvalue(), f"movimento_planetas_{ano}.xlsx")