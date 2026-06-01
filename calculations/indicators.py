import logging
import pandas as pd
from datetime import datetime
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

def resample_to_monthly_average(df_daily: pd.DataFrame, date_col: str, value_col: str) -> pd.DataFrame:
    """
    Reamostra um DataFrame diário para a média mensal.
    Ajusta o índice temporal para o primeiro dia de cada mês (MS).
    """
    if df_daily.empty:
        return pd.DataFrame(columns=["data", value_col])
        
    df = df_daily.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.set_index(date_col)
    
    # Reamostra pela média mensal e redefine a data para o início do mês (ex: 2026-06-01)
    df_monthly = df[[value_col]].resample("MS").mean().reset_index()
    return df_monthly

def calculate_correlations(
    df_dolar: pd.DataFrame, 
    df_selic: pd.DataFrame, 
    df_ipca: pd.DataFrame
) -> Dict[str, float]:
    """
    Calcula as correlações de Pearson entre Dólar, SELIC e IPCA (mensalizados).
    """
    # 1. Mensaliza Dólar e SELIC
    df_dol_m = resample_to_monthly_average(df_dolar, "data", "dolar")
    df_sel_m = resample_to_monthly_average(df_selic, "data", "selic")
    
    # 2. Faz o merge de tudo
    df_merged = pd.merge(df_dol_m, df_sel_m, on="data", how="inner")
    df_merged = pd.merge(df_merged, df_ipca, on="data", how="inner")
    
    if len(df_merged) < 5:
        logger.warning("Poucos dados para calcular correlações estatísticas significativas.")
        return {"dolar_selic": 0.0, "dolar_ipca": 0.0, "selic_ipca": 0.0}
        
    # 3. Calcula correlação de Pearson
    corr_dolar_selic = df_merged["dolar"].corr(df_merged["selic"])
    corr_dolar_ipca = df_merged["dolar"].corr(df_merged["ipca_mensal"])
    corr_selic_ipca = df_merged["selic"].corr(df_merged["ipca_mensal"])
    
    return {
        "dolar_selic": float(corr_dolar_selic),
        "dolar_ipca": float(corr_dolar_ipca),
        "selic_ipca": float(corr_selic_ipca)
    }

def get_presidency_summaries(
    df_dolar: pd.DataFrame,
    df_selic: pd.DataFrame,
    df_ipca: pd.DataFrame,
    df_wage: pd.DataFrame
) -> pd.DataFrame:
    """
    Gera uma tabela resumida dos indicadores macroeconômicos agrupada pelos mandatos presidenciais desde 1995.
    """
    # 1. Prepara dados mensais unificados
    df_dol_m = resample_to_monthly_average(df_dolar, "data", "dolar")
    df_sel_m = resample_to_monthly_average(df_selic, "data", "selic")
    
    # Alinha as séries econômicas
    df_econ = pd.merge(df_dol_m, df_sel_m, on="data", how="outer")
    df_econ = pd.merge(df_econ, df_ipca, on="data", how="outer")
    df_econ = pd.merge(df_econ, df_wage.rename(columns={"salario_minimo": "salario_nominal"}), on="data", how="outer")
    
    # Filtra dados a partir de 1995 (FHC)
    df_econ = df_econ[df_econ["data"] >= datetime(1995, 1, 1)].sort_values("data").reset_index(drop=True)
    
    # Definição dos Mandatos Presidenciais
    mandatos = [
        {"nome": "FHC (1995-2002)", "inicio": datetime(1995, 1, 1), "fim": datetime(2002, 12, 31)},
        {"nome": "Lula 1 & 2 (2003-2010)", "inicio": datetime(2003, 1, 1), "fim": datetime(2010, 12, 31)},
        {"nome": "Dilma Rousseff (2011-2016)", "inicio": datetime(2011, 1, 1), "fim": datetime(2016, 8, 31)},
        {"nome": "Michel Temer (2016-2018)", "inicio": datetime(2016, 9, 1), "fim": datetime(2018, 12, 31)},
        {"nome": "Jair Bolsonaro (2019-2022)", "inicio": datetime(2019, 1, 1), "fim": datetime(2022, 12, 31)},
        {"nome": "Lula 3 (2023-Presente)", "inicio": datetime(2023, 1, 1), "fim": datetime.now()}
    ]
    
    resumo_rows = []
    
    for m in mandatos:
        df_per = df_econ[(df_econ["data"] >= m["inicio"]) & (df_econ["data"] <= m["fim"])]
        if df_per.empty:
            continue
            
        # Médias
        avg_dolar = df_per["dolar"].mean()
        avg_selic = df_per["selic"].mean()
        
        # Inflação acumulada no período (usando Número-Índice)
        df_per_ipca = df_per.dropna(subset=["ipca_indice"])
        if not df_per_ipca.empty:
            idx_start = df_per_ipca.iloc[0]["ipca_indice"]
            idx_end = df_per_ipca.iloc[-1]["ipca_indice"]
            ipca_acumulado = (idx_end / idx_start) - 1
        else:
            ipca_acumulado = 0.0
            
        # Aumento do Salário Mínimo Nominal e Real
        df_per_wage = df_per.dropna(subset=["salario_nominal"])
        if not df_per_wage.empty and not df_per_ipca.empty:
            # Nominal
            wage_start = df_per_wage.iloc[0]["salario_nominal"]
            wage_end = df_per_wage.iloc[-1]["salario_nominal"]
            crescimento_nominal = (wage_end / wage_start) - 1
            
            # Real (Salários deflacionados para o fim do mandato)
            # Traz o salário inicial para o poder de compra do fim do mandato
            idx_start_w = df_per_ipca.iloc[0]["ipca_indice"]
            idx_end_w = df_per_ipca.iloc[-1]["ipca_indice"]
            
            wage_start_real = wage_start * (idx_end_w / idx_start_w)
            crescimento_real = (wage_end / wage_start_real) - 1
        else:
            crescimento_nominal = 0.0
            crescimento_real = 0.0
            
        resumo_rows.append({
            "Período": m["nome"],
            "Dólar Médio (R$)": avg_dolar,
            "SELIC Média (% a.a.)": avg_selic,
            "IPCA Acumulado": ipca_acumulado,
            "Aumento Salarial Nominal": crescimento_nominal,
            "Aumento Salarial Real (Acima da Inflação)": crescimento_real
        })
        
    return pd.DataFrame(resumo_rows)
