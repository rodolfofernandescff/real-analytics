import plotly.graph_objects as go  # type: ignore
import pandas as pd  # type: ignore

def create_food_inflation_comparison_chart(
    df_general: pd.DataFrame, 
    df_food: pd.DataFrame
) -> go.Figure:
    """
    Gera um gráfico comparativo da evolução do IPCA Geral vs. IPCA Alimentação e Bebidas.
    """
    # Reamostra para média mensal (MS) para alinhar datas perfeitamente se necessário
    # Ambos já devem vir alinhados mensalmente dos conectores
    df_merged = pd.merge(
        df_general[["data", "ipca_mensal"]],
        df_food[["data", "ipca_alimento"]],
        on="data",
        how="inner"
    )

    fig = go.Figure()

    # Linha da Inflação Geral (Cinza suave)
    fig.add_trace(
        go.Scatter(
            x=df_merged["data"],
            y=df_merged["ipca_mensal"],
            name="IPCA Geral (Média de Preços)",
            line=dict(color="#A9A9A9", width=2),
            hovertemplate="Mês: %{x|%m/%Y}<br>Geral: %{y:.2f}%<extra></extra>"
        )
    )

    # Linha da Inflação de Alimentos (Laranja/Vermelho Quente)
    fig.add_trace(
        go.Scatter(
            x=df_merged["data"],
            y=df_merged["ipca_alimento"],
            name="Alimentação & Bebidas (Alimentos)",
            line=dict(color="#FF4500", width=2.5), # Orange Red
            hovertemplate="Mês: %{x|%m/%Y}<br>Alimentos: %{y:.2f}%<extra></extra>"
        )
    )

    # Customização de Layout Premium
    fig.update_layout(
        title=dict(
            text="Evolução da Inflação: Geral (IPCA) vs. Alimentação e Bebidas",
            font=dict(size=18, family="Outfit, sans-serif")
        ),
        template="plotly_dark",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        ),
        margin=dict(l=20, r=20, t=80, b=20),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )

    fig.update_yaxes(
        title_text="Variação Mensal (%)",
        gridcolor="rgba(255, 255, 255, 0.05)",
    )

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

    # Adiciona linha horizontal em 0% (linha neutra de inflação)
    fig.add_hline(y=0.0, line_dash="solid", line_color="white", line_width=1, opacity=0.3)

    return fig
