import logging
import pandas as pd
import requests
from typing import Optional

# Configuração do Logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Constantes da API SIDRA (Tabela 1737 - IPCA)
TABELA_IPCA_HISTORICO = 1737
VARIAVEL_NUMERO_INDICE = 63
VARIAVEL_VARIACAO_MENSAL = 2265

def _fetch_sidra_raw(table: int, variable: int, periods: str = "all") -> pd.DataFrame:
    """
    Busca dados brutos na API SIDRA do IBGE para uma tabela e variável específicas.
    """
    url = f"https://apisidra.ibge.gov.br/values/t/{table}/p/{periods}/v/{variable}/n1/all?formato=json"
    
    logger.info(f"Buscando tabela SIDRA {table}, variável {variable}, períodos {periods}")
    
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        if not data or len(data) <= 1:
            logger.warning(f"Nenhum dado retornado para a tabela {table}, variável {variable}")
            return pd.DataFrame()
            
        # O SIDRA retorna o cabeçalho explicativo na primeira linha (índice 0). 
        # Nós descartamos a primeira linha e criamos o DataFrame com o restante.
        df = pd.DataFrame(data[1:])
        return df
    except requests.exceptions.Timeout:
        logger.error(f"Timeout ao consultar a API SIDRA do IBGE para a tabela {table}, variável {variable}")
        raise RuntimeError("O servidor do IBGE (SIDRA) demorou muito para responder. Tente novamente mais tarde.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro na requisição à API SIDRA do IBGE: {e}")
        raise RuntimeError(f"Falha na comunicação com o IBGE: {e}")
    except Exception as e:
        logger.error(f"Erro inesperado ao buscar dados do IBGE: {e}")
        raise RuntimeError(f"Erro ao processar dados do IBGE: {e}")

def get_ipca_data() -> pd.DataFrame:
    """
    Obtém e limpa a série histórica do IPCA contendo o Número-Índice e a Variação Mensal.
    
    Retorna:
        pd.DataFrame: DataFrame indexado por data, com colunas ['ipca_indice', 'ipca_mensal'].
    """
    # 1. Busca o número-índice (V/63)
    df_indice_raw = _fetch_sidra_raw(TABELA_IPCA_HISTORICO, VARIAVEL_NUMERO_INDICE)
    if df_indice_raw.empty:
        raise RuntimeError("Não foi possível obter a série histórica de número-índice do IPCA.")
        
    # 2. Busca a variação mensal (V/2265)
    df_var_raw = _fetch_sidra_raw(TABELA_IPCA_HISTORICO, VARIAVEL_VARIACAO_MENSAL)
    if df_var_raw.empty:
        raise RuntimeError("Não foi possível obter a série histórica de variação mensal do IPCA.")

    # 3. Limpa e renomeia o DataFrame de número-índice
    # D1C contém a data em formato YYYYMM (ex: '199312')
    # V contém o valor da variável
    df_indice = df_indice_raw[["D1C", "V"]].copy()
    df_indice.columns = ["data_ref", "ipca_indice"]
    df_indice["ipca_indice"] = pd.to_numeric(df_indice["ipca_indice"], errors="coerce")
    
    # 4. Limpa e renomeia o DataFrame de variação mensal
    df_var = df_var_raw[["D1C", "V"]].copy()
    df_var.columns = ["data_ref", "ipca_mensal"]
    df_var["ipca_mensal"] = pd.to_numeric(df_var["ipca_mensal"], errors="coerce")

    # 5. Combina as séries
    df_ipca = pd.merge(df_indice, df_var, on="data_ref", how="outer")
    
    # 6. Parse da data no formato YYYYMM (ex: '199312' -> 1993-12-01)
    df_ipca["data"] = pd.to_datetime(df_ipca["data_ref"], format="%Y%m")
    
    # 7. Limpeza final
    df_ipca = df_ipca.dropna(subset=["ipca_indice"])
    df_ipca = df_ipca.sort_values("data").reset_index(drop=True)
    
    # Retorna com colunas selecionadas
    return df_ipca[["data", "ipca_indice", "ipca_mensal"]]
