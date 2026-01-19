import streamlit as st
import swisseph as swe
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta
from datetime import date
import io
import re
import urllib.parse
import base64
import math
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Revolução Planetária", layout="wide")
st.markdown("""
    <style>
        /* Aumenta as fontes dos campos de IA */
        .stDateInput label p, .stTextInput label p {
            font-size: 1.1rem !important;
            font-weight: bold !important;
        }
        .stDateInput div div input, .stTextInput div div input {
            font-size: 1.1rem !important;
            height: 45px !important;
        }
        /* Remove o link de corrente/âncora dos títulos */
        button[data-testid="stHeaderActionElements"], 
        .aria-hidden, 
        [data-testid="stMarkdown"] svg {
            display: none !important;
        }
    </style>
""", unsafe_allow_html=True)

# Silencia avisos de downcasting
pd.set_option('future.no_silent_downcasting', True)

# --- CONSTANTES E FUNÇÕES AUXILIARES ---
SIGNOS = ["Áries", "Touro", "Gêmeos", "Câncer", "Leão", "Virgem", 
          "Libra", "Escorpião", "Sagitário", "Capricórnio", "Aquário", "Peixes"]

LISTA_PLANETAS_UI = ["Sol", "Lua", "Mercúrio", "Vênus", "Marte", "Júpiter", "Saturno", "Urano", "Netuno", "Plutão"]

# Dicionário atualizado para incluir os símbolos
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
    "MARTE": "♂", "JÚPITER": "♃", "SATURNO": "♄", 
    "URANO": "♅", "NETUNO": "♆", "PLUTÃO": "♇"
}

MESES = {1:'Janeiro', 2:'Fevereiro', 3:'Março', 4:'Abril', 5:'Maio', 6:'Junho', 7:'Julho',
         8:'Agosto', 9:'Setembro', 10:'Outubro', 11:'Novembro', 12:'Dezembro'}

def converter_svg_para_base64(caminho_arquivo):
    """Converte um arquivo SVG local em uma string Base64 para exibição universal."""
    if not os.path.exists(caminho_arquivo):
        return None
    with open(caminho_arquivo, "rb") as f:
        svg_bytes = f.read()
        encoded = base64.b64encode(svg_bytes).decode('utf-8')
        return f"data:image/svg+xml;base64,{encoded}"

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
    for angulo, (nome, simbolo) in ASPECTOS.items():
        if abs(diff - angulo) <= 5:
            return nome
    return "Outro"

def obter_simbolo_aspecto(long1, long2):
    diff = abs(long1 - long2) % 360
    if diff > 180: diff = 360 - diff
    for angulo, (nome, simbolo) in ASPECTOS.items():
        if abs(diff - angulo) <= 5:
            return simbolo
    return ""

def gerar_texto_relatorio(df, planeta_alvo_nome):
    """Analisa o dataframe para encontrar múltiplos períodos de influência e força de forma segmentada."""
    col_p = planeta_alvo_nome.upper()
    if col_p not in df.columns:
        return []

    # 1. Identificar onde há qualquer influência (Curva base)
    mask = df[col_p] > 0.01
    
    # 2. Criar grupos para cada curva isolada (evita unir datas de picos diferentes)
    df_copy = df.copy()
    df_copy['group'] = (mask != mask.shift()).cumsum()
    curvas = df_copy[mask].groupby('group')

    relatorios_planeta = []

    for _, dados_curva in curvas:
        if len(dados_curva) < 2: continue
        
        # Datas da curva total (Início e Término onde sai do 0)
        data_ini = dados_curva['date'].min().strftime('%d/%m/%Y')
        data_fim = dados_curva['date'].max().strftime('%d/%m/%Y')
        
        # Pega o signo no pico da intensidade desta curva específica
        ponto_max = dados_curva.loc[dados_curva[col_p].idxmax()]
        signo_transito = get_signo(ponto_max[f"{col_p}_long"])
        status_no_pico = ponto_max[f"{col_p}_status"]
        
        # 3. Análise de Aspecto Forte APENAS dentro desta fatia 'dados_curva'
        # Usamos 0.88 para representar a transição para forte (aprox. 1° de orbe)
        dados_fortes = dados_curva[dados_curva[col_p] >= 0.88]
        
        texto = f"**{planeta_alvo_nome} em {signo_transito} ({status_no_pico})**: influência de {data_ini} até {data_fim}"
        
        if not dados_fortes.empty:
            # Agora as datas são limitadas ao intervalo desta curva específica
            forte_ini = dados_fortes['date'].min().strftime('%d/%m/%Y')
            forte_fim = dados_fortes['date'].max().strftime('%d/%m/%Y')
            texto += f", fazendo aspecto forte entre {forte_ini} até {forte_fim}."
        else:
            texto += "."
            
        relatorios_planeta.append(texto)
        
    return relatorios_planeta

# --- INTERFACE LATERAL ---
st.sidebar.header("🪐 Configurações")
ano = st.sidebar.number_input("Ano da Análise", min_value=1900, max_value=2100, value=2026)
grau_input = st.sidebar.text_input("Grau Natal (0 a 30°)", value="27.0", help="Exemplo: 27.59 (27 graus e 59 minutos)")

planeta_selecionado = st.sidebar.selectbox("Planeta", options=["Escolha um planeta"] + LISTA_PLANETAS_UI, index=1)
signo_selecionado = st.sidebar.selectbox("Signo do Zodíaco", options=["Escolha um signo"] + SIGNOS, index=6)

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

# Cálculo da longitude natal absoluta para uso na função de símbolos
long_natal_absoluta_calc = 0
if planeta_selecionado != "Escolha um planeta" and signo_selecionado != "Escolha um signo":
    idx_s = SIGNOS.index(signo_selecionado)
    long_natal_absoluta_calc = (idx_s * 30) + grau_decimal

p_texto = planeta_selecionado if planeta_selecionado != "Escolha um planeta" else "Planeta"
s_texto = signo_selecionado if signo_selecionado != "Escolha um signo" else "Signo"

st.markdown(f"""
    <div style='text-align: left;'>
        <h1 style='font-size: 2.5rem; margin-bottom: 0;'>🔭 Revolução Planetária {ano}</h1>
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
def get_planetary_data(ano_ref, grau_ref_val, analisar_lua, mes_unico, long_natal_ref):
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
            
            simbolo = obter_simbolo_aspecto(res[0], long_natal_ref) if long_natal_ref > 0 else ""
            simbolo_html = f"<span style='font-size: 16px; line-height: 0; vertical-align: baseline;'><b>{simbolo}</b></span>" if simbolo else ""
            
            row[p["nome"]] = np.exp(-0.5 * (dist / 1.7)**2) if dist <= 5.0 else 0
            row[f"{p['nome']}_long"] = res[0]
            row[f"{p['nome']}_status"] = "Retrógrado" if res[3] < 0 else "Direto"
            row[f"{p['nome']}_info"] = f"{get_signo(res[0])} {'(R)' if res[3]<0 else '(D)'} {int(pos):02d}°{int((pos%1)*60):02d}' - {'Forte' if dist <= 1.0 else 'Médio' if dist <= 2.5 else 'Fraco'} {simbolo_html}"
        all_data.append(row)
    return pd.DataFrame(all_data).infer_objects(copy=False), planetas_cfg

df_mov_anual = get_annual_movements(ano)
df, lista_planetas = get_planetary_data(ano, grau_decimal, incluir_lua, mes_selecionado, long_natal_absoluta_calc)
grau_limpo_file = str(grau_input).replace('.', '_')

if incluir_lua:
    mes_nome = MESES.get(mes_selecionado, "periodo").lower()
    file_name_grafico = f"revolucao_planetaria_{mes_nome}_{ano}_{planeta_selecionado}_em_{signo_selecionado}_grau_{grau_limpo_file}.html"
    file_name_tabela = f"aspectos_{mes_nome}_{ano}_{planeta_selecionado}_em_{signo_selecionado}_grau_{grau_limpo_file}.xlsx"
else:
    file_name_grafico = f"revolucao_planetaria_{ano}_{planeta_selecionado}_em_{signo_selecionado}_grau_{grau_limpo_file}.html"
    file_name_tabela = f"aspectos_{ano}_{planeta_selecionado}_em_{signo_selecionado}_grau_{grau_limpo_file}.xlsx"

@st.fragment
def secao_previsao_ia(ano, planeta_selecionado, signo_selecionado, grau_input, long_natal_absoluta_calc):
        # --- SEÇÃO DE CONSULTA IA CENTRALIZADA (ABAIXO DO GRÁFICO) ---
    hoje = datetime.now()
    hora_agora = (datetime.now() - timedelta(hours=3)).strftime("%H:%M")

    st.divider()
    col_esq, col_central, col_dir = st.columns([1, 1.5, 1])

    with col_central:
        st.markdown("<h2 style='text-align: center;'>🤖 Consulta Astrológica</h2>", unsafe_allow_html=True)
        
        sub_col1, sub_col2 = st.columns(2)
        
        with sub_col1:
            data_consulta = st.date_input(
                "Escolha a data", 
                value=date(hoje.year, hoje.month, hoje.day),
                min_value=date(1900, 1, 1),
                max_value=date(2100, 12, 31),
                key="ia_data_key" 
            )
        
        with sub_col2:
            hora_input = st.text_input("Escolha a hora (HH:MM)", placeholder='12:00', key="ia_hora_key")
        
        btn_gerar = st.button("Obter informação sobre os trânsitos", use_container_width=True)

    if btn_gerar:
        # --- VALIDAÇÃO DE SELEÇÃO ---
        if planeta_selecionado == "Escolha um planeta" or signo_selecionado == "Escolha um signo":
            st.error("⚠️ Erro: Selecione o Planeta e o Signo na barra lateral antes de gerar a previsão.")
        else:
            hora_valida = "12:00"
            if hora_input.strip():
                if re.match(r"^([0-9]|0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$", hora_input.strip()):
                    hora_valida = hora_input.strip()
                else:
                    st.warning("Formato de hora inválido. Usando 12:00 por padrão.")

            h_str, m_str = hora_valida.split(":")
            hora_decimal = int(h_str) + (int(m_str) / 60.0)
            
            jd_ia = swe.julday(data_consulta.year, data_consulta.month, data_consulta.day, hora_decimal)
            
            ativos_ia = []
            planetas_ia = [
                {"id": swe.SUN, "nome": "Sol"}, {"id": swe.MOON, "nome": "Lua"},
                {"id": swe.MERCURY, "nome": "Mercúrio"}, {"id": swe.VENUS, "nome": "Vênus"},
                {"id": swe.MARS, "nome": "Marte"}, {"id": swe.JUPITER, "nome": "Júpiter"},
                {"id": swe.SATURN, "nome": "Saturno"}, {"id": swe.URANUS, "nome": "Urano"},
                {"id": swe.NEPTUNE, "nome": "Netuno"}, {"id": swe.PLUTO, "nome": "Plutão"}
            ]

            for p in planetas_ia:
                res, _ = swe.calc_ut(jd_ia, p["id"], swe.FLG_SWIEPH | swe.FLG_SPEED)
                long_transito = res[0]
                pos_no_signo = long_transito % 30
                
                diff = abs(long_transito - long_natal_absoluta_calc) % 360
                if diff > 180: diff = 360 - diff
                
                aspecto_nome = "Nenhum"
                menor_orbe = 999
                
                for angulo, (nome, simbolo) in ASPECTOS.items():
                    orbe_atual = abs(diff - angulo)
                    if orbe_atual <= 5.0:
                        aspecto_nome = nome
                        menor_orbe = orbe_atual
                        break
                
                if aspecto_nome != "Nenhum":
                    status = "Retrógrado" if res[3] < 0 else "Direto"
                    forca = "Forte" if menor_orbe <= 1.0 else "Médio" if menor_orbe <= 2.5 else "Fraco"
                    ativos_ia.append(f"{p['nome']} em {get_signo(long_transito)} ({status}) {int(pos_no_signo):02d}°{int((pos_no_signo%1)*60):02d}' fazendo {aspecto_nome} - {forca}")

            with col_central:
                if ativos_ia:
                    data_hora_str = f"{data_consulta.strftime('%d/%m/%Y')} às {hora_valida}"
                    prompt_final = f"""Data e hora: {data_hora_str}.\nTrânsitos ativos para {planeta_selecionado} a {grau_input}° de {signo_selecionado}: \n{'; \n'.join(ativos_ia)}."""
                    st.write("### 📝 Sua consulta está pronta!")
                    st.text_area("Resultado dos trânsitos:", value=prompt_final, height=200)
                else:
                    st.info("Não há aspectos significativos para este momento.")

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

fig.update_layout(title=dict(text=f'<b>{p_texto} Natal a {grau_input}° de {s_texto}</b>', x=0.5, xanchor = 'center', font = dict(size = 28)),
                  height=700,
                  xaxis=dict(rangeslider=dict(visible=True, thickness=0.08), type='date', tickformat='%d/%m\n%Y', hoverformat='%d/%m/%Y %H:%M'),
                  yaxis=dict(title='Intensidade', range=[0, 1.3], fixedrange=True), template='plotly_white', hovermode='x unified', dragmode='pan')
st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

# --- SEÇÃO DE RELATÓRIO (LENTOS) ---
st.divider()
col_rel1, col_rel2, col_rel3 = st.columns([1, 2, 1])

with col_rel2:
    st.markdown("<h2 style='text-align: center;'>📋 Relatório de Impacto (Planetas Lentos)</h2>", unsafe_allow_html=True)
    if st.button("Gerar Relatório de Ciclos Longos", use_container_width=True):
        if planeta_selecionado == "Escolha um planeta" or signo_selecionado == "Escolha um signo":
            st.error("⚠️ Selecione os dados natais na barra lateral.")
        else:
            lentos = ["Júpiter", "Saturno", "Urano", "Netuno", "Plutão"]
            encontrou_algum = False
            
            with st.expander("Visualizar Detalhes dos Ciclos", expanded=True):
                for p_lento in lentos:
                    lista_periodos = gerar_texto_relatorio(df, p_lento)
                    if lista_periodos:
                        encontrou_algum = True
                        for periodo_texto in lista_periodos:
                            st.markdown(f"✅ {periodo_texto}")
                
                if not encontrou_algum:
                    st.warning("Não foram encontrados trânsitos de planetas lentos para este ponto natal em {ano}.")

# Chamada da função da seção de IA
secao_previsao_ia(ano, planeta_selecionado, signo_selecionado, grau_input, long_natal_absoluta_calc)

# --- LÓGICA DA TABELA DE ASPECTOS ---
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
                    "Início": df.iloc[idx_ini]['date'].strftime('%d/%m/%Y %H:%M'),
                    "Pico": row_pico['date'].strftime('%d/%m/%Y %H:%M'),
                    "Término": df.iloc[idx_fim]['date'].strftime('%d/%m/%Y %H:%M'),
                    "Planeta e Signo Natal": f"{planeta_selecionado} em {signo_selecionado}",
                    "Planeta e Signo em Trânsito": f"{nome_p.capitalize()} em {get_signo(long_trans)}",
                    "Trânsito": row_pico[f"{nome_p}_status"],
                    "Aspecto": calcular_aspecto(long_trans, long_natal_absoluta)
                })

# --- EXIBIÇÃO DAS TABELAS ---
st.divider()
st.markdown("<h3 style='text-align: center;'>📅 Tabela de Trânsitos e Aspectos</h3>", unsafe_allow_html=True)
col_a1, col_a2, col_a3 = st.columns([0.05, 0.9, 0.05])
with col_a2:
    if eventos_aspectos:
        st.dataframe(pd.DataFrame(eventos_aspectos), use_container_width=True, hide_index=True, height=(len(eventos_aspectos) + 1) * 35 + 3)

st.markdown(f"<h3 style='text-align: center;'>🔄 Movimento Anual dos Planetas em {ano}</h3>", unsafe_allow_html=True)
col_m1, col_m2, col_m3 = st.columns([1, 2, 1])
with col_m2:
    st.dataframe(df_mov_anual, use_container_width=True, hide_index=True, height=(len(df_mov_anual) + 1) * 35 + 3)

# --- DOWNLOADS ---
# st.divider()
# c1, c2, c3 = st.columns(3)
# with c1:
#     buf = io.StringIO()
#     fig.write_html(buf, config={'scrollZoom': True}, include_plotlyjs=True)
#     st.download_button("📥 Baixar Gráfico Interativo (HTML)", data=buf.getvalue(), file_name=file_name_grafico, mime="text/html")
# with c2:
#     if eventos_aspectos:
#         out = io.BytesIO()
#         with pd.ExcelWriter(out, engine='openpyxl') as w: pd.DataFrame(eventos_aspectos).to_excel(w, index=False)
#         st.download_button("📂 Baixar Tabela Aspectos (Excel)", out.getvalue(), file_name=file_name_tabela)
#     else:
#         st.button("📂 Baixar Tabela Aspectos (Excel)", disabled=True)
# with c3:
#     out_m = io.BytesIO()
#     with pd.ExcelWriter(out_m, engine='openpyxl') as w: df_mov_anual.to_excel(w, index=False)
#     st.download_button("🔄 Baixar Movimento Anual (Excel)", out_m.getvalue(), f"movimento_planetas_{ano}.xlsx")

st.divider()
buf = io.StringIO()
fig.write_html(buf, config={'scrollZoom': True}, include_plotlyjs=True)
st.sidebar.download_button("📥 Baixar Gráfico Interativo (HTML)", data=buf.getvalue(), file_name=file_name_grafico, mime="text/html")

if eventos_aspectos:
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as w: pd.DataFrame(eventos_aspectos).to_excel(w, index=False)
    st.sidebar.download_button("📂 Baixar Tabela Aspectos (Excel)", out.getvalue(), file_name=file_name_tabela)
else:
    st.button("📂 Baixar Tabela Aspectos (Excel)", disabled=True)

out_m = io.BytesIO()
with pd.ExcelWriter(out_m, engine='openpyxl') as w: df_mov_anual.to_excel(w, index=False)
st.sidebar.download_button("🔄 Baixar Movimento Anual (Excel)", out_m.getvalue(), f"movimento_planetas_{ano}.xlsx")