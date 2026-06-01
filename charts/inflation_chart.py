import plotly.graph_objects as go  # type: ignore
from plotly.subplots import make_subplots  # type: ignore
import pandas as pd  # type: ignore

def create_inflation_chart(df_ipca: pd.DataFrame) -> go.Figure:
    """
    Cria um gráfico interativo mostrando a variação mensal do IPCA (barras) 
    e o Número-Índice acumulado (linha) em dupla escala.
    """
    # Cria a figura com eixo duplo
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Cores dinâmicas robustas: Vermelho para inflação, Verde para deflação, Cinza para valores nulos (NaN/None)
    colors = [
        "#FF6347" if pd.notna(val) and val >= 0 
        else "#3CB371" if pd.notna(val) 
        else "#888888" 
        for val in df_ipca["ipca_mensal"]
    ]

    # 1. Adiciona a Variação Mensal do IPCA (Eixo Esquerdo - Barras)
    fig.add_trace(
        go.Bar(
            x=df_ipca["data"],
            y=df_ipca["ipca_mensal"],
            name="IPCA Mensal (%)",
            marker_color=colors,
            opacity=0.85,
            hovertemplate="Mês: %{x|%m/%Y}<br>Variação: %{y:.2f}%<extra></extra>"
        ),
        secondary_y=False,
    )

    # 2. Adiciona o Número-Índice Acumulado (Eixo Direito - Linha)
    fig.add_trace(
        go.Scatter(
            x=df_ipca["data"],
            y=df_ipca["ipca_indice"],
            name="Número-Índice (Preços Acumulados)",
            line=dict(color="#00FFFF", width=2.5), # Ciano
            hovertemplate="Mês: %{x|%m/%Y}<br>Número-Índice: %{y:.2f}<extra></extra>"
        ),
        secondary_y=True,
    )

    # Customização de Layout Premium
    fig.update_layout(
        title=dict(
            text="IPCA: Inflação Mensal vs. Nível de Preços Acumulado",
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

    # Ajustes de Eixos
    fig.update_yaxes(
        title_text="<b>Variação Mensal (%)</b>",
        title_font=dict(color="#FF6347"),
        tickfont=dict(color="#FF6347"),
        gridcolor="rgba(255, 255, 255, 0.05)",
        secondary_y=False
    )

    fig.update_yaxes(
        title_text="<b>Número-Índice (Base Dez/1993=100)</b>",
        title_font=dict(color="#00FFFF"),
        tickfont=dict(color="#00FFFF"),
        gridcolor="rgba(0,0,0,0)",
        secondary_y=True
    )

    # Adiciona linha horizontal em 0% no eixo esquerdo (linha neutra de inflação)
    fig.add_hline(y=0.0, line_dash="solid", line_color="white", line_width=1, opacity=0.3, secondary_y=False)

    fig.update_xaxes(
        title_text="Ano",
        gridcolor="rgba(255, 255, 255, 0.05)",
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1 Ano", step="year", stepmode="backward"),
                dict(count=5, label="5 Anos", step="year", stepmode="backward"),
                dict(count=10, label="10 Anos", step="year", stepmode="backward"),
                dict(step="all", label="Tudo")
            ]),
            font=dict(color="#000")
        )
    )

    return fig
