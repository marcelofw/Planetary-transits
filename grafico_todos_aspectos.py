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

ASPECTOS = {
    0: "Conjunção", 30: "Semi-sêxtil", 60: "Sêxtil", 90: "Quadratura", 
    120: "Trígono", 150: "Quincúncio", 180: "Oposição"
}

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

def calcular_aspecto(long1, long2):
    diff = abs(long1 - long2) % 360
    if diff > 180: diff = 360 - diff
    for angulo, nome in ASPECTOS.items():
        if abs(diff - angulo) <= 5: # Orbe de 5 graus
            return nome
    return "Outro"

def generate_degree_transit_chart():
    # ==========================================
    # 1. CONFIGURAÇÃO
    # ==========================================
    ano = 2026
    grau_alvo_natal = "27.0"  
    planeta_natal_ui = "Sol"      
    signo_natal_ui = "Capricórnio" 
    
    grau_decimal = dms_to_dec(grau_alvo_natal)
    idx_signo_natal = SIGNOS.index(signo_natal_ui) if signo_natal_ui in SIGNOS else 0
    long_natal_absoluta = (idx_signo_natal * 30) + grau_decimal
    
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
            row[f"{p['nome']}_long"] = long_abs
            row[f"{p['nome']}_status"] = "Retrógrado" if velocidade < 0 else "Direto"
            row[f"{p['nome']}_info"] = f"{get_signo(long_abs)}{mov}"
            
        all_data.append(row)

    df = pd.DataFrame(all_data).infer_objects(copy=False)

    # Preparação do nome base para os arquivos
    grau_limpo = str(grau_alvo_natal).replace('.', '_')

    # ==========================================
    # 3. GERAÇÃO DA TABELA EXCEL
    # ==========================================
    eventos = []
    for p in planetas_monitorados:
        nome = p["nome"]
        serie_tabela = df[nome].fillna(0).values
        
        for i in range(1, len(serie_tabela) - 1):
            if serie_tabela[i] > 0.98 and serie_tabela[i] > serie_tabela[i-1] and serie_tabela[i] > serie_tabela[i+1]:
                
                idx_ini = i
                while idx_ini > 0 and serie_tabela[idx_ini] > 0.01:
                    idx_ini -= 1
                
                idx_fim = i
                while idx_fim < len(serie_tabela) - 1 and serie_tabela[idx_fim] > 0.01:
                    idx_fim += 1
                
                row_pico = df.iloc[i]
                long_trans = row_pico[f"{nome}_long"]
                
                eventos.append({
                    "Data e Hora Início": df.iloc[idx_ini]['date'].strftime('%d/%m/%Y %H:%M'),
                    "Data e Hora Pico": row_pico['date'].strftime('%d/%m/%Y %H:%M'),
                    "Data e Hora Término": df.iloc[idx_fim]['date'].strftime('%d/%m/%Y %H:%M'),
                    "Grau Natal": f"{grau_alvo_natal}°",
                    "Planeta e Signo Natal": f"{planeta_natal_ui} em {signo_natal_ui}",
                    "Planeta e Signo em Trânsito": f"{nome.capitalize()} em {get_signo(long_trans)}",
                    "Status": row_pico[f"{nome}_status"],
                    "Aspecto": calcular_aspecto(long_trans, long_natal_absoluta)
                })

    if eventos:
        df_excel = pd.DataFrame(eventos)
        # NOME DO ARQUIVO EXCEL COM O GRAU
        excel_name = f"tabela_transitos_{ano}_grau_{grau_limpo}.xlsx"
        df_excel.to_excel(excel_name, index=False)
        print(f"Sucesso! Tabela Excel gerada: {excel_name}")

    # ==========================================
    # 4. CONSTRUÇÃO DO GRÁFICO
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
                textfont=dict(family="Arial Black", size=10, color="#CCCCCC"),
                marker=dict(symbol="triangle-down", color=p['cor'], size=8),
                legendgroup=p['nome'],
                showlegend=False,
                hoverinfo='skip'
            ))

    fig.update_layout(
        title=dict(text=f'Revolucao Planetaria {ano}: Grau {grau_alvo_natal}', x=0.5),
        xaxis=dict(
            type='date', 
            tickformat='%d/%m\n%Y', 
            hoverformat='%d/%m/%Y %H:%M',
            rangeslider=dict(visible=True, thickness=0.08)
        ),
        yaxis=dict(title='Intensidade', range=[0, 1.25], fixedrange=True),
        template='plotly_white',
        hovermode='x unified', 
        dragmode='pan',
        margin=dict(t=100)
    )

    # NOME DO ARQUIVO HTML COM O GRAU
    html_file = f"revolucao_{ano}_grau_{grau_limpo}.html"
    fig.write_html(html_file, config={'scrollZoom': True})
    
    print(f"Sucesso! Grafico gerado: {html_file}")

if __name__ == "__main__":
    generate_degree_transit_chart()