import logging
from datetime import datetime
import pandas as pd
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

def _get_nearest_ipca_row(df_ipca: pd.DataFrame, target_date: datetime) -> pd.Series:
    """
    Retorna a linha do IPCA mais próxima da data informada (baseado em ano e mês).
    """
    df_temp = df_ipca.copy()
    # Diferença absoluta em dias
    df_temp["diff"] = (df_temp["data"] - target_date).abs()
    closest_row = df_temp.loc[df_temp["diff"].idxmin()]
    return closest_row

def calculate_accumulated_inflation(df_ipca: pd.DataFrame, start_date: datetime, end_date: datetime) -> float:
    """
    Calcula a inflação acumulada (%) entre duas datas com base no Número-Índice do IPCA.
    
    Fórmula: (Índice_Fim / Índice_Início) - 1
    
    Parâmetros:
        df_ipca (pd.DataFrame): DataFrame retornado pelo serviço ibge.py.
        start_date (datetime): Data de início do período.
        end_date (datetime): Data de fim do período.
        
    Retorna:
        float: Taxa de inflação acumulada (ex: 0.155 = 15.5%).
    """
    if df_ipca.empty:
        logger.warning("DataFrame do IPCA está vazio. Retornando inflação acumulada = 0.")
        return 0.0

    row_start = _get_nearest_ipca_row(df_ipca, start_date)
    row_end = _get_nearest_ipca_row(df_ipca, end_date)
    
    idx_start = row_start["ipca_indice"]
    idx_end = row_end["ipca_indice"]
    
    if idx_start == 0 or pd.isna(idx_start) or pd.isna(idx_end):
        logger.error("Índice de inflação inválido (zero ou NaN) detectado no cálculo.")
        return 0.0
        
    accumulated = (idx_end / idx_start) - 1
    logger.info(f"Inflação acumulada de {row_start['data'].strftime('%Y-%m')} a {row_end['data'].strftime('%Y-%m')}: {accumulated * 100:.2f}%")
    return float(accumulated)

def adjust_value_by_inflation(
    value: float, 
    start_date: datetime, 
    end_date: datetime, 
    df_ipca: pd.DataFrame
) -> Tuple[float, float, datetime, datetime]:
    """
    Ajusta um valor nominal de uma data passada para o poder de compra de uma data futura.
    
    Parâmetros:
        value (float): O valor nominal original.
        start_date (datetime): A data original do valor.
        end_date (datetime): A data alvo para atualização.
        df_ipca (pd.DataFrame): DataFrame de IPCA.
        
    Retorna:
        Tuple[float, float, datetime, datetime]: 
            - O valor corrigido final.
            - A taxa acumulada de inflação aplicada.
            - A data efetiva de início usada na correção.
            - A data efetiva de fim usada na correção.
    """
    if df_ipca.empty:
        return value, 0.0, start_date, end_date

    row_start = _get_nearest_ipca_row(df_ipca, start_date)
    row_end = _get_nearest_ipca_row(df_ipca, end_date)
    
    idx_start = row_start["ipca_indice"]
    idx_end = row_end["ipca_indice"]
    
    inflation_rate = (idx_end / idx_start) - 1
    adjusted_value = value * (idx_end / idx_start)
    
    return float(adjusted_value), float(inflation_rate), row_start["data"], row_end["data"]
