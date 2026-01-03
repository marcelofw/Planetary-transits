import swisseph as swe
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

def hex_to_rgba(hex_color, opacity):
    """Converte Hex #RRGGBB para rgba(r, g, b, a) corretamente."""
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({r}, {g}, {b}, {opacity})'

def generate_natal_aspects_chart():
    # 1. Configurações de Dados
    jd_start = swe.julday(2026, 1, 1)                                            #ano inicial
    jd_end = swe.julday(2027, 1, 1)                                              #ano final
    steps = np.arange(jd_start, jd_end, 0.04)
    
    # Pontos do Mapa Natal
    natal_points = [
        {"nome": "Aspecto 27°", "grau": 27.0, "cor": "#FFF12E"},                #SOL
        {"nome": "Aspecto 6.20°", "grau": 6.333, "cor": "#C37DEB"},             #LUA
        {"nome": "Aspecto 19.59°", "grau": 19.9833, "cor": "#F3A384"},          #MERCÚRIO
        {"nome": "Aspecto 5.16°", "grau": 5.267, "cor": "#0A8F11"},             #VÊNUS        
        {"nome": "Aspecto 8.48°", "grau": 8.8, "cor": "#F10808"},               #MARTE
        {"nome": "Aspecto 8.57°", "grau": 8.95, "cor": "#1746C9"}               #JÚPITER
    ]
    
    all_data = []

    # 2. Processamento das Efemérides
    for jd in steps:
        res, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH)                     #PLANETA DAS EFEMÉRIDES (COLUNA)
        lon = res[0]
        deg_in_sign = lon % 30
        
        y, m, d, h = swe.revjul(jd)
        dt = datetime(y, m, d, int(h), int((h%1)*60))
        
        row = {'date': dt}
        for p in natal_points:
            target = p["grau"]
            # Distância modular circular (janela de 5 graus)
            dist = abs(((deg_in_sign - target + 15) % 30) - 15)
            
            if dist <= 5:
                intensity = np.exp(-0.5 * (dist / 1.5)**2)
            else:
                intensity = 0
            row[p["nome"]] = intensity
            
        all_data.append(row)

    df = pd.DataFrame(all_data)
    fig = go.Figure()

    # 3. Adicionar as Curvas
    for p in natal_points:
        name = p['nome']
        rgba_fill = hex_to_rgba(p['cor'], 0.15)
        
        fig.add_trace(go.Scatter(
            x=df['date'], 
            y=df[name],
            mode='lines',
            name=name,
            line=dict(color=p['cor'], width=2),
            fill='tozeroy',
            fillcolor=rgba_fill,
            hovertemplate=f"<b>{name}</b><br>Data: %{{x}}<br>Força: %{{y:.2f}}<extra></extra>"
        ))

    # 4. Adicionar Anotações de Data
    for p in natal_points:
        name = p['nome']
        peak_mask = (df[name] > 0.98) & (df[name] > df[name].shift(1)) & (df[name] > df[name].shift(-1))
        picos = df[peak_mask]
        
        for _, row in picos.iterrows():
            fig.add_annotation(
                x=row['date'], y=row[name],
                text=f"{row['date'].strftime('%d/%m')}",
                showarrow=True, arrowhead=1, ax=0, ay=-25,
                font=dict(color=p['cor'], size=11, family="Arial Black"),
                bgcolor="rgba(255,255,255,0.8)", bordercolor=p['cor']
            )

    # 5. Layout Interativo
    fig.update_layout(
        title=dict(text='<b>TRÂNSITOS DA LUA 2026</b>', x=0.5),     #TÍTULO DO GRÁFICO
        xaxis=dict(
            rangeslider=dict(visible=True, thickness=0.07),
            type='date',
            range=[datetime(2026, 1, 1), datetime(2026, 1, 31)], 
            tickformat='%d/%m\n%Y'
        ),
        yaxis=dict(title='Intensidade do Aspecto', range=[0, 1.2]),
        template='plotly_white',
        dragmode='pan',
        hovermode='x unified'
    )

    file_name = "aspectos_lua_2026.html"                                           #NOME DO ARQUIVO
    fig.write_html(file_name)
    print(f"Sucesso! Arquivo '{file_name}' gerado na área de trabalho ou pasta do script.")

if __name__ == "__main__":
    generate_natal_aspects_chart()



