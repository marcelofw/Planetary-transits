import streamlit as st
import swisseph as swe
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Revolução Planetária Profissional", layout="wide")

# Silencia avisos de downcasting para compatibilidade futura
pd.set_option('future.no_silent_downcasting', True)

# --- FUNÇÕES AUXILIARES ---
SIGNOS = ["Áries", "Touro", "Gêmeos", "Câncer", "Leão", "Virgem", 
          "Libra", "Escorpião", "Sagitário", "Capricórnio", "Aquário", "Peixes"]

def get_signo(longitude):
    return SIGNOS[int(longitude / 30) % 12]

def dms_to_dec(dms_str):
    try:
        if isinstance(dms_str, (int, float)): return float(dms_str)
        parts = str(dms_str).split('.')
        graus = float(parts[0])
        minutos = float(parts[1]) if len(parts) > 1 else 0
        return graus + (minutos / 60)
    except:
        return 0.0

def hex_to_rgba(hex_color, opacity):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({r}, {g}, {b}, {opacity})'

# --- INTERFACE STREAMLIT ---
st.title("🔭 Calculador de Revolução Planetária")
st.markdown("---")

with st.sidebar:
    st.header("Configurações")
    ano = st.number_input("Ano da Análise", min_value=1900, max_value=2100, value=2026)
    grau_input = st.text_input("Grau Alvo (ex: 27.0 ou 27.30)", value="27.0")
    
    st.info("O cálculo utiliza uma orbe de 5 graus com decaimento Gaussiano.")

# --- PROCESSAMENTO ---
def main():
    grau_decimal = dms_to_dec(grau_input)
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED

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

    # Geração dos dias julianos
    jd_start = swe.julday(ano, 1, 1)
    jd_end = swe.julday(ano + 1, 1, 1)
    steps = np.arange(jd_start, jd_end, 0.05)
    
    all_data = []
    
    # Barra de progresso para UX
    progress_bar = st.progress(0)
    
    for i, jd in enumerate(steps):
        y, m, d, h = swe.revjul(jd)
        dt = datetime(y, m, d, int(h), int((h%1)*60))
        row = {'date': dt}
        
        for p in planetas_monitorados:
            res, _ = swe.calc_ut(jd, p["id"], flags)
            long_abs, velocidade = res[0], res[3]
            
            # Identificação R/D
            mov = " (R)" if velocidade < 0 else " (D)"
            
            # Cálculo de distância circular
            pos_no_signo = long_abs % 30
            dist = abs(((pos_no_signo - grau_decimal + 15) % 30) - 15)
            
            # Intensidade (Sigma 1.7 para orbe de 5 graus)
            val = np.exp(-0.5 * (dist / 1.7)**2)
            
            row[p["nome"]] = val if dist <= 5.0 else None
            row[f"{p['nome']}_info"] = f"{get_signo(long_abs)}{mov}"
            
        all_data.append(row)
        if i % 100 == 0:
            progress_bar.progress(i / len(steps))

    progress_bar.empty()
    
    # DataFrame com tratamento de tipos
    df = pd.DataFrame(all_data).infer_objects(copy=False)

    # --- GRÁFICO ---
    fig = go.Figure()

    for p in planetas_monitorados:
        # Trace Principal
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

        # Trace das Datas (Sincronizado)
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
                textfont=dict(family="Arial Black", size=10, color="black"),
                marker=dict(symbol="triangle-down", color=p['cor'], size=8),
                legendgroup=p['nome'],
                showlegend=False,
                hoverinfo='skip'
            ))

    fig.update_layout(
        height=700,
        title=dict(text=f"Revolução Planetária {ano}: Grau {grau_input}", x=0.5),
        xaxis=dict(
            type='date', 
            tickformat='%d/%m\n%Y', 
            rangeslider=dict(visible=True, thickness=0.08),
            showspikes=True, spikemode='across', spikethickness=1, spikecolor="gray"
        ),
        yaxis=dict(title="Intensidade (Aproximação)", range=[0, 1.3], fixedrange=True),
        template='plotly_white',
        hovermode='x unified', 
        dragmode='pan',
        margin=dict(t=100)
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- DOWNLOAD ---
    grau_file = str(grau_input).replace('.', '_')
    file_name = f"revolucao_{ano}_grau_{grau_file}.html"
    
    # Exporta para HTML em memória para o botão de download
    html_bytes = fig.to_html(config={'scrollZoom': True}).encode('utf-8')
    
    st.download_button(
        label="💾 Baixar Gráfico Interativo (HTML)",
        data=html_bytes,
        file_name=file_name,
        mime='text/html'
    )

if __name__ == "__main__":
    main()