import logging
import pandas as pd
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

def calculate_real_minimum_wage(
    df_wage: pd.DataFrame, 
    df_ipca: pd.DataFrame, 
    base_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Combina a série histórica do salário mínimo com o IPCA e calcula o Salário Mínimo Real (deflacionado).
    
    Fórmula do Salário Real (em termos do poder de compra da Data Base):
        Salário_Real = Salário_Nominal * (Índice_IPCA_DataBase / Índice_IPCA_Mês)
        
    Parâmetros:
        df_wage (pd.DataFrame): Colunas ['data', 'salario_minimo'].
        df_ipca (pd.DataFrame): Colunas ['data', 'ipca_indice', 'ipca_mensal'].
        base_date (datetime, opcional): Data base para o poder de compra. 
                                        Se omitido, usa a última data disponível no IPCA (Reais de Hoje).
                                        
    Retorna:
        pd.DataFrame: DataFrame combinado com colunas:
            ['data', 'salario_nominal', 'ipca_indice', 'ipca_mensal', 'salario_real', 'poder_compra_index']
    """
    if df_wage.empty or df_ipca.empty:
        logger.warning("DataFrames vazios fornecidos para cálculo do salário real.")
        return pd.DataFrame()

    # 1. Alinha as duas séries mensais por data
    # Fazemos merge interno para garantir que temos ambos os indicadores para as datas
    df_merged = pd.merge(
        df_wage.rename(columns={"salario_minimo": "salario_nominal"}),
        df_ipca,
        on="data",
        how="inner"
    )
    
    if df_merged.empty:
        logger.warning("Nenhuma interseção de datas encontrada entre salário mínimo e IPCA.")
        return pd.DataFrame()
        
    # 2. Define o IPCA de referência para a Data Base (deflacionamento)
    if base_date is None:
        # Padrão: Usa a data mais recente disponível
        latest_row = df_merged.loc[df_merged["data"].idxmax()]
        ref_date = latest_row["data"]
        ref_ipca = latest_row["ipca_indice"]
        logger.info(f"Usando IPCA mais recente ({ref_date.strftime('%Y-%m')}: {ref_ipca:.2f}) como base de deflacionamento.")
    else:
        # Busca a linha mais próxima da base_date fornecida
        df_temp = df_merged.copy()
        df_temp["diff"] = (df_temp["data"] - base_date).abs()
        ref_row = df_temp.loc[df_temp["diff"].idxmin()]
        ref_date = ref_row["data"]
        ref_ipca = ref_row["ipca_indice"]
        logger.info(f"Usando IPCA de {ref_date.strftime('%Y-%m')} ({ref_ipca:.2f}) como base de deflacionamento.")

    # 3. Calcula o salário real (ajustado ao poder de compra da data base)
    df_merged["salario_real"] = df_merged["salario_nominal"] * (ref_ipca / df_merged["ipca_indice"])
    
    # 4. Calcula o Índice de Poder de Compra (Base Plano Real - Julho de 1994 = 100)
    # Procuramos o salário real de Julho/1994 para servir de base 100 do índice
    df_jul_1994 = df_merged[df_merged["data"] == datetime(1994, 7, 1)]
    
    if not df_jul_1994.empty:
        real_wage_jul_1994 = df_jul_1994.iloc[0]["salario_real"]
        df_merged["poder_compra_index"] = (df_merged["salario_real"] / real_wage_jul_1994) * 100
    else:
        # Se julho/1994 não estiver na série (por ex, se filtrado), usa a primeira linha disponível como base 100
        first_real_wage = df_merged.iloc[0]["salario_real"]
        df_merged["poder_compra_index"] = (df_merged["salario_real"] / first_real_wage) * 100
        
    # Ordena os dados finais
    df_merged = df_merged.sort_values("data").reset_index(drop=True)
    
    return df_merged[[
        "data", "salario_nominal", "ipca_indice", "ipca_mensal", "salario_real", "poder_compra_index"
    ]]
