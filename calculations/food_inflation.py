import logging
from datetime import datetime
import pandas as pd
from typing import Tuple

logger = logging.getLogger(__name__)

def _get_nearest_food_ipca_row(df_food: pd.DataFrame, target_date: datetime) -> pd.Series:
    """
    Retorna a linha do IPCA Alimentar mais próxima da data informada.
    """
    df_temp = df_food.copy()
    df_temp["diff"] = (df_temp["data"] - target_date).abs()
    closest_row = df_temp.loc[df_temp["diff"].idxmin()]
    return closest_row

def adjust_food_value_by_inflation(
    value: float, 
    start_date: datetime, 
    end_date: datetime, 
    df_food: pd.DataFrame
) -> Tuple[float, float, datetime, datetime]:
    """
    Ajusta um valor nominal original de uma data passada para o poder de compra de alimentos de uma data futura.
    
    Parâmetros:
        value (float): O valor nominal original (ex: R$ 500,00).
        start_date (datetime): Data de origem.
        end_date (datetime): Data alvo para atualização.
        df_food (pd.DataFrame): DataFrame de inflação alimentar contendo ['data', 'ipca_alimento_indice'].
        
    Retorna:
        Tuple[float, float, datetime, datetime]: 
            - O valor corrigido de alimentação.
            - A taxa acumulada de inflação de alimentos aplicada.
            - A data efetiva de início usada.
            - A data efetiva de fim usada.
    """
    if df_food.empty:
        return value, 0.0, start_date, end_date

    row_start = _get_nearest_food_ipca_row(df_food, start_date)
    row_end = _get_nearest_food_ipca_row(df_food, end_date)
    
    idx_start = row_start["ipca_alimento_indice"]
    idx_end = row_end["ipca_alimento_indice"]
    
    if idx_start == 0 or pd.isna(idx_start) or pd.isna(idx_end):
        logger.error("Índice alimentar inválido (zero ou NaN) detectado no cálculo.")
        return value, 0.0, start_date, end_date
        
    food_inflation_rate = (idx_end / idx_start) - 1
    adjusted_value = value * (idx_end / idx_start)
    
    return float(adjusted_value), float(food_inflation_rate), row_start["data"], row_end["data"]
