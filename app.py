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

# Sistema visual: "Jornal do Real" — verde floresta + dourado + tipografia editorial
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Fraunces:ital,opsz,wght@0,9..144,700;0,9..144,900;1,9..144,400&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&family=IBM+Plex+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>

        @keyframes pulse-dot {
            0%, 100% { opacity: 1;   transform: scale(1.0); }
            50%       { opacity: 0.4; transform: scale(0.7); }
        }

        @keyframes fade-in-up {
            from { opacity: 0; transform: translateY(6px); }
            to   { opacity: 1; transform: translateY(0);   }
        }

        :root {
            --bg-deep:      #091710;
            --bg-card:      #0F2218;
            --bg-surface:   #162C1E;
            --border-sub:   rgba(244, 193, 0, 0.10);
            --border-mid:   rgba(244, 193, 0, 0.28);
            --gold:         #F4C100;
            --teal:         #00C48C;
            --red:          #E05252;
            --amber:        #FF8C00;
            --cream:        #EDE8D8;
            --muted:        #7A9E85;
            --dim:          #435E4A;
        }

        /* Fundo global + previne scroll horizontal */
        html, body {
            background-color: var(--bg-deep) !important;
            overflow-x: hidden !important;
        }
        .stApp, [data-testid="stAppViewContainer"] {
            background-color: var(--bg-deep) !important;
            overflow-x: hidden !important;
        }

        /* Tipografia global */
        html, body, [class*="css"], .stText, .stMarkdown, p, span, li, label {
            font-family: 'DM Sans', sans-serif !important;
            color: var(--cream);
        }

        /* Só muda a fonte dos headings — NÃO força cor (inline styles das seções controlam) */
        h1, h2, h3, h4 {
            font-family: 'Fraunces', serif !important;
        }
        /* Headings do Streamlit nativo ficam cream */
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
            color: #EDE8D8 !important;
        }

        /* ═══ SIDEBAR — Refatoração completa ═══ */

        /* Sidebar FIXA — sempre visível, sem colapso em nenhuma condição */
        section[data-testid="stSidebar"] {
            background-color: #060E09 !important;
            border-right: 1px solid var(--border-sub) !important;
            overflow-x: hidden !important;
            box-sizing: border-box !important;
            /* Bloqueia qualquer tentativa do Streamlit de colapsar */
            display: block !important;
            visibility: visible !important;
            transform: none !important;
            min-width: 244px !important;
            flex-shrink: 0 !important;
            transition: none !important;
            position: relative !important;
        }
        /* Quando Streamlit injeta transform inline ou aria-expanded="false" */
        section[data-testid="stSidebar"][aria-expanded="false"],
        section[data-testid="stSidebar"][style*="transform"],
        section[data-testid="stSidebar"][style*="width: 0"] {
            transform: none !important;
            min-width: 244px !important;
            width: 244px !important;
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
        }

        /* Área de conteúdo interna */
        section[data-testid="stSidebar"] > div,
        section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            overflow-x: hidden !important;
            box-sizing: border-box !important;
            width: 100% !important;
        }

        /* Block container da sidebar — padding controlado */
        section[data-testid="stSidebar"] .block-container {
            padding: 1.25rem 0.875rem !important;
            overflow-x: hidden !important;
            box-sizing: border-box !important;
            max-width: 100% !important;
        }

        /* Box-sizing universal na sidebar — previne overflow */
        section[data-testid="stSidebar"] * {
            box-sizing: border-box !important;
        }

        /* Colunas internas (date range customizado) — fix do scroll horizontal */
        section[data-testid="stSidebar"] [data-testid="column"] {
            min-width: 0 !important;
            overflow: hidden !important;
            flex-shrink: 1 !important;
        }

        /* Date inputs compactos dentro das colunas */
        section[data-testid="stSidebar"] [data-testid="stDateInput"],
        section[data-testid="stSidebar"] [data-testid="stDateInput"] > div {
            width: 100% !important;
        }
        section[data-testid="stSidebar"] [data-testid="stDateInput"] input {
            font-size: 12px !important;
            padding: 4px 6px !important;
        }

        /* Tipografia da sidebar */
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] li {
            color: var(--muted) !important;
            font-size: 13px !important;
            line-height: 1.55 !important;
        }
        section[data-testid="stSidebar"] a { color: var(--gold) !important; }
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: var(--cream) !important;
            font-size: 14px !important;
        }

        /* Scrollbar discreta (apenas vertical) */
        section[data-testid="stSidebar"]::-webkit-scrollbar { width: 3px; }
        section[data-testid="stSidebar"]::-webkit-scrollbar-track { background: transparent; }
        section[data-testid="stSidebar"]::-webkit-scrollbar-thumb {
            background: rgba(244,193,0,0.15); border-radius: 2px;
        }

        /* Sidebar sempre visível — header e todos os toggles de colapso ocultos */
        header,
        [data-testid="stHeader"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        [data-testid="collapsedControl"] {
            display: none !important;
        }

        /* Botão de colapso — cobertura total de seletores por versão do Streamlit
           Inclui kind="icon" que aparece no hover e não estava coberto */
        button[data-testid="stSidebarCollapseButton"],
        [data-testid="stSidebarCollapseButton"],
        section[data-testid="stSidebar"] button[kind="header"],
        section[data-testid="stSidebar"] button[kind="icon"],
        section[data-testid="stSidebar"]:hover button[data-testid="stSidebarCollapseButton"],
        section[data-testid="stSidebar"]:hover button[kind="header"],
        section[data-testid="stSidebar"]:hover button[kind="icon"],
        section[data-testid="stSidebar"] button:has(.material-symbols-rounded),
        section[data-testid="stSidebar"]:hover button:has(.material-symbols-rounded) {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
            position: absolute !important;
            width: 1px !important;
            height: 1px !important;
            overflow: hidden !important;
            clip-path: inset(50%) !important;
        }

        /* Remove espaço reservado ao header */
        .block-container {
            padding-top: 1rem !important;
        }

        /* Cards de métricas — estilo editorial com topo dourado */
        div[data-testid="metric-container"] {
            background-color: var(--bg-card) !important;
            border: 1px solid var(--border-sub) !important;
            border-top: 2px solid var(--gold) !important;
            border-radius: 0 0 6px 6px !important;
            padding: 14px 18px !important;
            transition: border-color 0.2s !important;
        }
        div[data-testid="metric-container"]:hover {
            border-left-color:   var(--border-mid) !important;
            border-right-color:  var(--border-mid) !important;
            border-bottom-color: var(--border-mid) !important;
        }
        div[data-testid="stMetricValue"] {
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: 22px !important;
            font-weight: 600 !important;
            color: var(--cream) !important;
        }
        [data-testid="stMetricLabel"] > div,
        [data-testid="stMetricLabel"] label {
            font-family: 'DM Sans', sans-serif !important;
            font-size: 10px !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.09em !important;
            color: var(--muted) !important;
        }
        [data-testid="stMetricDelta"] span {
            font-family: 'DM Sans', sans-serif !important;
            font-size: 11px !important;
        }

        /* Abas */
        .stTabs [data-baseweb="tab-list"] {
            background: transparent !important;
            border-bottom: 1px solid var(--border-sub) !important;
            gap: 2px !important;
        }
        .stTabs [data-baseweb="tab"] {
            background: transparent !important;
            color: var(--muted) !important;
            font-family: 'DM Sans', sans-serif !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            border-radius: 0 !important;
            padding: 10px 16px !important;
            border-bottom: 2px solid transparent !important;
        }
        .stTabs [aria-selected="true"] {
            color: var(--gold) !important;
            border-bottom-color: var(--gold) !important;
            background: transparent !important;
        }

        /* Botões */
        .stButton > button {
            background-color: var(--gold) !important;
            color: #091710 !important;
            border: none !important;
            border-radius: 4px !important;
            font-family: 'DM Sans', sans-serif !important;
            font-weight: 600 !important;
            font-size: 13px !important;
            letter-spacing: 0.02em !important;
            transition: background-color 0.15s !important;
        }
        .stButton > button:hover { background-color: #FFD800 !important; }

        /* Inputs */
        [data-baseweb="select"] > div,
        [data-testid="stNumberInput"] > div {
            background-color: var(--bg-surface) !important;
            border-color: var(--border-sub) !important;
            color: var(--cream) !important;
        }

        /* HR */
        hr { border-color: var(--border-sub) !important; }

        /* Container principal */
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
            padding-left: 2.5rem !important;
            padding-right: 2.5rem !important;
            max-width: 100% !important;
        }

        /* Caption / legenda */
        .stCaption, caption { color: var(--dim) !important; font-size: 11px !important; }

        /* Avisos */
        div[data-testid="stAlert"] {
            background-color: rgba(255, 140, 0, 0.06) !important;
            border-color: rgba(255, 140, 0, 0.30) !important;
        }

        /* Tabela presidencial */
        table { border-collapse: collapse !important; width: 100% !important;
                font-family: 'DM Sans', sans-serif !important; font-size: 13px !important; }
        table thead tr { background-color: var(--bg-surface) !important;
                         border-bottom: 1px solid var(--border-mid) !important; }
        table thead th { color: var(--muted) !important; font-size: 10px !important;
                         font-weight: 600 !important; text-transform: uppercase !important;
                         letter-spacing: 0.08em !important; padding: 10px 14px !important; }
        table tbody tr { border-bottom: 1px solid var(--border-sub) !important; }
        table tbody tr:hover { background-color: var(--bg-surface) !important; }
        table tbody td { color: var(--cream) !important; padding: 10px 14px !important; }

        /* ── Componentes customizados ── */

        /* Masthead */
        .masthead {
            border-bottom: 2px solid var(--gold);
            padding-bottom: 14px;
            margin-bottom: 22px;
        }
        .masthead-brand {
            font-family: 'Fraunces', serif !important;
            font-size: 40px !important;
            font-weight: 900 !important;
            color: var(--gold) !important;
            letter-spacing: -2px;
            line-height: 1;
            margin: 0;
        }
        .masthead-tagline {
            font-family: 'DM Sans', sans-serif !important;
            font-size: 11px !important;
            color: var(--muted) !important;
            margin: 5px 0 0 0;
            text-transform: uppercase;
            letter-spacing: 0.16em;
        }

        /* Eyebrow de seção */
        .eyebrow {
            font-family: 'DM Sans', sans-serif !important;
            font-size: 10px !important; font-weight: 600 !important;
            text-transform: uppercase !important; letter-spacing: 0.15em !important;
            color: var(--gold) !important; margin: 0 0 5px 0;
        }

        /* Box de insight macroeconômico */
        .insight-box {
            background: rgba(244, 193, 0, 0.03);
            border-left: 3px solid var(--gold);
            border-radius: 0 6px 6px 0;
            padding: 14px 18px; margin: 18px 0;
        }
        .insight-box h4 {
            font-family: 'DM Sans', sans-serif !important;
            font-size: 10px !important; font-weight: 600 !important;
            text-transform: uppercase !important; letter-spacing: 0.10em !important;
            color: var(--gold) !important; margin: 0 0 8px 0 !important;
        }
        .insight-box p { font-size: 14px !important; line-height: 1.65 !important;
                         color: var(--cream) !important; margin: 0 !important; }

        /* Box "Em palavras simples" para leigos */
        .simple-box {
            background: rgba(0, 196, 140, 0.04);
            border: 1px solid rgba(0, 196, 140, 0.18);
            border-radius: 6px; padding: 14px 18px; margin: 16px 0;
        }
        .simple-box-title {
            font-family: 'DM Sans', sans-serif !important;
            font-size: 10px !important; font-weight: 600 !important;
            text-transform: uppercase !important; letter-spacing: 0.12em !important;
            color: var(--teal) !important; display: block; margin: 0 0 8px 0;
        }
        .simple-box p { font-size: 14px !important; line-height: 1.65 !important;
                        color: var(--cream) !important; margin: 0 !important; }

        /* Highlight card (análise estatística) */
        .highlight-card {
            background: rgba(244, 193, 0, 0.03);
            border-left: 3px solid var(--gold);
            border-radius: 0 8px 8px 0;
            padding: 16px 20px; margin: 16px 0;
        }
        .highlight-card h4 {
            font-family: 'DM Sans', sans-serif !important;
            font-size: 10px !important; font-weight: 600 !important;
            text-transform: uppercase !important; letter-spacing: 0.10em !important;
            color: var(--gold) !important; margin: 0 0 10px 0 !important;
        }
        .highlight-card p,
        .highlight-card li,
        .highlight-card ul { font-size: 14px !important; line-height: 1.65 !important;
                             color: var(--cream) !important; }

        /* Cards de resultado dos simuladores */
        .result-card {
            background-color: var(--bg-surface);
            border: 1px solid var(--border-sub);
            border-radius: 6px; padding: 18px 20px; text-align: center;
        }
        .result-label {
            font-size: 10px; font-weight: 600; text-transform: uppercase;
            letter-spacing: 0.12em; color: var(--muted); display: block; margin: 0 0 10px 0;
        }
        .result-value {
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: 28px !important; font-weight: 600 !important;
            line-height: 1 !important; display: block; margin: 0 0 8px 0;
        }
        .result-sub { font-size: 11px !important; color: var(--muted) !important; display: block; }

        /* Caixa de comparação (simuladores) */
        .compare-box {
            background: rgba(30, 130, 255, 0.04);
            border: 1px solid rgba(30, 130, 255, 0.14);
            border-radius: 8px; padding: 18px 20px;
        }
        .compare-box h4 {
            font-family: 'DM Sans', sans-serif !important;
            font-size: 11px !important; font-weight: 600 !important;
            text-transform: uppercase !important; letter-spacing: 0.10em !important;
            color: #4A9EFF !important; margin: 0 0 10px 0 !important;
        }
        .compare-box p { font-size: 14px !important; line-height: 1.6 !important;
                         color: var(--cream) !important; margin: 5px 0 0 0 !important; }


        /* Responsividade — notebook e telas menores */
        @media (max-width: 1280px) {
            .block-container {
                padding-left: 1.5rem !important;
                padding-right: 1.5rem !important;
            }
        }
        @media (max-width: 900px) {
            .block-container {
                padding-left: 1rem !important;
                padding-right: 1rem !important;
                padding-top: 0.75rem !important;
            }
            div[data-testid="stMetricValue"] {
                font-size: 18px !important;
            }
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


# ----------------- MASTHEAD -----------------
st.markdown("""
<div style="border-bottom:1.5px solid #F4C100; padding:16px 0 14px 0; margin-bottom:28px; text-align:center; animation:fade-in-up 0.4s ease both; max-width:100%; overflow:hidden;">
<svg viewBox="0 0 820 72" xmlns="http://www.w3.org/2000/svg" style="display:block;margin:0 auto;width:100%;max-width:620px;height:auto;">
<defs>
<linearGradient id="titleGrad" x1="0%" y1="0%" x2="100%" y2="0%">
<stop offset="0%" stop-color="#F4C100"/>
<stop offset="40%" stop-color="#FFD84D"/>
<stop offset="100%" stop-color="#C8920A"/>
</linearGradient>
</defs>
<text x="410" y="58" text-anchor="middle" font-family="'Bebas Neue',Impact,sans-serif" font-size="64" fill="url(#titleGrad)" letter-spacing="10">REAL ANALYTICS</text>
</svg>
<div style="font-family:'DM Sans',system-ui,sans-serif; font-size:10px; font-weight:600; color:#7A9E85; text-transform:uppercase; letter-spacing:0.20em; margin:8px 0 10px 0;">Monitor histórico &nbsp;·&nbsp; Inflação &nbsp;·&nbsp; Câmbio &nbsp;·&nbsp; Poder de Compra &nbsp;·&nbsp; Plano Real (1994–Hoje)</div>
<div style="display:flex; align-items:center; justify-content:center; gap:20px; flex-wrap:wrap;">
<div style="display:flex; align-items:center; gap:6px;">
<span style="width:6px; height:6px; border-radius:50%; background:#00C48C; display:inline-block; animation:pulse-dot 2s ease-in-out infinite;"></span>
<span style="font-family:'DM Sans',system-ui,sans-serif; font-size:10px; color:#00C48C; font-weight:700; text-transform:uppercase; letter-spacing:0.10em;">Dados em tempo real</span>
</div>
<span style="color:#435E4A; font-size:12px;">·</span>
<div style="font-family:'IBM Plex Mono',monospace; font-size:10px; color:#435E4A;">BCB &nbsp;·&nbsp; IBGE &nbsp;·&nbsp; IPEA &nbsp;🇧🇷</div>
</div>
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
st.sidebar.markdown("### 🏛️ Fontes Oficiais")
st.sidebar.markdown(
    """
    * **Câmbio & SELIC**: [Banco Central](https://www.bcb.gov.br/) (SGS API)
    * **Inflação (IPCA)**: [IBGE](https://www.ibge.gov.br/) (SIDRA API)
    * **Salário Mínimo**: [IPEA](http://www.ipeadata.gov.br/) (IpeaData API)

    *Dados coletados diretamente das APIs governamentais em tempo real.*
    """
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📖 Glossário Rápido")
st.sidebar.markdown(
    """
    **IPCA**: Inflação oficial do Brasil, medida pelo IBGE. Acompanha o preço de uma cesta de produtos e serviços consumidos pelas famílias.

    **SELIC**: Taxa básica de juros da economia, definida pelo Banco Central (COPOM). É o "preço do dinheiro" no Brasil.

    **Dólar Comercial**: Cotação BRL/USD — quantos Reais são necessários para comprar 1 Dólar americano.

    **Poder de Compra**: Quanto seu dinheiro consegue adquirir de bens e serviços. Sobe quando o salário cresce acima da inflação.

    **Plano Real (1994)**: Programa econômico que criou a moeda Real e encerrou a hiperinflação no Brasil.

    **Deflação**: Queda geral nos preços — raro no Brasil, mas pode indicar retração econômica.
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


# ----------------- CARDS DE MÉTRICAS -----------------
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        label="💵 Dólar Comercial (Venda)",
        value=format_currency_brl(latest_dolar),   # taxa BRL/USD — já está em Reais
        delta=delta_dolar,
        delta_color="inverse"  # alta do dólar = Real desvalorizado
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
        delta="Meta CMN: 3,0%"
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
        delta=f"{(latest_pp_index - 100):+.1f}% vs. jul/1994",
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
    st.markdown('<p class="eyebrow">Câmbio & Política Monetária</p>', unsafe_allow_html=True)
    st.markdown("### Dólar vs. Taxa de Juros (SELIC)")
    st.markdown(
        "A SELIC é o principal instrumento do Banco Central para controlar a inflação e influenciar o câmbio. "
        "O gráfico abaixo mostra como as duas séries se relacionam desde a criação do Real:"
    )

    if not df_dolar.empty and not df_selic.empty:
        fig_ex = create_exchange_and_selic_chart(df_dolar, df_selic)
        st.plotly_chart(fig_ex, use_container_width=True)
    else:
        st.warning("Período sem dados disponíveis para Dólar ou SELIC.")

    st.markdown("""
        <div class="simple-box">
            <span class="simple-box-title">🧠 Em palavras simples</span>
            <p>
                Pense na SELIC como o "preço do dinheiro". Quando o Banco Central sobe os juros,
                pegar empréstimos fica mais caro — o consumo cai e a inflação desacelera.
                Juros altos também atraem investidores estrangeiros (que precisam comprar Reais para aplicar no Brasil),
                o que valoriza o Real e derruba o Dólar. Quando os juros caem, o oposto ocorre:
                o consumo aquece, mas o Real pode perder valor frente ao Dólar.
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="insight-box">
            <h4>💡 Insight Macroeconômico</h4>
            <p>
                Observe os ciclos: cortes agressivos na SELIC (como em 2020) costumam coincidir com
                forte alta do Dólar. Ciclos de aumento de juros, ao contrário, tendem a segurar o câmbio.
                Note também que a relação não é instantânea — o mercado antecipa as decisões do COPOM.
            </p>
        </div>
    """, unsafe_allow_html=True)

# -------------------------------- ABA 2: INFLAÇÃO & SALÁRIOS --------------------------------
with tab2:
    st.markdown('<p class="eyebrow">Inflação Oficial · IBGE</p>', unsafe_allow_html=True)
    st.markdown("### Evolução do IPCA — Variação Mensal e Nível de Preços")
    st.markdown(
        "O IPCA (Índice de Preços ao Consumidor Amplo) é a medida oficial da inflação brasileira, "
        "calculada pelo IBGE. As barras mostram a variação mês a mês; a linha azul mostra o nível "
        "acumulado de preços desde dezembro de 1993 (base = 100):"
    )
    if not df_ipca.empty:
        fig_inf = create_inflation_chart(df_ipca)
        st.plotly_chart(fig_inf, use_container_width=True)
    else:
        st.warning("Sem dados de IPCA no período escolhido.")

    st.markdown("""
        <div class="simple-box">
            <span class="simple-box-title">🧠 Em palavras simples</span>
            <p>
                O IPCA funciona como um "termômetro dos preços". Se o IPCA de um mês foi 0,5%,
                significa que os preços subiram, em média, 0,5% naquele mês.
                Em 12 meses, se o IPCA acumulou 5%, um produto que custava R$ 100 passou a custar R$ 105.
                A linha azul mostra que os preços no Brasil hoje são <strong>muito</strong> maiores do que em 1993 —
                evidência da inflação acumulada ao longo de décadas.
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<br><hr><br>", unsafe_allow_html=True)

    st.markdown('<p class="eyebrow">Salário Mínimo · Série Histórica</p>', unsafe_allow_html=True)
    st.markdown("### Salário Mínimo: Nominal vs. Real (Deflacionado)")
    st.markdown(
        "O salário nominal é o valor em Reais da carteira de trabalho. "
        "O salário real mostra esse valor <em>descontando a inflação</em> — ou seja, quanto ele "
        "realmente compra em valores de hoje. A diferença entre as duas curvas revela o ganho "
        "verdadeiro do trabalhador:", unsafe_allow_html=True
    )
    if not df_pp_filtered.empty:
        fig_wage = create_nominal_vs_real_salary_chart(df_pp_filtered)
        st.plotly_chart(fig_wage, use_container_width=True)
    else:
        st.warning("Sem dados de poder de compra no período escolhido.")

    st.markdown("""
        <div class="simple-box">
            <span class="simple-box-title">🧠 Em palavras simples</span>
            <p>
                Imagine que seu salário subiu 10% num ano, mas a inflação foi 8%.
                O seu ganho <em>real</em> foi de apenas ~2% — e é exatamente isso que o gráfico mostra.
                Quando a linha real cresce mais que a nominal, o trabalhador ganhou poder de compra de verdade.
                Quando ficam próximas, o aumento serviu apenas para "repor" a inflação.
            </p>
        </div>
    """, unsafe_allow_html=True)

# -------------------------------- ABA 3: PODER DE COMPRA --------------------------------
with tab3:
    st.markdown('<p class="eyebrow">Índice Base 100 · Julho de 1994</p>', unsafe_allow_html=True)
    st.markdown("### Evolução do Poder de Compra do Salário Mínimo")
    st.markdown(
        "O índice abaixo define **julho de 1994 (criação do Real) = 100**. "
        "Valores acima de 100 indicam ganho de poder aquisitivo real desde então — "
        "ou seja, o salário mínimo cresceu acima da inflação:"
    )

    if not df_pp_filtered.empty:
        fig_index = create_purchasing_power_index_chart(df_pp_filtered)
        st.plotly_chart(fig_index, use_container_width=True)
    else:
        st.warning("Sem dados disponíveis no período.")

    st.markdown("""
        <div class="simple-box">
            <span class="simple-box-title">🧠 Em palavras simples</span>
            <p>
                Imagine que em julho de 1994 o salário mínimo tinha "poder de compra = 100".
                Este índice mostra como esse poder evoluiu ao longo dos anos, já descontando toda a inflação do período.
                Se o índice está em 250, significa que o trabalhador de salário mínimo consegue comprar
                <strong>2,5 vezes mais</strong> do que conseguia em 1994 — esse é o ganho real,
                não o aumento do número na carteira.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Análise estatística com linguagem simples
    if not df_purchasing_power.empty:
        df_jul94 = df_wage_total[df_wage_total["data"] == datetime(1994, 7, 1)]
        if not df_jul94.empty:
            initial_wage_1994 = df_jul94.iloc[0]["salario_minimo"]
            row_94 = df_purchasing_power[df_purchasing_power["data"] == datetime(1994, 7, 1)]
            wage_94_real_today = row_94.iloc[0]["salario_real"] if not row_94.empty else 0.0

            st.markdown(f"""
                <div class="highlight-card">
                    <h4>📊 Raio-X do Poder de Compra Histórico</h4>
                    <ul>
                        <li><strong>Em julho de 1994:</strong> O salário mínimo nominal era de <strong>{format_currency_brl(initial_wage_1994)}</strong>.</li>
                        <li><strong>Inflação acumulada:</strong> Para comprar hoje as mesmas coisas que aquele salário comprava em 1994, seriam necessários <strong>{format_currency_brl(wage_94_real_today)}</strong>.</li>
                        <li><strong>Hoje:</strong> O salário mínimo vigente é de <strong>{format_currency_brl(latest_wage)}</strong> — acima do que a inflação exigiria. Isso representa um ganho real de <strong>{latest_pp_index - 100:.1f}%</strong> desde 1994, ou seja, o poder de compra é <strong>{latest_pp_index/100:.2f}×</strong> superior.</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)

# -------------------------------- ABA 4: ALIMENTAÇÃO E PODER DE COMPRA --------------------------------
with tab4:
    st.markdown('<p class="eyebrow">IPCA Alimentos e Bebidas · BCB Série 1635</p>', unsafe_allow_html=True)
    st.markdown("### Alimentação e Poder de Compra")
    st.markdown(
        "Alimentos têm o maior peso na cesta de consumo das famílias de baixa renda. "
        "Aqui comparamos a inflação do grupo <strong>Alimentação e Bebidas</strong> com o IPCA geral "
        "e medimos quantas cestas básicas o salário mínimo compra ao longo do tempo:", unsafe_allow_html=True
    )

    st.markdown("""
        <div class="simple-box">
            <span class="simple-box-title">🧠 Em palavras simples</span>
            <p>
                Quando a inflação de alimentos é maior que a geral, o prato de comida fica
                proporcionalmente mais caro do que outros gastos (roupa, transporte, lazer).
                Famílias que gastam a maior parte do salário em comida sentem esse impacto direto na mesa.
                O número de cestas básicas que o salário mínimo compra é uma medida prática disso.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
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
        st.markdown("#### Inflação de Alimentos vs. IPCA Geral")
        st.markdown(
            "Variação mensal do grupo **Alimentação e Bebidas** comparada ao IPCA geral. "
            "Alimentos sobem mais em períodos de seca, geadas ou choques de câmbio (importações):"
        )
        if not df_food.empty and not df_ipca.empty:
            fig_food_inf = create_food_inflation_comparison_chart(df_ipca, df_food)
            st.plotly_chart(fig_food_inf, use_container_width=True)
        else:
            st.warning("Período sem dados disponíveis para inflação de alimentos.")

    with tab_graphs_food[1]:
        st.markdown("#### Crescimento Anual do Salário Mínimo")
        st.markdown(
            "Aumento nominal do salário mínimo ano a ano (YoY — Year-over-Year). "
            "Para saber se o trabalhador ganhou de verdade, compare este percentual com o IPCA do mesmo ano:"
        )
        if not df_wage.empty:
            fig_wage_growth = create_minimum_wage_growth_chart(df_wage)
            st.plotly_chart(fig_wage_growth, use_container_width=True)
        else:
            st.warning("Sem dados disponíveis do salário mínimo.")

    with tab_graphs_food[2]:
        st.markdown("#### Cestas Básicas por Salário Mínimo")
        st.markdown(
            "Quantas cestas básicas o salário mínimo comprava em cada época? "
            "Proxy calculada deflacionando R$ 800,00 (custo atual estimado da cesta) pelo IPCA de Alimentos:"
        )
        if not df_food_power_filtered.empty:
            fig_food_pp = create_food_purchasing_power_chart(df_food_power_filtered)
            st.plotly_chart(fig_food_pp, use_container_width=True)
        else:
            st.warning("Sem dados suficientes para gerar o poder de compra alimentar.")
            
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 3. Simulador de Compras de Alimentos
    st.markdown('<hr style="margin:24px 0;">', unsafe_allow_html=True)
    st.markdown('<p class="eyebrow">Simulador · Inflação de Alimentos</p>', unsafe_allow_html=True)
    st.markdown("### Quanto custaria o mesmo carrinho hoje?")
    st.markdown(
        "Informe o valor de uma compra no passado para ver quanto equivaleria hoje, "
        "corrigido pela inflação específica do grupo **Alimentação e Bebidas**."
    )

    col_fsim1, col_fsim2 = st.columns([1, 2])

    with col_fsim1:
        st.markdown("##### Parâmetros")
        sim_food_val = st.number_input("Valor da compra (R$):", min_value=1.0, value=500.0, step=50.0, key="sim_food_val")

        df_food_all = df_food_total[df_food_total["data"] >= datetime(1994, 7, 1)].sort_values("data")
        lista_datas_f = df_food_all["data"].tolist()
        lista_datas_f_str = [dt.strftime("%m/%Y") for dt in lista_datas_f]

        sim_food_origem_str = st.selectbox(
            "Mês/ano da compra original:",
            options=lista_datas_f_str,
            index=192 if len(lista_datas_f_str) > 192 else 0,
            key="sim_food_origem"
        )

        st.text_input("Mês/ano de destino (hoje):", value=lista_datas_f_str[-1], disabled=True, key="sim_food_dest")

    with col_fsim2:
        st.markdown("##### Resultado")

        idx_f_origem = lista_datas_f_str.index(sim_food_origem_str)
        data_origem_f = lista_datas_f[idx_f_origem]
        data_destino_f = lista_datas_f[-1]

        adj_food_val, food_rate, eff_start_f, eff_end_f = adjust_food_value_by_inflation(
            sim_food_val, data_origem_f, data_destino_f, df_food_total
        )

        col_fres1, col_fres2 = st.columns(2)
        with col_fres1:
            st.markdown(f"""
                <div class="result-card">
                    <span class="result-label">Carrinho Corrigido</span>
                    <span class="result-value" style="color:#00C48C;">{format_currency_brl(adj_food_val)}</span>
                    <span class="result-sub">em {format_date(eff_end_f)}</span>
                </div>
            """, unsafe_allow_html=True)
        with col_fres2:
            st.markdown(f"""
                <div class="result-card">
                    <span class="result-label">Inflação Acumulada (Alimentos)</span>
                    <span class="result-value" style="color:#FF8C00;">{format_percent(food_rate, is_fraction=True)}</span>
                    <span class="result-sub">Alimentação & Bebidas no período</span>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""
            <div class="compare-box">
                <h4>🕵️ O que isso significa</h4>
                <p>
                    A compra de <strong>{format_currency_brl(sim_food_val)}</strong> realizada em
                    <strong>{format_date(eff_start_f)}</strong> exigiria hoje
                    <strong>{format_currency_brl(adj_food_val)}</strong> para comprar os mesmos itens —
                    um aumento de <strong>{format_percent(food_rate, is_fraction=True)}</strong>
                    pela inflação acumulada de alimentos no período.
                </p>
            </div>
        """, unsafe_allow_html=True)

# -------------------------------- ABA 5: SIMULADOR DE INFLAÇÃO --------------------------------
with tab5:
    st.markdown('<p class="eyebrow">Correção Monetária · IPCA Oficial</p>', unsafe_allow_html=True)
    st.markdown("### Simulador de Correção Monetária")
    st.markdown(
        "Informe um valor e o mês de referência. O simulador calcula quanto esse dinheiro "
        "deveria valer hoje para ter o mesmo poder de compra, usando o IPCA oficial."
    )

    st.markdown("""
        <div class="simple-box">
            <span class="simple-box-title">🧠 Em palavras simples</span>
            <p>
                Se você guardou R$ 1.000 em 1994 debaixo do colchão, hoje esse dinheiro compraria
                muito menos do que compraria antes — porque os preços subiram. Este simulador usa
                o IPCA oficial para mostrar quanto aquele valor precisaria ser hoje para comprar
                as mesmas coisas. É o mesmo índice usado para reajustar aluguéis, aposentadorias e contratos.
            </p>
        </div>
    """, unsafe_allow_html=True)

    col_sim1, col_sim2 = st.columns([1, 2])

    with col_sim1:
        st.markdown("##### Parâmetros")
        sim_valor = st.number_input("Valor original (R$):", min_value=1.0, value=100.0, step=50.0)

        df_ipca_all = df_ipca_total[df_ipca_total["data"] >= datetime(1994, 7, 1)].sort_values("data")
        lista_datas = df_ipca_all["data"].tolist()
        lista_datas_str = [dt.strftime("%m/%Y") for dt in lista_datas]

        sim_data_origem_str = st.selectbox(
            "Mês/ano do valor original:",
            options=lista_datas_str,
            index=0
        )

        st.text_input("Mês/ano de destino (atual):", value=lista_datas_str[-1], disabled=True)

    with col_sim2:
        st.markdown("##### Resultado")

        idx_origem = lista_datas_str.index(sim_data_origem_str)
        data_origem = lista_datas[idx_origem]
        data_destino = lista_datas[-1]

        adjusted_val, inflation_rate, eff_start, eff_end = adjust_value_by_inflation(
            sim_valor, data_origem, data_destino, df_ipca_total
        )

        wage_origem_row = df_wage_total[df_wage_total["data"] == data_origem]
        wage_origem = wage_origem_row.iloc[0]["salario_minimo"] if not wage_origem_row.empty else 0.0

        wage_destino_row = df_wage_total[df_wage_total["data"] == data_destino]
        wage_destino = wage_destino_row.iloc[0]["salario_minimo"] if not wage_destino_row.empty else latest_wage

        prop_wage_origem = sim_valor / wage_origem if wage_origem > 0 else 0.0
        prop_wage_destino = adjusted_val / wage_destino if wage_destino > 0 else 0.0

        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.markdown(f"""
                <div class="result-card">
                    <span class="result-label">Valor Corrigido Hoje</span>
                    <span class="result-value" style="color:#00C48C;">{format_currency_brl(adjusted_val)}</span>
                    <span class="result-sub">poder de compra em {format_date(eff_end)}</span>
                </div>
            """, unsafe_allow_html=True)
        with col_res2:
            st.markdown(f"""
                <div class="result-card">
                    <span class="result-label">IPCA Acumulado no Período</span>
                    <span class="result-value" style="color:#FF8C00;">{format_percent(inflation_rate, is_fraction=True)}</span>
                    <span class="result-sub">{format_date(eff_start)} → {format_date(eff_end)}</span>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(f"""
            <div class="compare-box">
                <h4>🕵️ Comparação com o Salário Mínimo de cada Época</h4>
                <p>
                    Em <strong>{format_date(eff_start)}</strong>, o valor de <strong>{format_currency_brl(sim_valor)}</strong>
                    correspondia a <strong>{prop_wage_origem:.2f} salário(s) mínimo(s)</strong>
                    da época (que era de {format_currency_brl(wage_origem)}).
                </p>
                <p>
                    Hoje, o valor corrigido de <strong>{format_currency_brl(adjusted_val)}</strong> representa
                    <strong>{prop_wage_destino:.2f} salário(s) mínimo(s)</strong> atuais
                    ({format_currency_brl(wage_destino)}).
                </p>
            </div>
        """, unsafe_allow_html=True)

# -------------------------------- ABA 6: HISTÓRICO & CORRELAÇÕES --------------------------------
with tab6:
    st.markdown('<p class="eyebrow">Análise Histórica · FHC a Lula 3</p>', unsafe_allow_html=True)
    st.markdown("### Economia por Mandato Presidencial")

    st.markdown("""
        <div class="simple-box">
            <span class="simple-box-title">🧠 Em palavras simples</span>
            <p>
                Esta tabela resume os principais indicadores econômicos de cada governo desde 1995.
                O <strong>aumento salarial real</strong> (última coluna) é a métrica mais importante:
                valores positivos significam que o salário mínimo cresceu <em>acima</em> da inflação
                — o trabalhador ficou mais rico de verdade. Valores negativos indicam perda de poder de compra.
            </p>
        </div>
    """, unsafe_allow_html=True)

    col_corr1, col_corr2 = st.columns([1, 2])

    with col_corr1:
        st.markdown('<p class="eyebrow">Correlação de Pearson · Série Completa</p>', unsafe_allow_html=True)
        st.markdown("#### Relação Estatística entre Indicadores")
        st.markdown(
            "Quanto cada par de indicadores se move junto ao longo do tempo? "
            "Coeficiente de Pearson calculado sobre a série histórica mensalizada:"
        )

        corrs = calculate_correlations(df_dolar_total, df_selic_total, df_ipca_total)

        def _corr_color(v: float) -> str:
            if v >= 0.5:   return "#00C48C"
            if v <= -0.5:  return "#E05252"
            return "#F4C100"

        st.markdown(f"""
            <div class="highlight-card">
                <h4>Correlações históricas</h4>
                <p>
                    <strong>Dólar × SELIC:</strong>
                    <span style="color:{_corr_color(corrs['dolar_selic'])}; font-family:'IBM Plex Mono',monospace; font-weight:600;">
                        {corrs['dolar_selic']:+.2f}
                    </span>
                </p>
                <p>
                    <strong>Dólar × IPCA Mensal:</strong>
                    <span style="color:{_corr_color(corrs['dolar_ipca'])}; font-family:'IBM Plex Mono',monospace; font-weight:600;">
                        {corrs['dolar_ipca']:+.2f}
                    </span>
                </p>
                <p>
                    <strong>SELIC × IPCA Mensal:</strong>
                    <span style="color:{_corr_color(corrs['selic_ipca'])}; font-family:'IBM Plex Mono',monospace; font-weight:600;">
                        {corrs['selic_ipca']:+.2f}
                    </span>
                </p>
                <p style="font-size:12px; color:#435E4A; margin-top:12px;">
                    +1 = movem juntos | −1 = movem ao contrário | 0 = sem relação linear
                </p>
            </div>
        """, unsafe_allow_html=True)

    with col_corr2:
        st.markdown('<p class="eyebrow">Painel Presidencial · 1995–Hoje</p>', unsafe_allow_html=True)
        st.markdown("#### Indicadores Econômicos por Mandato")

        df_presidency = get_presidency_summaries(df_dolar_total, df_selic_total, df_ipca_total, df_wage_total)

        df_presidency_formatted = df_presidency.copy()
        df_presidency_formatted["Dólar Médio (R$)"] = df_presidency_formatted["Dólar Médio (R$)"].map(lambda x: f"R$ {x:.2f}")
        df_presidency_formatted["SELIC Média (% a.a.)"] = df_presidency_formatted["SELIC Média (% a.a.)"].map(lambda x: f"{x:.2f}%")
        df_presidency_formatted["IPCA Acumulado"] = df_presidency_formatted["IPCA Acumulado"].map(lambda x: f"{x*100:,.1f}%")
        df_presidency_formatted["Aumento Salarial Nominal"] = df_presidency_formatted["Aumento Salarial Nominal"].map(lambda x: f"{x*100:,.1f}%")
        df_presidency_formatted["Aumento Salarial Real (Acima da Inflação)"] = df_presidency_formatted["Aumento Salarial Real (Acima da Inflação)"].map(
            lambda x: f"<span style='color:{'#00C48C' if x >= 0 else '#E05252'}; font-weight:600;'>{x*100:+.1f}%</span>"
        )

        st.write(df_presidency_formatted.to_html(escape=False, index=False), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption(
            "Inflação acumulada: número-índice IPCA do fim do mandato ÷ início do mandato. "
            "Aumento real: crescimento salarial nominal deflacionado pelo IPCA do mesmo período."
        )
