import os
import time
import logging
from datetime import datetime, timedelta
import pandas as pd
import requests

# Configuração do Logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("bootstrap")

CACHE_DIR = "assets"
os.makedirs(CACHE_DIR, exist_ok=True)

# ----------------- CONFIGURAÇÕES E AUXILIARES -----------------

def fetch_with_retry(url: str, description: str, max_retries: int = 4, timeout: int = 15) -> requests.Response:
    """Realiza uma requisição HTTP com tentativas de reprocessamento em caso de falha/timeout."""
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Tentativa {attempt}/{max_retries}: {description}")
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response
        except (requests.exceptions.RequestException, Exception) as e:
            logger.warning(f"Falha na tentativa {attempt}: {e}")
            if attempt == max_retries:
                raise e
            time.sleep(2 * attempt) # Backoff exponencial simples
    raise RuntimeError("Falha inexplicável no loop de tentativas")

# ----------------- BANCO CENTRAL (DÓLAR E SELIC) COM MICRO-CHUNKING -----------------

def get_bcb_series_bootstrap(series_code: int, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Busca série do BCB dividida em micro-blocos de 2 anos para evitar sobrecarga e timeouts."""
    # Chunking de 2 anos (aprox. 730 dias)
    chunks = []
    current_start = start_date
    delta_max = timedelta(days=2 * 365)
    
    while current_start < end_date:
        current_end = current_start + delta_max
        if current_end > end_date:
            current_end = end_date
        chunks.append((current_start, current_end))
        current_start = current_end + timedelta(days=1)
        
    dfs = []
    for chunk_start, chunk_end in chunks:
        str_start = chunk_start.strftime("%d/%m/%Y")
        str_end = chunk_end.strftime("%d/%m/%Y")
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series_code}/dados?formato=json&dataInicial={str_start}&dataFinal={str_end}"
        
        try:
            response = fetch_with_retry(url, f"BCB {series_code} de {str_start} a {str_end}")
            data = response.json()
            if data:
                dfs.append(pd.DataFrame(data))
            # Pequeno delay de cortesia para evitar bloqueios de taxa limite (rate limit)
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Erro crítico no bloco {str_start} - {str_end}: {e}")
            # Se for um erro crítico, continuamos tentando os outros blocos para salvar o máximo possível
            continue
            
    if not dfs:
        return pd.DataFrame(columns=["data", "valor"])
        
    df_final = pd.concat(dfs, ignore_index=True)
    df_final = df_final.drop_duplicates(subset=["data"])
    df_final["data"] = pd.to_datetime(df_final["data"], format="%d/%m/%Y")
    df_final["valor"] = pd.to_numeric(df_final["valor"], errors="coerce")
    df_final = df_final.dropna(subset=["valor"])
    return df_final.sort_values("data").reset_index(drop=True)

# ----------------- EXECUÇÃO DO BOOTSTRAP -----------------

def main():
    logger.info("=== INICIANDO BOOTSTRAP DE DADOS REAL ANALYTICS ===")
    
    start_date = datetime(1994, 7, 1)
    end_date = datetime.now()
    
    # 1. Dólar Comercial (Série 1)
    logger.info("--- 1. Importando Taxa de Câmbio Dólar ---")
    try:
        df_dolar = get_bcb_series_bootstrap(1, start_date, end_date)
        df_dolar = df_dolar.rename(columns={"valor": "dolar"})
        df_dolar.to_csv(os.path.join(CACHE_DIR, "cache_dolar.csv"), index=False)
        logger.info(f"Dólar salvo com sucesso! {len(df_dolar)} registros desde {df_dolar['data'].min().strftime('%Y-%m')}")
    except Exception as e:
        logger.error(f"Falha ao gerar bootstrap do Dólar: {e}")
        
    # 2. SELIC Meta (Série 432)
    logger.info("--- 2. Importando Taxa SELIC Meta ---")
    try:
        df_selic = get_bcb_series_bootstrap(432, start_date, end_date)
        df_selic = df_selic.rename(columns={"valor": "selic"})
        df_selic.to_csv(os.path.join(CACHE_DIR, "cache_selic.csv"), index=False)
        logger.info(f"SELIC salva com sucesso! {len(df_selic)} registros desde {df_selic['data'].min().strftime('%Y-%m')}")
    except Exception as e:
        logger.error(f"Falha ao gerar bootstrap da SELIC: {e}")
        
    # 3. IPCA (IBGE SIDRA Tabela 1737)
    logger.info("--- 3. Importando IPCA (Inflação IBGE) ---")
    try:
        # V/63: Número-Índice
        url_idx = "https://apisidra.ibge.gov.br/values/t/1737/p/all/v/63/n1/all?formato=json"
        res_idx = fetch_with_retry(url_idx, "IBGE SIDRA IPCA Número-Índice (63)")
        df_idx_raw = pd.DataFrame(res_idx.json()[1:])
        df_idx = df_idx_raw[["D1C", "V"]].copy()
        df_idx.columns = ["data_ref", "ipca_indice"]
        df_idx["ipca_indice"] = pd.to_numeric(df_idx["ipca_indice"], errors="coerce")
        
        # V/2265: Variação Mensal
        url_var = "https://apisidra.ibge.gov.br/values/t/1737/p/all/v/2265/n1/all?formato=json"
        res_var = fetch_with_retry(url_var, "IBGE SIDRA IPCA Variação Mensal (2265)")
        df_var_raw = pd.DataFrame(res_var.json()[1:])
        df_var = df_var_raw[["D1C", "V"]].copy()
        df_var.columns = ["data_ref", "ipca_mensal"]
        df_var["ipca_mensal"] = pd.to_numeric(df_var["ipca_mensal"], errors="coerce")
        
        df_ipca = pd.merge(df_idx, df_var, on="data_ref", how="outer")
        df_ipca["data"] = pd.to_datetime(df_ipca["data_ref"], format="%Y%m")
        df_ipca = df_ipca.dropna(subset=["ipca_indice"])
        df_ipca = df_ipca.sort_values("data").reset_index(drop=True)
        df_ipca = df_ipca[["data", "ipca_indice", "ipca_mensal"]]
        
        df_ipca.to_csv(os.path.join(CACHE_DIR, "cache_ipca.csv"), index=False)
        logger.info(f"IPCA salvo com sucesso! {len(df_ipca)} registros desde {df_ipca['data'].min().strftime('%Y-%m')}")
    except Exception as e:
        logger.error(f"Falha ao gerar bootstrap do IPCA: {e}")
        
    # 4. Salário Mínimo (IPEA ValoresSerie)
    logger.info("--- 4. Importando Salário Mínimo (IPEA) ---")
    try:
        url_wage = "http://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='MTE12_SALMIN12')"
        res_wage = fetch_with_retry(url_wage, "IpeaData Salário Mínimo")
        df_wage_raw = pd.DataFrame(res_wage.json()["value"])
        df_wage = df_wage_raw[["VALDATA", "VALVALOR"]].copy()
        df_wage.columns = ["data", "salario_minimo"]
        df_wage["data"] = pd.to_datetime(df_wage["data"].str.slice(0, 10), format="%Y-%m-%d")
        df_wage["salario_minimo"] = pd.to_numeric(df_wage["salario_minimo"], errors="coerce")
        df_wage = df_wage.dropna(subset=["salario_minimo"])
        df_wage = df_wage.sort_values("data").reset_index(drop=True)
        
        df_wage.to_csv(os.path.join(CACHE_DIR, "cache_wage.csv"), index=False)
        logger.info(f"Salário Mínimo salvo com sucesso! {len(df_wage)} registros desde {df_wage['data'].min().strftime('%Y-%m')}")
    except Exception as e:
        logger.error(f"Falha ao gerar bootstrap do Salário Mínimo: {e}")
        
    logger.info("=== BOOTSTRAP DE DADOS CONCLUÍDO COM SUCESSO ===")

if __name__ == "__main__":
    main()
