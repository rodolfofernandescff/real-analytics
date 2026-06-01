import plotly.graph_objects as go  # type: ignore
import pandas as pd  # type: ignore

def create_nominal_vs_real_salary_chart(df_power: pd.DataFrame) -> go.Figure:
    """
    Gera um gráfico comparativo da evolução do Salário Mínimo Nominal vs. Salário Mínimo Real.
    """
    fig = go.Figure()

    # Linha do Salário Nominal (Cinza/Branco suave)
    fig.add_trace(
        go.Scatter(
            x=df_power["data"],
            y=df_power["salario_nominal"],
            name="Salário Nominal (Valor da Época)",
            line=dict(color="#A9A9A9", width=2, dash="dot"),
            hovertemplate="Data: %{x|%m/%Y}<br>Nominal: R$ %{y:,.2f}<extra></extra>"
        )
    )

    # Linha do Salário Real (Verde Esmeralda Vibrante - Poder de Compra Atual)
    fig.add_trace(
        go.Scatter(
            x=df_power["data"],
            y=df_power["salario_real"],
            name="Salário Real (Poder de Compra Ajustado pela Inflação)",
            line=dict(color="#00FA9A", width=3), # Verde Primavera/Esmeralda
            fill="tonexty", # Preenche a lacuna de inflação entre as linhas
            fillcolor="rgba(0, 250, 154, 0.05)",
            hovertemplate="Data: %{x|%m/%Y}<br>Real (Hoje): R$ %{y:,.2f}<extra></extra>"
        )
    )

    # Customização de Layout Premium
    fig.update_layout(
        title=dict(
            text="Evolução do Salário Mínimo: Nominal vs. Real",
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
        title_text="Valor em Reais (R$)",
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

    return fig

def create_purchasing_power_index_chart(df_power: pd.DataFrame) -> go.Figure:
    """
    Gera um gráfico do Índice de Poder de Compra do Salário Mínimo (Base Julho de 1994 = 100).
    """
    fig = go.Figure()

    # Linha do Índice
    fig.add_trace(
        go.Scatter(
            x=df_power["data"],
            y=df_power["poder_compra_index"],
            name="Índice de Poder de Compra",
            line=dict(color="#FF8C00", width=2.5), # Dark Orange
            hovertemplate="Data: %{x|%m/%Y}<br>Índice: %{y:.1f} (Jul/94=100)<extra></extra>"
        )
    )

    # Linha de Base em 100 (Poder de compra inicial do Plano Real)
    fig.add_hline(
        y=100.0,
        line_dash="dash",
        line_color="#FF4500", # Laranja avermelhado
        line_width=1.5,
        annotation_text="Base Plano Real (Jul/1994 = 100)",
        annotation_position="bottom right",
        annotation_font=dict(color="#FF4500", size=10)
    )

    # Customização de Layout Premium
    fig.update_layout(
        title=dict(
            text="Evolução do Índice de Poder de Compra do Salário Mínimo",
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
        title_text="Índice (Jul/1994 = 100)",
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

    return fig
