import plotly.graph_objects as go  # type: ignore
from plotly.subplots import make_subplots  # type: ignore
import pandas as pd  # type: ignore
from typing import Optional

def create_exchange_and_selic_chart(
    df_dolar: pd.DataFrame, 
    df_selic: pd.DataFrame, 
    use_resampling: bool = True
) -> go.Figure:
    """
    Cria um gráfico interativo de dupla escala (eixo Y duplo) comparando o Dólar e a SELIC Meta.
    """
    # 1. Alinha os dados para exibição (reamostra se solicitado para ficar mais leve e legível)
    if use_resampling:
        # Reamostra para média semanal (W) para suavizar ruídos diários e acelerar o Plotly
        df_dol_plot = df_dolar.set_index("data").resample("W").mean().reset_index()
        df_sel_plot = df_selic.set_index("data").resample("W").mean().reset_index()
    else:
        df_dol_plot = df_dolar
        df_sel_plot = df_selic

    # Inicializa o gráfico com dois eixos Y
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Adiciona a série do Dólar (Eixo Esquerdo)
    fig.add_trace(
        go.Scatter(
            x=df_dol_plot["data"],
            y=df_dol_plot["dolar"],
            name="Dólar Comercial (Venda)",
            line=dict(color="#FFD700", width=2.5), # Dourado
            hovertemplate="Data: %{x|%d/%m/%Y}<br>Dólar: R$ %{y:.4f}<extra></extra>"
        ),
        secondary_y=False,
    )

    # Adiciona a série da SELIC (Eixo Direito)
    fig.add_trace(
        go.Scatter(
            x=df_sel_plot["data"],
            y=df_sel_plot["selic"],
            name="SELIC Meta (% a.a.)",
            line=dict(color="#1E90FF", width=2.0, dash="dash"), # Azul Safira
            hovertemplate="Data: %{x|%d/%m/%Y}<br>SELIC: %{y:.2f}% a.a.<extra></extra>"
        ),
        secondary_y=True,
    )

    # Customização de Layout Premium
    fig.update_layout(
        title=dict(
            text="Evolução do Dólar vs. Taxa SELIC Meta COPOM",
            font=dict(size=18, family="Outfit, sans-serif")
        ),
        template="plotly_dark",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=20, r=20, t=80, b=20),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )

    # Ajustes dos Eixos Y
    fig.update_yaxes(
        title_text="<b>Dólar (R$)</b>", 
        title_font=dict(color="#FFD700"),
        tickfont=dict(color="#FFD700"),
        gridcolor="rgba(255, 255, 255, 0.05)",
        secondary_y=False
    )
    
    fig.update_yaxes(
        title_text="<b>SELIC (% a.a.)</b>", 
        title_font=dict(color="#1E90FF"),
        tickfont=dict(color="#1E90FF"),
        gridcolor="rgba(0,0,0,0)", # Remove a malha dupla para não poluir
        secondary_y=True
    )

    # Ajuste do Eixo X
    fig.update_xaxes(
        title_text="Ano",
        gridcolor="rgba(255, 255, 255, 0.05)",
        rangeslider=dict(visible=False),
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1 Ano", step="year", stepmode="backward"),
                dict(count=5, label="5 Anos", step="year", stepmode="backward"),
                dict(count=10, label="10 Anos", step="year", stepmode="backward"),
                dict(step="all", label="Tudo")
            ]),
            font=dict(color="#000") # Botões visíveis
        )
    )

    return fig
