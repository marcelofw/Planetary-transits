import swisseph as swe
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# Silencia o aviso de downcasting do Pandas
pd.set_option('future.no_silent_downcasting', True)

# --- CONFIGURAÇÕES E FUNÇÕES AUXILIARES ---
SIGNOS = ["Áries", "Touro", "Gêmeos", "Câncer", "Leão", "Virgem", 
          "Libra", "Escorpião", "Sagitário", "Capricórnio", "Aquário", "Peixes"]

def get_signo(longitude):
    return SIGNOS[int(longitude / 30) % 12]

def dms_to_dec(dms_str):
    if isinstance(dms_str, (int, float)): return float(dms_str)
    parts = str(dms_str).split('.')
    return float(parts[0]) + (float(parts[1])/60 if len(parts) > 1 else 0)

def hex_to_rgba(hex_color, opacity):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({r}, {g}, {b}, {opacity})'

def generate_degree_transit_chart():
    # ==========================================
    # 1. CONFIGURAÇÃO
    # ==========================================
    ano = 2026
    grau_alvo_natal = "27.0"  
    
    grau_decimal = dms_to_dec(grau_alvo_natal)
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

    # ==========================================
    # 2. PROCESSAMENTO DE DADOS
    # ==========================================
    jd_start = swe.julday(ano, 1, 1)
    jd_end = swe.julday(ano + 1, 1, 1)
    steps = np.arange(jd_start, jd_end, 0.05)
    
    all_data = []
    for jd in steps:
        y, m, d, h = swe.revjul(jd)
        dt = datetime(y, m, d, int(h), int((h%1)*60))
        row = {'date': dt}
        
        for p in planetas_monitorados:
            res, _ = swe.calc_ut(jd, p["id"], flags)
            long_abs, velocidade = res[0], res[3]
            mov = " (R)" if velocidade < 0 else " (D)"
            dist = abs(((long_abs % 30 - grau_decimal + 15) % 30) - 15)
            val = np.exp(-0.5 * (dist / 1.7)**2)
            row[p["nome"]] = val if dist <= 5.0 else None
            row[f"{p['nome']}_info"] = f"{get_signo(long_abs)}{mov}"
            
        all_data.append(row)

    df = pd.DataFrame(all_data).infer_objects(copy=False)

    # ==========================================
    # 3. CONSTRUÇÃO DO GRÁFICO
    # ==========================================
    fig = go.Figure()

    for p in planetas_monitorados:
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

    # ==========================================
    # 4. LAYOUT E EXPORTAÇÃO
    # ==========================================
    fig.update_layout(
        title=dict(text=f'Revolucao Planetaria {ano}: Grau {grau_alvo_natal}', x=0.5),
        xaxis=dict(type='date', tickformat='%d/%m\n%Y', rangeslider=dict(visible=True, thickness=0.08)),
        yaxis=dict(title='Intensidade', range=[0, 1.25], fixedrange=True),
        template='plotly_white',
        hovermode='x unified', 
        dragmode='pan',
        margin=dict(t=100)
    )

    # Nome do arquivo dinâmico
    grau_para_nome = str(grau_alvo_natal).replace('.', '_')
    file_name = f"revolucao_{ano}_grau_{grau_para_nome}.html"
    
    fig.write_html(file_name, config={'scrollZoom': True})
    
    # REMOVIDO O EMOJI DO PRINT PARA EVITAR UNICODEENCODEERROR
    print(f"Sucesso! Grafico gerado: {file_name}")

if __name__ == "__main__":
    generate_degree_transit_chart()