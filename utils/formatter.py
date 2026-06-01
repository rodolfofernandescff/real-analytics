from datetime import datetime
from typing import Union

def format_currency_brl(value: Union[float, int]) -> str:
    """
    Formata um valor numérico para o padrão monetário brasileiro (R$ 1.234,56).
    """
    if value is None:
        return "R$ 0,00"
    
    # Formata com separador de milhar americano e depois inverte
    formatted = f"R$ {value:,.2f}"
    # Substitui a vírgula provisoriamente por um caractere qualquer, depois troca pontos por vírgulas e vice-versa
    formatted = formatted.replace(",", "_").replace(".", ",").replace("_", ".")
    return formatted

def format_currency_usd(value: Union[float, int]) -> str:
    """
    Formata um valor numérico para o padrão monetário norte-americano (US$ 1,234.56).
    """
    if value is None:
        return "US$ 0.00"
    
    return f"US$ {value:,.2f}"

def format_percent(value: Union[float, int], is_fraction: bool = False, decimal_places: int = 2) -> str:
    """
    Formata um valor para porcentagem com vírgula como separador decimal (ex: 12,34%).
    
    Parâmetros:
        value: O valor numérico.
        is_fraction: Se True, considera que 0.1234 representa 12.34%. Se False, considera que 12.34 representa 12.34%.
        decimal_places: Número de casas decimais.
    """
    if value is None:
        return f"0,{ '0' * decimal_places }%"
        
    val_to_format = value * 100.0 if is_fraction else value
    
    fmt_string = f"{{:.{decimal_places}f}}%"
    formatted = fmt_string.format(val_to_format)
    formatted = formatted.replace(".", ",")
    return formatted

def format_date(date_val: Union[datetime, str], output_format: str = "%m/%Y") -> str:
    """
    Formata um objeto de data ou string de data para o formato de saída brasileiro.
    """
    if date_val is None:
        return ""
        
    if isinstance(date_val, str):
        try:
            # Tenta converter string YYYY-MM-DD
            dt = datetime.strptime(date_val[:10], "%Y-%m-%d")
        except ValueError:
            return date_val
    else:
        dt = date_val
        
    # Nomes dos meses em português para uso se necessário, ou formatação padrão
    return dt.strftime(output_format)
