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
if 'resultados_data' not in st.session_state:
    st.session_state.resultados_data = None

# Configuração da Página
st.set_page_config(page_title="Revolução Planetária", layout="wide")
st.markdown("""
    <style>
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

SIMBOLOS_PLANETAS = {
    "Sol": "☉", "Lua": "☽", "Mercúrio": "☿", "Vênus": "♀", "Marte": "♂",
    "Júpiter": "♃", "Saturno": "♄", "Urano": "♅", "Netuno": "♆", "Plutão": "♇",
    "Sol": "☉", "Lua": "☽", "Mercúrio": "☿", "Vênus": "♀", "Marte": "♂",
    "Júpiter": "♃", "Saturno": "♄", "Urano": "♅", "Netuno": "♆", "Plutão": "♇"
}

SIMBOLOS_SIGNOS = {
    "Áries": "♈", "Touro": "♉", "Gêmeos": "♊", "Câncer": "♋", 
    "Leão": "♌", "Virgem": "♍", "Libra": "♎", "Escorpião": "♏", 
    "Sagitário": "♐", "Capricórnio": "♑", "Aquário": "♒", "Peixes": "♓"
}

# --- FUNÇÕES AUXILIARES ---
def get_signo(longitude):
    return SIGNOS[int(longitude / 30) % 12]

def dms_to_dec(dms_str):
    if dms_str is None or dms_str == "": return 0.0
    if isinstance(dms_str, (int, float)): return float(dms_str)
    
    try:
        s = str(dms_str).replace(',', '.').strip()
        if '.' in s:
            parts = s.split('.')
            graus = float(parts[0])
            minutos_raw = parts[1]
            
            # Correção do Pico: .2 vira 20, .02 continua 2
            if len(minutos_raw) == 1:
                minutos = float(minutos_raw) * 10
            else:
                minutos = float(minutos_raw)
            
            if minutos >= 60:
                return "ERRO_MINUTOS"
                
            val = graus + (minutos / 60.0)
        else:
            val = float(s)
            
        if 0 <= val <= 30:
            return val
        return "ERRO_GRAUS"
    except:
        return "ERRO_FORMATO"

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

def gerar_texto_relatorio(df, planeta_alvo_nome, long_natal_ref, id_planeta_transito):
    col_p = planeta_alvo_nome.upper()
    if col_p not in df.columns or long_natal_ref is None:
        return []

    # Função interna para calcular o signo real na data do pico
    def calcular_signo_real(data_pico):
        jd = swe.julday(data_pico.year, data_pico.month, data_pico.day, data_pico.hour + data_pico.minute/60.0)
        res, _ = swe.calc_ut(jd, id_planeta_transito, swe.FLG_SWIEPH)
        return SIGNOS[int(res[0] / 30) % 12]

    # Função para pegar APENAS o símbolo do aspecto
    def obter_simbolo_aspecto(s_transito, s_natal):
        try:
            idx_t = SIGNOS.index(s_transito)
            idx_n = SIGNOS.index(s_natal)
            distancia = abs(idx_t - idx_n)
            if distancia > 6: distancia = 12 - distancia
            
            # Pega o símbolo (índice 1 do valor do dicionário ASPECTOS)
            # Multiplicamos por 30 para bater com as chaves 0, 30, 60... do seu dicionário
            _, simbolo = ASPECTOS.get(distancia * 30, ("", ""))
            return simbolo
        except:
            return ""

    LIMIAR_INFLUENCIA = 0.01
    LIMIAR_FORTE = 0.841

    mask_inf = df[col_p] > LIMIAR_INFLUENCIA
    if not mask_inf.any(): return []

    df_copy = df.copy()
    df_copy['group_inf'] = (mask_inf != mask_inf.shift()).cumsum()
    curvas = df_copy[mask_inf].groupby('group_inf')

    relatorios_planeta = []
    signo_natal_nome = get_signo(long_natal_ref)

    for _, dados_curva in curvas:
        if len(dados_curva) < 2: continue
        
        data_ini = dados_curva['date'].min().strftime('%d/%m/%Y')
        data_fim = dados_curva['date'].max().strftime('%d/%m/%Y')
        
        ponto_max = dados_curva.loc[dados_curva[col_p].idxmax()]
        signo_transito = calcular_signo_real(ponto_max['date'])
        
        # Obtém apenas o símbolo (ex: ☍, ✶, □)
        simb_asp = obter_simbolo_aspecto(signo_transito, signo_natal_nome)
        
        mask_forte = dados_curva[col_p] >= LIMIAR_FORTE
        intervalos_fortes_texto = []
        
        if mask_forte.any():
            g_fortes = (mask_forte != mask_forte.shift()).cumsum()
            ilhas = dados_curva[mask_forte].groupby(g_fortes)
            
            for _, ilha in ilhas:
                f_ini = ilha['date'].min().strftime('%d/%m/%Y')
                f_fim = ilha['date'].max().strftime('%d/%m/%Y')
                
                # Lógica de Picos
                v = ilha[col_p].values
                d = ilha['date'].values
                picos_datas = []
                if len(v) <= 3:
                    picos_datas.append(pd.to_datetime(d[np.argmax(v)]))
                else:
                    for i in range(1, len(v) - 1):
                        if v[i] > v[i-1] and v[i] >= v[i+1]:
                            picos_datas.append(pd.to_datetime(d[i]))
                    if not picos_datas:
                        picos_datas.append(pd.to_datetime(d[np.argmax(v)]))

                str_picos = " e ".join([dt.strftime('%d/%m/%Y') for dt in sorted(list(set(picos_datas)))])
                intervalos_fortes_texto.append(
                    f"**Período de intensidade forte**: {f_ini} até {f_fim}  \n"
                    f"**Pico**: {str_picos}"
                )

        # Título formatado apenas com o símbolo (ex: JÚPITER em Câncer ✶)
        texto = (f"### {planeta_alvo_nome.title()} em {signo_transito} {simb_asp}  \n"
                 f"**Trânsito total**: {data_ini} até {data_fim}")
        
        if intervalos_fortes_texto:
            texto += "  \n" + "  \n".join(intervalos_fortes_texto)
        
        relatorios_planeta.append(texto)
        
    return relatorios_planeta

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
erro_detectado = False

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
    
    val_check = dms_to_dec(g)
    if val_check == "ERRO_MINUTOS":
        st.sidebar.error(f"⚠️ {alvo['p']}: Minutos devem ser < 60")
        erro_detectado = True
    elif val_check == "ERRO_GRAUS":
        st.sidebar.error(f"⚠️ {alvo['p']}: Deve ser entre 0 e 29")
        erro_detectado = True
    elif val_check == "ERRO_FORMATO":
        st.sidebar.error(f"⚠️ {alvo['p']}: Formato inválido")
        erro_detectado = True
    
    alvos_input.append({"planeta": alvo['p'], "signo": s, "grau": g})
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

# --- NOVO: GERADOR DE RELATÓRIO ABAIXO DO GRÁFICO ---
    st.divider()
    st.subheader("📋 Relatório de Trânsitos Longos")
    
    # Filtramos apenas os lentos da sua lista original planetas_monitorados
    lentos = [p for p in planetas_monitorados if p["nome"] in ["SOL", "JÚPITER", "SATURNO", "URANO", "NETUNO", "PLUTÃO"]]
    
    for alvo in alvos_input:
        idx_s_natal = SIGNOS.index(alvo["signo"])
        long_natal_abs = (idx_s_natal * 30) + dms_to_dec(alvo["grau"])
        
        with st.expander(f"Trânsitos sobre {alvo['planeta']} em {alvo['signo']}", expanded=False):
            df_alvo = resultados[alvo["planeta"]]
            encontrou = False
            
            for p_lento in lentos:
                # Passamos o df, o nome, a longitude natal e o ID do planeta lento
                relatorio = gerar_texto_relatorio(df_alvo, p_lento["nome"], long_natal_abs, p_lento["id"])
                if relatorio:
                    encontrou = True
                    for bloco in relatorio:
                        st.markdown(bloco)
                        st.markdown("---")
            
            if not encontrou:
                st.write("Nenhum trânsito de planeta lento para este ponto em 2026.")

    st.sidebar.download_button(
        label="📥 Baixar Gráfico Interativo (HTML)",
        data=buf.getvalue(),
        file_name=st.session_state.file_name,
        mime="text/html",
        use_container_width=True
    )   
else:
    st.info("Utilize o menu lateral para configurar os dados e clique em 'Gerar Gráficos'.")