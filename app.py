import logging
from datetime import datetime, date
import os
import pandas as pd
import streamlit as st

# Configuração da página - DEVE SER O PRIMEIRO COMANDO STREAMLIT
st.set_page_config(
    page_title="Real Analytics | Análise Econômica",
    page_icon="🇧🇷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Importações internas do projeto
from services.banco_central import get_exchange_rate, get_selic_rate
from services.ibge import get_ipca_data
from services.ipea import get_minimum_wage_data
from services.ibge_food_inflation import get_food_inflation_data
from calculations.inflation import adjust_value_by_inflation, calculate_accumulated_inflation
from calculations.purchasing_power import calculate_real_minimum_wage
from calculations.food_inflation import adjust_food_value_by_inflation
from calculations.food_purchasing_power import calculate_food_purchasing_power
from calculations.indicators import calculate_correlations, get_presidency_summaries
from charts.exchange_chart import create_exchange_and_selic_chart
from charts.inflation_chart import create_inflation_chart
from charts.purchasing_power_chart import create_nominal_vs_real_salary_chart, create_purchasing_power_index_chart
from charts.food_inflation_chart import create_food_inflation_comparison_chart
from charts.food_purchasing_power_chart import create_food_purchasing_power_chart, create_minimum_wage_growth_chart
from utils.formatter import format_currency_brl, format_currency_usd, format_percent, format_date

# Configuração do Logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Caminhos dos arquivos de cache local para fallback offline
CACHE_DIR = "assets"
CACHE_DOLAR = os.path.join(CACHE_DIR, "cache_dolar.csv")
CACHE_SELIC = os.path.join(CACHE_DIR, "cache_selic.csv")
CACHE_IPCA = os.path.join(CACHE_DIR, "cache_ipca.csv")
CACHE_WAGE = os.path.join(CACHE_DIR, "cache_wage.csv")

# CSS customizado para Visual Premium
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
        
        /* Modificando a fonte global */
        html, body, [class*="css"], .stText, .stMarkdown {
            font-family: 'Outfit', sans-serif !important;
        }
        
        /* Customização de Cards de Métricas com Glassmorphism */
        div[data-testid="metric-container"] {
            background-color: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 18px 22px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
            transition: transform 0.2s, border-color 0.2s;
        }
        div[data-testid="metric-container"]:hover {
            transform: translateY(-2px);
            border-color: rgba(255, 215, 0, 0.3);
        }
        
        /* Cores de métricas de alta */
        div[data-testid="stMetricValue"] {
            font-size: 26px !important;
            font-weight: 600 !important;
            color: #FFFFFF !important;
        }
        
        /* Customizando botões e sliders */
        .stButton>button {
            border-radius: 8px;
            background-color: #2e7bcf;
            color: white;
            font-weight: 600;
            border: none;
            padding: 8px 20px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
            transition: all 0.2s;
        }
        .stButton>button:hover {
            background-color: #468ee6;
            transform: translateY(-1px);
        }
        
        /* Reduzindo tamanho da sidebar para ganhar respiro no main */
        section[data-testid="stSidebar"] {
            width: 260px !important;
            min-width: 260px !important;
        }
        
        /* Ajustando respiro geral do contêiner principal */
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
            padding-left: 3rem !important;
            padding-right: 3rem !important;
            max-width: 98% !important;
        }

        /* Banner de Cabeçalho Superior (Mais enxuto e no topo) */
        .header-container {
            background: linear-gradient(135deg, #111e38 0%, #060b13 100%);
            border-radius: 10px;
            padding: 15px 20px;
            margin-bottom: 20px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        }
        .header-title {
            color: #FFD700 !important;
            font-size: 26px !important;
            font-weight: 800 !important;
            margin: 0;
            padding-bottom: 2px;
            letter-spacing: -0.5px;
        }
        .header-subtitle {
            color: #8fa0c2 !important;
            font-size: 14px !important;
            margin: 0;
            font-weight: 300;
        }
        
        /* Destaques em Blocos (Com mais respiro) */
        .highlight-card {
            background: rgba(30, 144, 255, 0.05);
            border-left: 5px solid #1E90FF;
            border-radius: 4px 12px 12px 4px;
            padding: 15px 20px;
            margin: 20px 0;
        }
    </style>
""", unsafe_allow_html=True)

# ----------------- FUNÇÕES DE CARREGAMENTO DE DADOS COM FALLBACK -----------------

@st.cache_data(ttl=3600)
def load_dolar_data(start_str: str) -> tuple[pd.DataFrame, bool]:
    """Carrega dados do Dólar com cache local como fallback."""
    is_fallback = False
    try:
        df = get_exchange_rate(start_str)
        # Salva em cache local para emergências
        os.makedirs(CACHE_DIR, exist_ok=True)
        df.to_csv(CACHE_DOLAR, index=False)
        return df, is_fallback
    except Exception as e:
        logger.error(f"Erro ao obter Dólar da API: {e}")
        if os.path.exists(CACHE_DOLAR):
            logger.info("Carregando Dólar do cache local.")
            df = pd.read_csv(CACHE_DOLAR)
            df["data"] = pd.to_datetime(df["data"])
            is_fallback = True
            return df, is_fallback
        else:
            st.error("Sem conexão com o Banco Central e sem cache local disponível para o Dólar.")
            raise e

@st.cache_data(ttl=3600)
def load_selic_data(start_str: str) -> tuple[pd.DataFrame, bool]:
    """Carrega dados da SELIC com cache local como fallback."""
    is_fallback = False
    try:
        df = get_selic_rate(start_str)
        os.makedirs(CACHE_DIR, exist_ok=True)
        df.to_csv(CACHE_SELIC, index=False)
        return df, is_fallback
    except Exception as e:
        logger.error(f"Erro ao obter SELIC da API: {e}")
        if os.path.exists(CACHE_SELIC):
            logger.info("Carregando SELIC do cache local.")
            df = pd.read_csv(CACHE_SELIC)
            df["data"] = pd.to_datetime(df["data"])
            is_fallback = True
            return df, is_fallback
        else:
            st.error("Sem conexão com o Banco Central e sem cache local disponível para a SELIC.")
            raise e

@st.cache_data(ttl=3600)
def load_ipca_data() -> tuple[pd.DataFrame, bool]:
    """Carrega dados de IPCA com cache local como fallback."""
    is_fallback = False
    try:
        df = get_ipca_data()
        os.makedirs(CACHE_DIR, exist_ok=True)
        df.to_csv(CACHE_IPCA, index=False)
        return df, is_fallback
    except Exception as e:
        logger.error(f"Erro ao obter IPCA da API: {e}")
        if os.path.exists(CACHE_IPCA):
            logger.info("Carregando IPCA do cache local.")
            df = pd.read_csv(CACHE_IPCA)
            df["data"] = pd.to_datetime(df["data"])
            is_fallback = True
            return df, is_fallback
        else:
            st.error("Sem conexão com o IBGE e sem cache local disponível para a Inflação.")
            raise e

@st.cache_data(ttl=3600)
def load_wage_data() -> tuple[pd.DataFrame, bool]:
    """Carrega dados do Salário Mínimo com cache local como fallback."""
    is_fallback = False
    try:
        df = get_minimum_wage_data()
        os.makedirs(CACHE_DIR, exist_ok=True)
        df.to_csv(CACHE_WAGE, index=False)
        return df, is_fallback
    except Exception as e:
        logger.error(f"Erro ao obter Salário Mínimo da API: {e}")
        if os.path.exists(CACHE_WAGE):
            logger.info("Carregando Salário Mínimo do cache local.")
            df = pd.read_csv(CACHE_WAGE)
            df["data"] = pd.to_datetime(df["data"])
            is_fallback = True
            return df, is_fallback
        else:
            st.error("Sem conexão com o IPEA e sem cache local disponível para o Salário Mínimo.")
            raise e

@st.cache_data(ttl=3600)
def load_food_inflation_data() -> tuple[pd.DataFrame, bool]:
    """Carrega dados da Inflação de Alimentos com cache local como fallback."""
    is_fallback = False
    try:
        df = get_food_inflation_data("01/07/1994")
        os.makedirs(CACHE_DIR, exist_ok=True)
        df.to_csv(os.path.join(CACHE_DIR, "cache_food.csv"), index=False)
        return df, is_fallback
    except Exception as e:
        logger.error(f"Erro ao obter Inflação de Alimentos da API: {e}")
        cache_path = os.path.join(CACHE_DIR, "cache_food.csv")
        if os.path.exists(cache_path):
            logger.info("Carregando Inflação de Alimentos do cache local.")
            df = pd.read_csv(cache_path)
            df["data"] = pd.to_datetime(df["data"])
            is_fallback = True
            return df, is_fallback
        else:
            st.error("Sem conexão com o IBGE/BCB e sem cache local disponível para a Inflação de Alimentos.")
            raise e


# ----------------- TÍTULO DA APLICAÇÃO (HEADER PREMIUM) -----------------
st.markdown("""
    <div class="header-container">
        <h1 class="header-title">📊 REAL ANALYTICS</h1>
        <p class="header-subtitle">🇧🇷 O Monitor Definitivo da Inflação, Taxas de Juros e Poder de Compra Histórico do Real Brasileiro (BRL)</p>
    </div>
""", unsafe_allow_html=True)


# ----------------- BARRA LATERAL (FILTROS E FONTES) -----------------
st.sidebar.markdown("## 🔍 Filtros Temporais")

# Seletor de período rápido
periodo_rapido = st.sidebar.selectbox(
    "Escolha o período de análise:",
    options=[
        "Desde o Plano Real (1994)",
        "Últimos 10 anos",
        "Últimos 5 anos",
        "Últimos 12 meses",
        "Customizado"
    ],
    index=0
)

# Define datas iniciais e finais correspondentes
data_fim_default = datetime.now().date()

if periodo_rapido == "Desde o Plano Real (1994)":
    data_ini_default = date(1994, 7, 1)
elif periodo_rapido == "Últimos 10 anos":
    data_ini_default = date(data_fim_default.year - 10, data_fim_default.month, data_fim_default.day)
elif periodo_rapido == "Últimos 5 anos":
    data_ini_default = date(data_fim_default.year - 5, data_fim_default.month, data_fim_default.day)
elif periodo_rapido == "Últimos 12 meses":
    data_ini_default = date(data_fim_default.year - 1, data_fim_default.month, data_fim_default.day)
else:
    # Customizado
    col_ini, col_fim = st.sidebar.columns(2)
    with col_ini:
        data_ini_input = st.date_input("Início:", date(1994, 7, 1), min_value=date(1994, 7, 1), max_value=data_fim_default)
    with col_fim:
        data_fim_input = st.date_input("Fim:", data_fim_default, min_value=date(1994, 7, 1), max_value=data_fim_default)
    data_ini_default = data_ini_input
    data_fim_default = data_fim_input

# Converte datas de volta para datetime
data_inicio = datetime.combine(data_ini_default, datetime.min.time())
data_fim = datetime.combine(data_fim_default, datetime.max.time())

# Informações de fontes na barra lateral
st.sidebar.markdown("---")
st.sidebar.markdown("### 🏛️ Fontes de Dados Oficiais")
st.sidebar.markdown(
    """
    * **Câmbio & SELIC**: [Banco Central do Brasil](https://www.bcb.gov.br/) (SGS API)
    * **Inflação (IPCA)**: [IBGE](https://www.ibge.gov.br/) (SIDRA API)
    * **Salário Mínimo**: [IPEA](http://www.ipeadata.gov.br/) (Ipeadata API)
    
    *Todos os dados são coletados dinamicamente em tempo real, sem intermediários.*
    """
)


# ----------------- EXECUÇÃO DE CARGA DOS DADOS (COM SPINNER) -----------------
with st.spinner("Conectando aos servidores do Governo Federal e extraindo bases de dados..."):
    try:
        # Carga padrão - usamos a data limite do Plano Real (1994-07-01) para pegar a base inteira
        df_dolar_total, dol_fallback = load_dolar_data("01/07/1994")
        df_selic_total, sel_fallback = load_selic_data("01/07/1994")
        df_ipca_total, ipca_fallback = load_ipca_data()
        df_wage_total, wage_fallback = load_wage_data()
        df_food_total, food_fallback = load_food_inflation_data()
        
        # Indica se algum dado está vindo do cache por queda do servidor público
        algum_fallback = dol_fallback or sel_fallback or ipca_fallback or wage_fallback or food_fallback
        
        if algum_fallback:
            st.warning(
                "⚠️ Atenção: Um ou mais servidores governamentais estão temporariamente indisponíveis ou demorando a responder. "
                "Para garantir sua navegação, carregamos dados salvos em cache offline local."
            )
            
    except Exception as e:
        st.error(f"Erro fatal ao inicializar aplicação: {e}")
        st.stop()

# Filtra os DataFrames com base nas datas selecionadas na barra lateral
df_dolar = df_dolar_total[(df_dolar_total["data"] >= data_inicio) & (df_dolar_total["data"] <= data_fim)].copy()
df_selic = df_selic_total[(df_selic_total["data"] >= data_inicio) & (df_selic_total["data"] <= data_fim)].copy()
df_ipca = df_ipca_total[(df_ipca_total["data"] >= data_inicio) & (df_ipca_total["data"] <= data_fim)].copy()
df_wage = df_wage_total[(df_wage_total["data"] >= data_inicio) & (df_wage_total["data"] <= data_fim)].copy()
df_food = df_food_total[(df_food_total["data"] >= data_inicio) & (df_food_total["data"] <= data_fim)].copy()


# ----------------- PROCESSAMENTO & CÁLCULOS PRINCIPAIS -----------------

# 1. Salário Mínimo Real e Poder de Compra Geral
df_purchasing_power = calculate_real_minimum_wage(df_wage_total, df_ipca_total)
# Filtra o poder de compra pelo período visualizado
df_pp_filtered = df_purchasing_power[
    (df_purchasing_power["data"] >= data_inicio) & (df_purchasing_power["data"] <= data_fim)
].copy()

# 2. Poder de Compra Alimentar (DIEESE Cesta Básica Proxy)
df_food_power = calculate_food_purchasing_power(df_wage_total, df_food_total)
# Filtra o poder de compra alimentar pelo período visualizado
df_food_power_filtered = df_food_power[
    (df_food_power["data"] >= data_inicio) & (df_food_power["data"] <= data_fim)
].copy()

# 3. Dados Atuais para st.metric (últimos pontos de dados disponíveis globalmente)
latest_dolar = df_dolar_total.iloc[-1]["dolar"] if not df_dolar_total.empty else 0.0
# Variação cambial recente (últimos 30 dias de cotação comercial)
if len(df_dolar_total) > 30:
    prev_dolar = df_dolar_total.iloc[-30]["dolar"]
    delta_dolar = f"{((latest_dolar / prev_dolar) - 1) * 100:+.2f}% (30d)"
else:
    delta_dolar = None

latest_selic = df_selic_total.iloc[-1]["selic"] if not df_selic_total.empty else 0.0
# Variação da SELIC no último mês
if len(df_selic_total) > 30:
    prev_selic = df_selic_total.iloc[-30]["selic"]
    delta_selic = f"{latest_selic - prev_selic:+.2f}% p.p."
else:
    delta_selic = None

# IPCA acumulado de 12 meses
if len(df_ipca_total) >= 12:
    idx_now = df_ipca_total.iloc[-1]["ipca_indice"]
    idx_12m = df_ipca_total.iloc[-13]["ipca_indice"]
    ipca_12m = (idx_now / idx_12m) - 1
else:
    ipca_12m = 0.0

# IPCA de Alimentos acumulado de 12 meses
if len(df_food_total) >= 12:
    idx_food_now = df_food_total.iloc[-1]["ipca_alimento_indice"]
    idx_food_12m = df_food_total.iloc[-13]["ipca_alimento_indice"]
    ipca_food_12m = (idx_food_now / idx_food_12m) - 1
else:
    ipca_food_12m = 0.0

latest_wage = df_wage_total.iloc[-1]["salario_minimo"] if not df_wage_total.empty else 0.0

# Índice do Poder de Compra Geral atual
latest_pp_index = df_purchasing_power.iloc[-1]["poder_compra_index"] if not df_purchasing_power.empty else 100.0

# Índice do Poder de Compra Alimentar atual (Cestas Básicas equivalentes)
if not df_food_power.empty:
    latest_food_pp = df_food_power.iloc[-1]["cestas_por_salario"]
    df_jul_1994_f = df_food_power[df_food_power["data"] == datetime(1994, 7, 1)]
    prev_food_pp = df_jul_1994_f.iloc[0]["cestas_por_salario"] if not df_jul_1994_f.empty else df_food_power.iloc[0]["cestas_por_salario"]
    food_pp_index = (latest_food_pp / prev_food_pp) * 100
else:
    food_pp_index = 100.0


# ----------------- SEÇÃO DE CARD DE MÉTRICAS (PRODUTO PREMIUM) -----------------
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        label="💵 Dólar Comercial (Venda)",
        value=format_currency_usd(latest_dolar).replace("US$", "R$"), # Exibe em R$ por dólar
        delta=delta_dolar,
        delta_color="inverse" # Aumento de dólar é negativo para o Real
    )
with col2:
    st.metric(
        label="🏦 SELIC Meta (COPOM)",
        value=format_percent(latest_selic),
        delta=delta_selic
    )
with col3:
    st.metric(
        label="📈 IPCA Acumulado (12m)",
        value=format_percent(ipca_12m, is_fraction=True),
        delta=f"Meta Central: 3,0%"
    )
with col4:
    st.metric(
        label="💼 Salário Mínimo Nominal",
        value=format_currency_brl(latest_wage)
    )
with col5:
    st.metric(
        label="🛒 Poder de Compra Real",
        value=f"{latest_pp_index:.1f}%",
        delta=f"{(latest_pp_index - 100):+.1f}% desde 1994",
        delta_color="normal"
    )

st.markdown("<br>", unsafe_allow_html=True)


# ----------------- ESTRUTURA DE ABAS (TABS) DO DASHBOARD -----------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Painel Geral", 
    "📈 Inflação & Salários", 
    "🛒 Poder de Compra", 
    "🍎 Alimentação e Poder de Compra",
    "🧮 Simulador de Inflação", 
    "🏛️ Histórico & Correlações"
])

# -------------------------------- ABA 1: PAINEL GERAL --------------------------------
with tab1:
    st.markdown("### 📊 Comportamento Conjunto: Dólar vs Taxa de Juros")
    st.markdown(
        "A taxa SELIC é o principal instrumento de política monetária do Banco Central. "
        "Em tese, taxas de juros mais elevadas atraem capital estrangeiro em busca de rentabilidade, "
        "fortalecendo o Real frente ao Dólar. Abaixo, acompanhe esta dinâmica interativa:"
    )
    
    if not df_dolar.empty and not df_selic.empty:
        fig_ex = create_exchange_and_selic_chart(df_dolar, df_selic)
        st.plotly_chart(fig_ex, use_container_width=True)
    else:
        st.warning("Período sem dados disponíveis para Dólar ou SELIC.")
        
    st.markdown("""
        <div class="highlight-card">
            <h4>💡 Insight Macroeconômico</h4>
            <p>Repare nos ciclos econômicos: períodos de cortes agressivos na taxa SELIC (como em 2020) costumam coincidir com fortes pressões de desvalorização cambial (alta do Dólar). Inversamente, ciclos de alta de juros visam segurar a inflação e tendem a estabilizar ou arrefecer a cotação da moeda americana.</p>
        </div>
    """, unsafe_allow_html=True)

# -------------------------------- ABA 2: INFLAÇÃO & SALÁRIOS --------------------------------
with tab2:
    st.markdown("### 📈 Inflação de Preços (IPCA)")
    st.markdown(
        "O IPCA (Índice de Preços ao Consumidor Amplo), calculado pelo IBGE, mede a variação de preços da cesta básica de consumo das famílias. "
        "Abaixo, a variação mês a mês (barras vermelhas/verdes) e o nível acumulado histórico de preços (linha ciana):"
    )
    if not df_ipca.empty:
        fig_inf = create_inflation_chart(df_ipca)
        st.plotly_chart(fig_inf, use_container_width=True)
    else:
        st.warning("Sem dados de IPCA no período escolhido.")
        
    st.markdown("<br><hr><br>", unsafe_allow_html=True)
        
    st.markdown("### 💼 Evolução do Salário Mínimo: Nominal vs Real")
    st.markdown(
        "O salário mínimo nominal aumenta anualmente, mas grande parte deste reajuste serve apenas para recompor a inflação. "
        "A linha real (verde) mostra o salário mínimo do passado trazido para o poder de compra de hoje, evidenciando o real ganho real de renda:"
    )
    if not df_pp_filtered.empty:
        fig_wage = create_nominal_vs_real_salary_chart(df_pp_filtered)
        st.plotly_chart(fig_wage, use_container_width=True)
    else:
        st.warning("Sem dados de poder de compra no período escolhido.")

# -------------------------------- ABA 3: PODER DE COMPRA --------------------------------
with tab3:
    st.markdown("### 🛒 Evolução do Poder de Compra do Salário Mínimo")
    st.markdown(
        "Este índice representa o poder de compra real do salário mínimo ao longo do tempo. "
        "Definimos o poder de compra de **Julho de 1994 (lançamento do Real) como Base 100**. "
        "Qualquer valor acima de 100 indica ganho de poder aquisitivo real em relação à criação da moeda:"
    )
    
    if not df_pp_filtered.empty:
        fig_index = create_purchasing_power_index_chart(df_pp_filtered)
        st.plotly_chart(fig_index, use_container_width=True)
    else:
        st.warning("Sem dados disponíveis no período.")
        
    # Análise Estatística Prática do Poder de Compra
    if not df_purchasing_power.empty:
        initial_wage_1994 = df_wage_total[df_wage_total["data"] == datetime(1994, 7, 1)].iloc[0]["salario_minimo"]
        
        # Busca o salário mínimo de 1994 corrigido para hoje por inflação
        row_94 = df_purchasing_power[df_purchasing_power["data"] == datetime(1994, 7, 1)].iloc[0]
        wage_94_real_today = row_94["salario_real"]
        
        st.markdown(f"""
            <div class="highlight-card">
                <h4>📊 Raio-X do Poder de Compra Histórico</h4>
                <ul>
                    <li><strong>Em Julho de 1994:</strong> O salário mínimo nominal era de <strong>{format_currency_brl(initial_wage_1994)}</strong>.</li>
                    <li><strong>Erosão Monetária:</strong> Para comprar hoje as mesmas coisas que aquele salário inicial comprava em 1994, seriam necessários <strong>{format_currency_brl(wage_94_real_today)}</strong> (valor corrigido pela inflação acumulada).</li>
                    <li><strong>Valor Atual:</strong> Como o salário mínimo vigente é de <strong>{format_currency_brl(latest_wage)}</strong>, isso demonstra que o trabalhador de salário mínimo teve um ganho real de poder de compra de aproximadamente <strong>{latest_pp_index - 100:.1f}%</strong> (ou seja, seu poder de compra é <strong>{latest_pp_index/100:.2f}x</strong> superior ao de 1994).</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)

# -------------------------------- ABA 4: ALIMENTAÇÃO E PODER DE COMPRA --------------------------------
with tab4:
    st.markdown("### 🍎 Alimentação e Poder de Compra")
    st.markdown(
        "A alimentação é o item de maior peso na cesta de consumo das famílias brasileiras. "
        "Esta seção analisa a evolução dos preços do grupo **Alimentação e Bebidas** em comparação ao IPCA geral "
        "e mede o impacto direto na mesa do trabalhador através da quantidade de cestas básicas adquiridas por salário."
    )
    
    # 1. Cards de Indicadores Principais de Alimentos
    col_fd1, col_fd2, col_fd3, col_fd4, col_fd5 = st.columns(5)
    
    # Diferença de inflação
    food_diff = ipca_food_12m - ipca_12m
    
    # Cestas básicas equivalentes atual
    latest_food_baskets = df_food_power.iloc[-1]["cestas_por_salario"] if not df_food_power.empty else 0.0
    
    with col_fd1:
        st.metric(
            label="📈 Inflação Geral IPCA (12m)",
            value=format_percent(ipca_12m, is_fraction=True)
        )
    with col_fd2:
        st.metric(
            label="🍎 Inflação de Alimentos (12m)",
            value=format_percent(ipca_food_12m, is_fraction=True),
            delta=f"{food_diff * 100:+.2f}% p.p. vs Geral" if food_diff != 0 else None,
            delta_color="inverse" # Aumento maior em alimentos é ruim
        )
    with col_fd3:
        st.metric(
            label="📊 Saldo Alimentos vs Geral",
            value=format_percent(food_diff, is_fraction=True),
            delta="Pressão Alimentar" if food_diff > 0 else "Alívio Alimentar",
            delta_color="inverse" if food_diff > 0 else "normal"
        )
    with col_fd4:
        st.metric(
            label="💼 Salário Mínimo Atual",
            value=format_currency_brl(latest_wage)
        )
    with col_fd5:
        st.metric(
            label="🛒 Compra Alimentar (proxy)",
            value=f"{latest_food_baskets:.2f} Cestas",
            delta=f"{food_pp_index - 100:+.1f}% vs 1994",
            delta_color="normal"
        )
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 2. Seção de Gráficos de Alimentos
    tab_graphs_food = st.tabs([
        "📈 Variação IPCA Alimentos", 
        "💼 Salário Anual & Crescimento", 
        "🛒 Cestas Básicas por Salário"
    ])
    
    with tab_graphs_food[0]:
        st.markdown("#### Evolução da Inflação de Alimentos")
        st.markdown(
            "Veja a variação da inflação mensal do grupo de **Alimentação e Bebidas** em comparação com o IPCA Geral. "
            "Alimentos tendem a apresentar picos sazonais mais acentuados devido a safras e intempéries climáticas:"
        )
        if not df_food.empty and not df_ipca.empty:
            fig_food_inf = create_food_inflation_comparison_chart(df_ipca, df_food)
            st.plotly_chart(fig_food_inf, use_container_width=True)
        else:
            st.warning("Período sem dados disponíveis para inflação de alimentos.")
            
    with tab_graphs_food[1]:
        st.markdown("#### Evolução do Salário Mínimo Nominal e YoY Growth")
        st.markdown(
            "Acompanhe o aumento anual nominal do salário mínimo no Brasil e o percentual de crescimento "
            "ano contra ano (Year-over-Year):"
        )
        if not df_wage.empty:
            fig_wage_growth = create_minimum_wage_growth_chart(df_wage)
            st.plotly_chart(fig_wage_growth, use_container_width=True)
        else:
            st.warning("Sem dados disponíveis do salário mínimo.")
            
    with tab_graphs_food[2]:
        st.markdown("#### Evolução do Poder de Compra Alimentar")
        st.markdown(
            "Quantas cestas básicas um salário mínimo conseguia comprar ao longo da história? "
            "Utilizamos a proxy robusta do custo da Cesta Básica deflacionada retrospectivamente a partir "
            "do valor de hoje (R$ 800,00) pelo IPCA de Alimentos:"
        )
        if not df_food_power_filtered.empty:
            fig_food_pp = create_food_purchasing_power_chart(df_food_power_filtered)
            st.plotly_chart(fig_food_pp, use_container_width=True)
        else:
            st.warning("Sem dados suficientes para gerar o poder de compra alimentar.")
            
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 3. Simulador de Compras de Alimentos
    st.markdown("### 🛒 Simulador de Compras de Alimentos (Mercado)")
    st.markdown(
        "Compare quanto custava encher o carrinho de supermercado no passado e quanto custaria "
        "comprar os mesmos itens hoje, corrigidos unicamente pela inflação do grupo de **Alimentação e Bebidas**."
    )
    
    col_fsim1, col_fsim2 = st.columns([1, 2])
    
    with col_fsim1:
        st.markdown("#### ⚙️ Parâmetros do Carrinho")
        sim_food_val = st.number_input("Valor da Compra de Alimentos (R$):", min_value=1.0, value=500.0, step=50.0, key="sim_food_val")
        
        # Filtra datas disponíveis desde Jul/1994
        df_food_all = df_food_total[df_food_total["data"] >= datetime(1994, 7, 1)].sort_values("data")
        lista_datas_f = df_food_all["data"].tolist()
        lista_datas_f_str = [dt.strftime("%m/%Y") for dt in lista_datas_f]
        
        sim_food_origem_str = st.selectbox(
            "Selecione o mês/ano de referência no passado:",
            options=lista_datas_f_str,
            index=192 if len(lista_datas_f_str) > 192 else 0, # Padrão: 2010 se disponível, ou primeira data
            key="sim_food_origem"
        )
        
        st.text_input("Mês/ano de destino (Hoje):", value=lista_datas_f_str[-1], disabled=True, key="sim_food_dest")
        
    with col_fsim2:
        st.markdown("#### 🎯 Resultado da Atualização Alimentar")
        
        idx_f_origem = lista_datas_f_str.index(sim_food_origem_str)
        data_origem_f = lista_datas_f[idx_f_origem]
        data_destino_f = lista_datas_f[-1]
        
        adj_food_val, food_rate, eff_start_f, eff_end_f = adjust_food_value_by_inflation(
            sim_food_val, data_origem_f, data_destino_f, df_food_total
        )
        
        col_fres1, col_fres2 = st.columns(2)
        with col_fres1:
            st.markdown(
                f"""
                <div style="background-color:rgba(255, 255, 255, 0.02); padding:15px; border-radius:10px; border:1px solid rgba(255,255,255,0.05); text-align:center;">
                    <span style="font-size:12px; color:#A9A9A9; text-transform:uppercase;">Valor Corrigido do Carrinho</span>
                    <h2 style="color:#00FA9A; font-size:32px; font-weight:800; margin:5px 0;">{format_currency_brl(adj_food_val)}</h2>
                    <span style="font-size:11px; color:#8fa0c2;">Poder de compra alimentar em {format_date(eff_end_f)}</span>
                </div>
                """, unsafe_allow_html=True
            )
        with col_fres2:
            st.markdown(
                f"""
                <div style="background-color:rgba(255, 255, 255, 0.02); padding:15px; border-radius:10px; border:1px solid rgba(255,255,255,0.05); text-align:center;">
                    <span style="font-size:12px; color:#A9A9A9; text-transform:uppercase;">Inflação de Alimentos</span>
                    <h2 style="color:#FF8C00; font-size:32px; font-weight:800; margin:5px 0;">{format_percent(food_rate, is_fraction=True)}</h2>
                    <span style="font-size:11px; color:#8fa0c2;">Grupo Alimentação & Bebidas</span>
                </div>
                """, unsafe_allow_html=True
            )
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Frase explicativa em destaque (boas práticas de UI/UX)
        st.markdown(
            f"""
            <div style="background: rgba(30, 144, 255, 0.05); border: 1px solid rgba(30, 144, 255, 0.15); border-radius:10px; padding:20px;">
                <h4 style="margin:0; color:#1E90FF;">🕵️ Análise de Equivalência do Carrinho</h4>
                <p style="margin:8px 0 0 0; font-size:15px; color: var(--text-color); line-height: 1.5;">
                    Uma compra de supermercado de <strong>{format_currency_brl(sim_food_val)}</strong> em <strong>{format_date(eff_start_f)}</strong> equivaleria aproximadamente a <strong>{format_currency_brl(adj_food_val)}</strong> atualmente, considerando a inflação acumulada de alimentos de <strong>{format_percent(food_rate, is_fraction=True)}</strong> no período.
                </p>
            </div>
            """, unsafe_allow_html=True
        )

# -------------------------------- ABA 5: SIMULADOR DE INFLAÇÃO --------------------------------
with tab5:
    st.markdown("### 🧮 Simulador de Correção Monetária e Renda Histórica")
    st.markdown(
        "Digite um valor em Reais e selecione o mês/ano de referência no passado. "
        "O sistema calculará automaticamente o valor correspondente hoje ajustado pela inflação acumulada do IPCA, "
        "além de fornecer uma comparação visual com o Salário Mínimo de cada época."
    )
    
    col_sim1, col_sim2 = st.columns([1, 2])
    
    with col_sim1:
        st.markdown("#### ⚙️ Parâmetros do Cálculo")
        sim_valor = st.number_input("Valor Original (R$):", min_value=1.0, value=100.0, step=50.0)
        
        # Filtra anos disponíveis a partir de Julho/1994
        df_ipca_all = df_ipca_total[df_ipca_total["data"] >= datetime(1994, 7, 1)].sort_values("data")
        lista_datas = df_ipca_all["data"].tolist()
        lista_datas_str = [dt.strftime("%m/%Y") for dt in lista_datas]
        
        # Seletor de data de origem
        sim_data_origem_str = st.selectbox(
            "Selecione o mês/ano de origem do valor:",
            options=lista_datas_str,
            index=0 # Padrão: Julho de 1994
        )
        
        # Data de Destino (Fixada em hoje para maior utilidade)
        st.text_input("Mês/ano de destino (Atual):", value=lista_datas_str[-1], disabled=True)
        
    with col_sim2:
        st.markdown("#### 🎯 Resultado da Atualização Monetária")
        
        # Executa o cálculo de correção
        idx_origem = lista_datas_str.index(sim_data_origem_str)
        data_origem = lista_datas[idx_origem]
        data_destino = lista_datas[-1] # Último mês do IPCA
        
        adjusted_val, inflation_rate, eff_start, eff_end = adjust_value_by_inflation(
            sim_valor, data_origem, data_destino, df_ipca_total
        )
        
        # Busca salários mínimos das duas datas correspondentes
        wage_origem_row = df_wage_total[df_wage_total["data"] == data_origem]
        wage_origem = wage_origem_row.iloc[0]["salario_minimo"] if not wage_origem_row.empty else 0.0
        
        wage_destino_row = df_wage_total[df_wage_total["data"] == data_destino]
        wage_destino = wage_destino_row.iloc[0]["salario_minimo"] if not wage_destino_row.empty else latest_wage
        
        # Proporções de salário mínimo
        prop_wage_origem = sim_valor / wage_origem if wage_origem > 0 else 0.0
        prop_wage_destino = adjusted_val / wage_destino if wage_destino > 0 else 0.0
        
        # Renderização premium dos resultados
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.markdown(
                f"""
                <div style="background-color:rgba(255, 255, 255, 0.02); padding:15px; border-radius:10px; border:1px solid rgba(255,255,255,0.05); text-align:center;">
                    <span style="font-size:12px; color:#A9A9A9; text-transform:uppercase;">Valor Corrigido Hoje</span>
                    <h2 style="color:#00FA9A; font-size:32px; font-weight:800; margin:5px 0;">{format_currency_brl(adjusted_val)}</h2>
                    <span style="font-size:11px; color:#8fa0c2;">Poder de compra em {format_date(eff_end)}</span>
                </div>
                """, unsafe_allow_html=True
            )
        with col_res2:
            st.markdown(
                f"""
                <div style="background-color:rgba(255, 255, 255, 0.02); padding:15px; border-radius:10px; border:1px solid rgba(255,255,255,0.05); text-align:center;">
                    <span style="font-size:12px; color:#A9A9A9; text-transform:uppercase;">Inflação Acumulada</span>
                    <h2 style="color:#FF8C00; font-size:32px; font-weight:800; margin:5px 0;">{format_percent(inflation_rate, is_fraction=True)}</h2>
                    <span style="font-size:11px; color:#8fa0c2;">IPCA no período selecionado</span>
                </div>
                """, unsafe_allow_html=True
            )
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Cartão de equivalente em salário mínimo (curiosidade do poder de compra real)
        st.markdown(
            f"""
            <div style="background: rgba(30, 144, 255, 0.05); border: 1px solid rgba(30, 144, 255, 0.15); border-radius:10px; padding:20px;">
                <h4 style="margin:0; color:#1E90FF;">🕵️ Comparação com o Salário Mínimo de cada Época</h4>
                <p style="margin:8px 0 0 0; font-size:14px; color: var(--text-color);">
                    Em <strong>{format_date(eff_start)}</strong>, o valor original of <strong>{format_currency_brl(sim_valor)}</strong> correspondia a 
                    <strong>{prop_wage_origem:.2f} salários mínimos</strong> vigentes da época (que era de {format_currency_brl(wage_origem)}).
                </p>
                <p style="margin:5px 0 0 0; font-size:14px; color: var(--text-color);">
                    Hoje, o valor corrigido de <strong>{format_currency_brl(adjusted_val)}</strong> corresponde a 
                    <strong>{prop_wage_destino:.2f} salários mínimos</strong> atuais (que é de {format_currency_brl(wage_destino)}).
                </p>
            </div>
            """, unsafe_allow_html=True
        )

# -------------------------------- ABA 6: HISTÓRICO & CORRELAÇÕES --------------------------------
with tab6:
    col_corr1, col_corr2 = st.columns([1, 2])
    
    with col_corr1:
        st.markdown("### 🏛️ Mandatos Presidenciais e a Economia")
        st.markdown(
            "Diferentes mandatos presidenciais e governos enfrentaram distintos cenários inflacionários, "
            "regimes de câmbio e taxas de juros. "
            "A tabela ao lado consolida as principais estatísticas macroeconômicas calculadas e agregadas "
            "por mandato presidencial desde a estabilização econômica de 1995. "
            "Isso permite avaliar quais períodos entregaram ganhos reais de poder de compra acima da inflação."
        )
        
        # Correlação de Pearson calculada
        corrs = calculate_correlations(df_dolar_total, df_selic_total, df_ipca_total)
        
        st.markdown("#### 📊 Correlação Estatística de Pearson (Histórico)")
        st.markdown(
            f"""
            * **Dólar vs. Taxa SELIC:** <strong style='color:#00FFFF;'>{corrs['dolar_selic']:.2f}</strong>
            * **Dólar vs. IPCA Mensal:** <strong style='color:#00FFFF;'>{corrs['dolar_ipca']:.2f}</strong>
            * **SELIC vs. IPCA Mensal:** <strong style='color:#00FFFF;'>{corrs['selic_ipca']:.2f}</strong>
            
            <em>* Valores próximos de 1 indicam correlação positiva perfeita; próximos de -1, correlação negativa perfeita; e próximos de 0 indicam ausência de relação linear.</em>
            """
        )
        
    with col_corr2:
        st.markdown("#### 📈 Painel Econômico Consolidade por Mandatos (FHC a Lula 3)")
        
        # Gera e formata a tabela agrupada por mandatos presidenciais
        df_presidency = get_presidency_summaries(df_dolar_total, df_selic_total, df_ipca_total, df_wage_total)
        
        # Cria uma cópia formatada para visualização estética
        df_presidency_formatted = df_presidency.copy()
        df_presidency_formatted["Dólar Médio (R$)"] = df_presidency_formatted["Dólar Médio (R$)"].map(lambda x: f"R$ {x:.2f}")
        df_presidency_formatted["SELIC Média (% a.a.)"] = df_presidency_formatted["SELIC Média (% a.a.)"].map(lambda x: f"{x:.2f}%")
        df_presidency_formatted["IPCA Acumulado"] = df_presidency_formatted["IPCA Acumulado"].map(lambda x: f"{x*100:,.1f}%")
        df_presidency_formatted["Aumento Salarial Nominal"] = df_presidency_formatted["Aumento Salarial Nominal"].map(lambda x: f"{x*100:,.1f}%")
        df_presidency_formatted["Aumento Salarial Real (Acima da Inflação)"] = df_presidency_formatted["Aumento Salarial Real (Acima da Inflação)"].map(
            lambda x: f"<span style='color:{'#00FA9A' if x >= 0 else '#FF6347'}'>{x*100:+.1f}%</span>"
        )
        
        # Exibe como tabela HTML interativa e premium para poder exibir cores/HTML customizado
        st.write(df_presidency_formatted.to_html(escape=False, index=False), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption(
            "Nota: A inflação acumulada de cada mandato é calculada dividindo o número-índice do último mês do mandato "
            "pelo número-índice do mês anterior ao início do mandato. O aumento real do salário mínimo representa o ganho nominal de poder aquisitivo deflacionado pelo IPCA do mesmo período."
        )
