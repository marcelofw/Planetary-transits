import streamlit as st
import swisseph as swe
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import io

if 'fig_gerada' not in st.session_state:
    st.session_state.fig_gerada = None
if 'file_name' not in st.session_state:
    st.session_state.file_name = ""

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

MESES = {
    1: "janeiro", 2: "fevereiro", 3: "marco", 4: "abril",
    5: "maio", 6: "junho", 7: "julho", 8: "agosto",
    9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro"
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

@st.cache_data(show_spinner=False)
def calcular_dados_efemerides(ano, mes, usar_lua, alvos, monitorados):
        jd_start = swe.julday(ano, mes if mes else 1, 1)
        jd_end = swe.julday(ano + (1 if not mes else 0), (mes + 1 if mes and mes < 12 else 1) if mes else 1, 1)
        steps = np.arange(jd_start, jd_end, 0.005 if usar_lua and mes else 0.05)
        flags = swe.FLG_SWIEPH | swe.FLG_SPEED

        dict_dfs = {}

        for alvo in alvos:
            grau_decimal = dms_to_dec(alvo["grau"])
            idx_signo_natal = SIGNOS.index(alvo["signo"])
            long_natal_absoluta = (idx_signo_natal * 30) + grau_decimal
            
            alvo_data = []
            for jd in steps:
                y, m, d, h = swe.revjul(jd)
                row = {'date': datetime(y, m, d, int(h), int((h%1)*60))}
                
                for p in monitorados:
                    res, _ = swe.calc_ut(jd, p["id"], flags)
                    long_abs, vel = res[0], res[3]
                    
                    pos_no_signo = long_abs % 30
                    # Cálculo de distância considerando a volta do zodíaco (orb de 5 graus)
                    graus_int = int(pos_no_signo)
                    minutos_int = int((pos_no_signo - graus_int) * 60)
                    dist = abs(((pos_no_signo - grau_decimal + 15) % 30) - 15)
                    
                    if dist <= 5.0:
                        # Cálculo da Força (Exponencial)
                        val = np.exp(-0.5 * (dist / 1.7)**2)
                        
                        # Info Detalhada
                        status = "(R)" if vel < 0 else "(D)"
                        simb = obter_simbolo_aspecto(long_abs, long_natal_absoluta)
                        int_txt = "Forte" if dist <= 1.0 else "Médio" if dist <= 2.5 else "Fraco"
                        
                        row[p["nome"]] = val
                        row[f"{p['nome']}_info"] = f"{get_signo(long_abs)} {status} {graus_int:02d}°{minutos_int:02d}' - {int_txt} {simb}"
                    else:
                        row[p["nome"]] = np.nan
                        row[f"{p['nome']}_info"] = ""
                
                alvo_data.append(row)

            dict_dfs[alvo["planeta"]] = pd.DataFrame(alvo_data)

        return dict_dfs

# --- INTERFACE LATERAL ---
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
ponto_inicial = [
    {"p": "Sol", "s": "Virgem", "g": "27.0"}, {"p": "Lua", "s": "Leão", "g": "6.2"},
    {"p": "Mercúrio", "s": "Libra", "g": "19.59"}, {"p": "Vênus", "s": "Libra", "g": "5.16"},
    {"p": "Marte", "s": "Escorpião", "g": "8.48"}, {"p": "Júpiter", "s": "Sagitário", "g": "8.57"},
    {"p": "Saturno", "s": "Peixes", "g": "20.53"}, {"p": "Urano", "s": "Capricórnio", "g": "26.37"},
    {"p": "Netuno", "s": "Capricórnio", "g": "22.50"}, {"p": "Plutão", "s": "Escorpião", "g": "28.19"}
]
st.sidebar.title("🪐 Configurações")
ano_analise = st.sidebar.number_input("Ano da Análise", 1900, 2100, 2026)
st.sidebar.subheader("Dados Natais", help="Insira os graus no formato Graus.Minutos (Ex: 27.30 para 27°30'). Use ponto como separador decimal.")

alvos_input = []
for i, alvo in enumerate(ponto_inicial):
    # Anotação acima do par de campos (estilizado em negrito/pequeno)
    st.sidebar.markdown(f"**{alvo['p']}**")
    
    # Colunas lado a lado
    col1, col2 = st.sidebar.columns([1.8, 1]) 
    
    with col1:
        s = st.selectbox(
            "Signo", 
            SIGNOS, 
            index=SIGNOS.index(alvo['s']), 
            key=f"s{i}", 
            label_visibility="collapsed" # Esconde o label interno para não repetir o título
        )
    
    with col2:
        g = st.text_input(
            "Grau", 
            value=alvo['g'], 
            key=f"g{i}", 
            label_visibility="collapsed" # Esconde o label interno
        )
    
    alvos_input.append({"planeta": alvo['p'], "signo": s, "grau": g})
    # Espaço opcional entre os blocos de planetas
    st.sidebar.markdown("<div style='margin-bottom: -10px;'></div>", unsafe_allow_html=True)

incluir_lua = st.sidebar.checkbox("Quero analisar a Lua", key="chk_analisar_lua")
mes_selecionado = st.sidebar.slider("Mês da Lua", 1, 12, 1) if incluir_lua else None
st.sidebar.divider()

# --- PROCESSAMENTO ---
if st.sidebar.button("Gerar Gráficos", help="Pode levar um tempo para processar.", use_container_width=True):
    with st.spinner("Sincronizando efemérides..."):
        
        lista_p = planetas_monitorados.copy()
        if incluir_lua:
            lista_p.insert(1, {"id": swe.MOON, "nome": "LUA", "cor": "#A6A6A6"})

        resultados = calcular_dados_efemerides(ano_analise, mes_selecionado, incluir_lua, alvos_input, lista_p)

        fig = make_subplots(
            rows=len(alvos_input), cols=1,
            subplot_titles=[f"<b>{a['planeta']} Natal em {a['signo']} {a['grau']}°</b>" for a in alvos_input],
            vertical_spacing=0.025,
            shared_xaxes=True
        )
        
        for idx, alvo in enumerate(alvos_input):
            df = resultados[alvo["planeta"]]

            for p in lista_p:
                if p['nome'] in df.columns:
                    # Gráfico de Área (Intensidade)
                    fig.add_trace(go.Scatter(
                        x=df['date'], y=df[p['nome']],
                        mode='lines', name=p['nome'],
                        legendgroup=p['nome'],
                        showlegend=(idx == 0), # Mostra legenda apenas no primeiro subplot
                        line=dict(color=p['cor'], width=2.5),
                        fill='tozeroy',
                        fillcolor=hex_to_rgba(p['cor'], 0.15),
                        customdata=df[f"{p['nome']}_info"],
                        hovertemplate="<b>%{customdata}</b><extra></extra>",
                        connectgaps=False
                    ), row=idx+1, col=1)

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
                            # textfont=dict(family="Arial", size=10, color="white"),
                            marker=dict(symbol="triangle-down", color=p['cor'], size=8),
                            legendgroup=p['nome'], showlegend=False, hoverinfo='skip'
                        ), row=idx+1, col=1)

            fig.update_yaxes(
                title_text=f"Intensidade de {alvo['planeta']}", 
                row=idx + 1, 
                col=1,
                range=[0, 1.3], 
                fixedrange=True
            )

        # alvo_principal = alvos_input[0]
        # p_nome = alvo_principal['planeta'].lower()
        # s_nome = alvo_principal['signo'].lower()
        # g_limpo = str(alvo_principal['grau']).replace('.','_')

        if incluir_lua:
            nome_mes = MESES.get(mes_selecionado).lower()
            file_name_grafico = f"revolucao_planetaria_{nome_mes}_{ano_analise}_todos_planetas_natais.html"
        else:
            file_name_grafico = f"revolucao_planetaria_{ano_analise}_todos_planetas_natais.html"

        fig.update_layout(
            height=520 * len(alvos_input), # Altura proporcional ao número de alvos
            title=dict(text=f"<b>Revolução Planetária {ano_analise}</b>", x=0.5, y=0.98, xanchor = "center", yanchor="top", font = dict(size = 24)),
            template='plotly_white',
            hovermode='x unified', dragmode='pan', margin=dict(t=240, b=50, l=50, r=50),
            legend=dict(orientation="h", yanchor="top", y=0.97, yref="container", xanchor="center", x=0.5)
        )

        fig.update_xaxes(type='date', tickformat='%d/%m\n%Y', hoverformat='%d/%m/%Y %H:%M', showticklabels=True, visible=True)
        #fig.update_yaxes(title='Intensidade', range=[0, 1.3], fixedrange=True)
        fig.update_annotations(patch=dict(font=dict(size=14), yshift=20))

        st.session_state.fig_gerada = fig
        st.session_state.file_name = file_name_grafico

if st.session_state.fig_gerada is not None:
    st.plotly_chart(st.session_state.fig_gerada, use_container_width=True, config={'scrollZoom': True})
    buf = io.StringIO()
    st.session_state.fig_gerada.write_html(buf, config={'scrollZoom': True}, include_plotlyjs=True)

    st.sidebar.download_button(
        label="📥 Baixar Gráfico Interativo (HTML)",
        data=buf.getvalue(),
        file_name=st.session_state.file_name,
        mime="text/html",
        use_container_width=True
    )   
else:
    st.info("Utilize o menu lateral para configurar os dados e clique em 'Gerar Gráficos'.")