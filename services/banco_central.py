import logging
from datetime import datetime, timedelta
import pandas as pd
import requests
from typing import Optional

# Configuração do Logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Constantes das Séries do SGS
SERIE_DOLAR_VENDA = 1
SERIE_SELIC_META = 432

def _chunk_dates(start_date: datetime, end_date: datetime, max_years: int = 3) -> list[tuple[datetime, datetime]]:
    """
    Divide um intervalo de datas em blocos menores para contornar o limite de 10 anos da API do BCB.
    """
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

def _fetch_bcb_sgs_raw(series_code: int, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    Realiza a requisição direta para a API do BCB SGS para um intervalo específico.
    """
    str_start = start_date.strftime("%d/%m/%Y")
    str_end = end_date.strftime("%d/%m/%Y")
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series_code}/dados?formato=json&dataInicial={str_start}&dataFinal={str_end}"
    
    logger.info(f"Buscando série BCB {series_code} de {str_start} a {str_end}")
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            logger.warning(f"Série {series_code} não retornou dados para o período {str_start} a {str_end}")
            return pd.DataFrame(columns=["data", "valor"])
            
        df = pd.DataFrame(data)
        return df
    except requests.exceptions.HTTPError as e:
        # Se for um erro 404 (Não Encontrado), significa que a série não existia nessa data (ex: SELIC Meta antes de 1999)
        if e.response is not None and e.response.status_code == 404:
            logger.warning(f"Série {series_code} não existia (404) no período {str_start} a {str_end}. Ignorando com segurança.")
            return pd.DataFrame(columns=["data", "valor"])
        logger.error(f"Erro HTTP na série {series_code} do BCB: {e}")
        raise RuntimeError(f"Erro de comunicação HTTP {e.response.status_code if e.response is not None else '?'} com o Banco Central.")
    except requests.exceptions.Timeout:
        logger.error(f"Timeout ao consultar a série {series_code} do BCB no período {str_start} a {str_end}")
        raise RuntimeError("O servidor do Banco Central demorou muito para responder. Tente novamente mais tarde.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro na requisição da série {series_code} do BCB: {e}")
        raise RuntimeError(f"Falha na comunicação com o Banco Central: {e}")
    except Exception as e:
        logger.error(f"Erro inesperado ao buscar dados do BCB: {e}")
        raise RuntimeError(f"Erro ao processar dados do Banco Central: {e}")

def get_bcb_series(series_code: int, start_date_str: str, end_date_str: Optional[str] = None) -> pd.DataFrame:
    """
    Busca uma série temporal do BCB SGS tratando automaticamente o limite de 10 anos de consulta.
    
    Parâmetros:
        series_code (int): Código da série no SGS (ex: 1 para Dólar, 432 para SELIC Meta).
        start_date_str (str): Data de início no formato 'AAAA-MM-DD' ou 'DD/MM/AAAA'.
        end_date_str (str, opcional): Data de fim. Se omitida, utiliza a data atual.
        
    Retorna:
        pd.DataFrame: DataFrame com as colunas ['data', 'valor'] onde 'data' é Datetime e 'valor' é Float.
    """
    # Parsing das datas de entrada
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

    if start_date > end_date:
        raise ValueError("A data de início não pode ser posterior à data de término.")

    # Chunking das datas para contornar o limite de 10 anos
    date_chunks = _chunk_dates(start_date, end_date)
    dfs = []
    
    for chunk_start, chunk_end in date_chunks:
        df_chunk = _fetch_bcb_sgs_raw(series_code, chunk_start, chunk_end)
        if not df_chunk.empty:
            dfs.append(df_chunk)
            
    if not dfs:
        logger.warning(f"Nenhum dado encontrado para a série {series_code} no período especificado.")
        return pd.DataFrame(columns=["data", "valor"])
        
    # Combina e limpa os dados
    df_final = pd.concat(dfs, ignore_index=True)
    df_final = df_final.drop_duplicates(subset=["data"])
    
    # Conversões de tipos e formatações
    df_final["data"] = pd.to_datetime(df_final["data"], format="%d/%m/%Y")
    df_final["valor"] = pd.to_numeric(df_final["valor"], errors="coerce")
    df_final = df_final.dropna(subset=["valor"])
    df_final = df_final.sort_values("data").reset_index(drop=True)
    
    return df_final

def get_exchange_rate(start_date_str: str, end_date_str: Optional[str] = None) -> pd.DataFrame:
    """
    Obtém a taxa de câmbio histórica do Dólar Comercial (venda) - Série 1.
    """
    df = get_bcb_series(SERIE_DOLAR_VENDA, start_date_str, end_date_str)
    return df.rename(columns={"valor": "dolar"})

def get_selic_rate(start_date_str: str, end_date_str: Optional[str] = None) -> pd.DataFrame:
    """
    Obtém a taxa SELIC Meta histórica definida pelo COPOM - Série 432.
    """
    df = get_bcb_series(SERIE_SELIC_META, start_date_str, end_date_str)
    return df.rename(columns={"valor": "selic"})
