import logging
import pandas as pd
import requests
from typing import Optional

# Configuração do Logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Constantes da API Ipeadata (Salário Mínimo)
SERIE_SALARIO_MINIMO = "MTE12_SALMIN12"
URL_IPEADATA_VALORES = f"http://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='{SERIE_SALARIO_MINIMO}')"

def get_minimum_wage_data() -> pd.DataFrame:
    """
    Busca a série histórica do salário mínimo nacional vigente na API do Ipeadata.
    
    Retorna:
        pd.DataFrame: DataFrame com colunas ['data', 'salario_minimo'] onde 'data' é Datetime e 'salario_minimo' é Float.
    """
    logger.info("Buscando série histórica do salário mínimo no Ipeadata")
    
    try:
        response = requests.get(URL_IPEADATA_VALORES, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        if not data or "value" not in data or not data["value"]:
            logger.warning("Nenhum dado retornado pela API do Ipeadata para o salário mínimo.")
            return pd.DataFrame(columns=["data", "salario_minimo"])
            
        # Transforma o nó 'value' no DataFrame
        df_raw = pd.DataFrame(data["value"])
        
        # Filtra apenas as colunas relevantes
        # VALDATA: Data de vigência
        # VALVALOR: Valor nominal do salário mínimo
        df = df_raw[["VALDATA", "VALVALOR"]].copy()
        df.columns = ["data", "salario_minimo"]
        
        # Parse das datas: Extrai a parte da data YYYY-MM-DD para evitar problemas com fuso horário
        df["data"] = pd.to_datetime(df["data"].str.slice(0, 10), format="%Y-%m-%d")
        
        # Conversão de valores
        df["salario_minimo"] = pd.to_numeric(df["salario_minimo"], errors="coerce")
        df = df.dropna(subset=["salario_minimo"])
        
        # Ordena e limpa índice
        df = df.sort_values("data").reset_index(drop=True)
        
        logger.info(f"Retornados {len(df)} registros de salário mínimo desde {df['data'].min().strftime('%Y-%m')}")
        return df
        
    except requests.exceptions.Timeout:
        logger.error("Timeout ao consultar o Ipeadata para a série de salário mínimo.")
        raise RuntimeError("O servidor do Ipeadata demorou muito para responder. Tente novamente mais tarde.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro na requisição ao Ipeadata: {e}")
        raise RuntimeError(f"Falha na comunicação com o Ipeadata: {e}")
    except Exception as e:
        logger.error(f"Erro inesperado ao buscar salário mínimo do Ipeadata: {e}")
        raise RuntimeError(f"Erro ao processar dados do salário mínimo: {e}")
