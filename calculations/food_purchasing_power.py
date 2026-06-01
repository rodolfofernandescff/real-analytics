import logging
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

def calculate_food_purchasing_power(
    df_wage: pd.DataFrame, 
    df_food: pd.DataFrame, 
    basket_baseline_today: float = 800.00
) -> pd.DataFrame:
    """
    Combina o salário mínimo com o IPCA de alimentos para estimar o preço histórico 
    da cesta básica e calcular o poder de compra alimentar (Cestas Básicas por salário).
    
    Fórmulas:
        Preço_Cesta_t = Cesta_Hoje * (Índice_Alimentar_t / Índice_Alimentar_Hoje)
        Cestas_por_Salário_t = Salário_Mínimo_Nominal_t / Preço_Cesta_t
        
    Parâmetros:
        df_wage (pd.DataFrame): Colunas ['data', 'salario_minimo'].
        df_food (pd.DataFrame): Colunas ['data', 'ipca_alimento', 'ipca_alimento_indice'].
        basket_baseline_today (float): Custo de referência da cesta básica hoje (Padrão: R$ 800,00).
        
    Retorna:
        pd.DataFrame: DataFrame alinhado contendo:
            ['data', 'salario_nominal', 'ipca_alimento', 'ipca_alimento_indice', 'cesta_preco', 'cestas_por_salario']
    """
    if df_wage.empty or df_food.empty:
        logger.warning("DataFrames vazios fornecidos para o cálculo do poder de compra alimentar.")
        return pd.DataFrame()

    # 1. Faz o merge de salário e inflação alimentar
    df_merged = pd.merge(
        df_wage.rename(columns={"salario_minimo": "salario_nominal"}),
        df_food,
        on="data",
        how="inner"
    )
    
    if df_merged.empty:
        logger.warning("Nenhuma interseção de datas encontrada para salário e inflação alimentar.")
        return pd.DataFrame()

    # Encontra o último índice de inflação alimentar disponível (Hoje)
    latest_row = df_merged.loc[df_merged["data"].idxmax()]
    latest_food_index = latest_row["ipca_alimento_indice"]
    latest_date = latest_row["data"]
    
    logger.info(f"Gerando proxy de Cesta Básica deflacionando R$ {basket_baseline_today:.2f} a partir de {latest_date.strftime('%Y-%m')}")
    
    # 2. Deflaciona o preço da cesta básica de hoje para construir a série histórica
    df_merged["cesta_preco"] = basket_baseline_today * (df_merged["ipca_alimento_indice"] / latest_food_index)
    
    # 3. Calcula a quantidade equivalente de Cestas Básicas compradas com um salário mínimo nominal
    df_merged["cestas_por_salario"] = df_merged["salario_nominal"] / df_merged["cesta_preco"]
    
    df_merged = df_merged.sort_values("data").reset_index(drop=True)
    return df_merged[[
        "data", "salario_nominal", "ipca_alimento", "ipca_alimento_indice", "cesta_preco", "cestas_por_salario"
    ]]
