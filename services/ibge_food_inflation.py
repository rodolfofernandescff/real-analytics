import logging
from datetime import datetime, timedelta
import pandas as pd
import requests
from typing import Optional

# Configuração do Logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Constante da Série SGS do BCB (IPCA - Alimentação e Bebidas - Variação Mensal %)
SERIE_IPCA_ALIMENTACAO_MENSAL = 1635

def _chunk_dates(start_date: datetime, end_date: datetime, max_years: int = 3) -> list[tuple[datetime, datetime]]:
    """Divide um intervalo de datas em blocos menores para contornar limites da API do BCB."""
    chunks = []
    current_start = start_date
    delta_max = timedelta(days=max_years * 365)

    while current_start < end_date:
        current_end = current_start + delta_max
        if current_end > end_date:
            current_end = end_date
        chunks.append((current_start, current_end))
        current_start = current_end + timedelta(days=1)
        
    return chunks

def _fetch_bcb_sgs_raw_food(series_code: int, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Realiza a requisição direta para a API do BCB SGS com repetições automáticas em caso de instabilidade."""
    str_start = start_date.strftime("%d/%m/%Y")
    str_end = end_date.strftime("%d/%m/%Y")
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series_code}/dados?formato=json&dataInicial={str_start}&dataFinal={str_end}"
    
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Tentativa {attempt}/{max_retries}: Buscando série {series_code} de {str_start} a {str_end}")
            response = requests.get(url, timeout=12)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return pd.DataFrame(columns=["data", "valor"])
            return pd.DataFrame(data)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                logger.warning(f"Série {series_code} não ativa (404) em {str_start} - {str_end}.")
                return pd.DataFrame(columns=["data", "valor"])
            if attempt == max_retries:
                raise RuntimeError(f"Erro HTTP {e.response.status_code if e.response is not None else '?'} com o Banco Central.")
        except Exception as e:
            if attempt == max_retries:
                raise RuntimeError(f"Falha ao conectar com o Banco Central: {e}")
            time_to_sleep = 1.5 * attempt
            logger.warning(f"Tentativa falhou. Retentando em {time_to_sleep}s... Erro: {e}")
            import time
            time.sleep(time_to_sleep)
            
    return pd.DataFrame(columns=["data", "valor"])

def get_food_inflation_data(start_date_str: str, end_date_str: Optional[str] = None) -> pd.DataFrame:
    """
    Obtém a série histórica de inflação de alimentação e bebidas do IBGE/BCB, 
    calculando também o Número-Índice acumulado (Base Julho de 1994 = 100).
    """
    try:
        if "-" in start_date_str:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        else:
            start_date = datetime.strptime(start_date_str, "%d/%m/%Y")
            
        if end_date_str:
            if "-" in end_date_str:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            else:
                end_date = datetime.strptime(end_date_str, "%d/%m/%Y")
        else:
            end_date = datetime.now()
    except ValueError as e:
        logger.error(f"Erro no parsing das datas: {e}")
        raise ValueError("As datas de entrada devem estar no formato YYYY-MM-DD ou DD/MM/YYYY.")

    # 1. Busca os dados em pequenos blocos
    date_chunks = _chunk_dates(start_date, end_date)
    dfs = []
    
    for chunk_start, chunk_end in date_chunks:
        df_chunk = _fetch_bcb_sgs_raw_food(SERIE_IPCA_ALIMENTACAO_MENSAL, chunk_start, chunk_end)
        if not df_chunk.empty:
            dfs.append(df_chunk)
            
    if not dfs:
        logger.warning("Nenhum dado encontrado para a série de inflação alimentar.")
        return pd.DataFrame(columns=["data", "ipca_alimento", "ipca_alimento_indice"])
        
    df_final = pd.concat(dfs, ignore_index=True)
    df_final = df_final.drop_duplicates(subset=["data"])
    
    df_final["data"] = pd.to_datetime(df_final["data"], format="%d/%m/%Y")
    df_final["valor"] = pd.to_numeric(df_final["valor"], errors="coerce")
    df_final = df_final.dropna(subset=["valor"])
    df_final = df_final.sort_values("data").reset_index(drop=True)
    df_final = df_final.rename(columns={"valor": "ipca_alimento"})
    
    # 2. Calcula o Número-Índice composto (Base Julho de 1994 = 100)
    # Encontra a posição de julho/1994 para iniciar a base 100
    df_final = df_final.sort_values("data").reset_index(drop=True)
    
    # Cria uma série acumulada baseada no produto composto das taxas mensais
    # Para datas anteriores a Julho/1994, acumulamos de trás para frente
    # Para simplificar e garantir precisão, definimos a base 100 em Julho/1994
    # e multiplicamos cumulativamente as taxas
    df_final["ipca_alimento_indice"] = 100.0
    
    # Encontra o índice correspondente a 1994-07-01
    idx_jul_1994 = df_final[df_final["data"] == datetime(1994, 7, 1)].index
    if len(idx_jul_1994) > 0:
        base_idx = idx_jul_1994[0]
    else:
        base_idx = 0
        
    # Acumula de forma composta para frente a partir de Julho/1994
    current_value = 100.0
    for idx in range(base_idx + 1, len(df_final)):
        rate = df_final.loc[idx, "ipca_alimento"]
        # Se for nulo, assume inflação 0%
        if pd.isna(rate):
            rate = 0.0
        current_value = current_value * (1 + rate / 100.0)
        df_final.loc[idx, "ipca_alimento_indice"] = current_value
        
    # Acumula de forma composta para trás (de Julho/1994 para 1994-01-01 se houver)
    current_value = 100.0
    for idx in range(base_idx - 1, -1, -1):
        rate = df_final.loc[idx + 1, "ipca_alimento"]
        if pd.isna(rate):
            rate = 0.0
        current_value = current_value / (1 + rate / 100.0)
        df_final.loc[idx, "ipca_alimento_indice"] = current_value
        
    return df_final[["data", "ipca_alimento", "ipca_alimento_indice"]]
