import plotly.graph_objects as go  # type: ignore
import pandas as pd  # type: ignore

def create_food_purchasing_power_chart(df_food_power: pd.DataFrame) -> go.Figure:
    """
    Gera um gráfico temporal da quantidade equivalente de cestas básicas 
    que podiam ser compradas com um salário mínimo nominal (Poder de Compra Alimentar).
    """
    fig = go.Figure()

    # Linha de Poder de Compra Alimentar (Verde Esmeralda Médio)
    fig.add_trace(
        go.Scatter(
            x=df_food_power["data"],
            y=df_food_power["cestas_por_salario"],
            name="Cestas Básicas por Salário Mínimo",
            line=dict(color="#00FA9A", width=3), # Primavera Esmeralda
            fill="tozeroy",
            fillcolor="rgba(0, 250, 154, 0.03)",
            hovertemplate="Data: %{x|%m/%Y}<br>Cestas Básicas: %{y:.2f} cestas<br>Cesta Básica (Preço Proxy): R$ %{customdata:,.2f}<extra></extra>",
            customdata=df_food_power["cesta_preco"]
        )
    )

    # Customização de Layout Premium
    fig.update_layout(
        title=dict(
            text="Evolução do Poder de Compra Alimentar (Qtd Cestas por Salário Mínimo)",
            font=dict(size=18, family="Outfit, sans-serif")
        ),
        template="plotly_dark",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=80, b=20),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )

    fig.update_yaxes(
        title_text="Quantidade de Cestas Básicas",
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

def create_minimum_wage_growth_chart(df_wage: pd.DataFrame) -> go.Figure:
    """
    Gera um gráfico anual de evolução do Salário Mínimo Nominal 
    exibindo o valor nominal e o percentual de crescimento anual (YoY).
    """
    if df_wage.empty:
        return go.Figure()
        
    df = df_wage.copy()
    df["ano"] = df["data"].dt.year
    
    # Agrupa por ano pegando o último salário do ano como referência nominal anual
    df_annual = df.groupby("ano").last().reset_index()
    
    # Calcula a taxa de crescimento nominal anual (%)
    df_annual["crescimento"] = df_annual["salario_minimo"].pct_change() * 100.0
    # Preenche o primeiro ano (sem anterior) com 0%
    df_annual["crescimento"] = df_annual["crescimento"].fillna(0.0)
    
    fig = go.Figure()
    
    # Barras de Salário Mínimo Nominal (Azul Safira suave)
    fig.add_trace(
        go.Bar(
            x=df_annual["ano"],
            y=df_annual["salario_minimo"],
            name="Salário Mínimo (R$)",
            marker_color="#1E90FF", # Dodger Blue
            opacity=0.85,
            hovertemplate="Ano: %{x}<br>Salário Mínimo: R$ %{y:,.2f}<br>Crescimento YoY: %{customdata:+.2f}%<extra></extra>",
            customdata=df_annual["crescimento"]
        )
    )
    
    # Customização de Layout Premium
    fig.update_layout(
        title=dict(
            text="Evolução Anual do Salário Mínimo Nominal",
            font=dict(size=18, family="Outfit, sans-serif")
        ),
        template="plotly_dark",
        hovermode="x unified",
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
    )
    
    return fig
