# Real Analytics 🇧🇷📈

O **Real Analytics** é um dashboard interativo projetado para monitorar, simular e analisar a valorização e desvalorização histórica do Real Brasileiro (BRL). Utilizando exclusivamente dados públicos, gratuitos e oficiais do **Banco Central do Brasil**, **IBGE** e **IPEA**, a aplicação fornece uma visão integrada de indicadores macroeconômicos fundamentais e seu impacto real no poder de compra dos cidadãos.

---

## 🎯 Objetivo do Projeto

Fornecer um ambiente analítico completo, visual e interativo onde usuários possam:
1. Analisar a **evolução histórica do Dólar** e da **taxa SELIC**.
2. Compreender a **inflação histórica** medida pelo IPCA.
3. Contrastar o **Salário Mínimo Nominal** com o seu valor **Real** (corrigido pela inflação).
4. Medir e simular a perda ou ganho do **poder de compra** do brasileiro ao longo do tempo.
5. Realizar **correções monetárias** robustas por meio de um simulador de inflação acumulada de 1994 até o presente.

---

## 🛠️ Tecnologias Utilizadas

O projeto utiliza uma stack leve, moderna e de alta performance em Python:
* **Python 3.12+**
* **Streamlit**: Para o desenvolvimento rápido de uma interface de usuário moderna e responsiva.
* **Pandas**: Para a manipulação, limpeza e análise estatística dos dados.
* **Plotly**: Para gráficos interativos dinâmicos com suporte a zoom, hover e filtros.
* **Requests**: Para integração direta com as APIs REST públicas oficiais.

---

## 📁 Estrutura do Projeto

O projeto adota uma arquitetura modular que separa as responsabilidades de integração de dados, cálculos, visualizações e interface do usuário:

```
real/
├── app.py                      # Ponto de entrada do Streamlit
├── requirements.txt            # Dependências da aplicação
├── README.md                   # Documentação do projeto
│
├── services/                   # Integrações com APIs públicas oficiais
│   ├── __init__.py
│   ├── banco_central.py        # Integração com BCB SGS (Dólar, SELIC) - inclui auto-chunking
│   ├── ibge.py                 # Integração com SIDRA/IBGE (IPCA número-índice e variação)
│   ├── ibge_food_inflation.py  # Integração com BCB SGS (IPCA Alimentos e Bebidas - Série 1635)
│   └── ipea.py                 # Integração com IpeaData (Salário Mínimo)
│
├── calculations/               # Regras de negócio e cálculos matemáticos
│   ├── __init__.py
│   ├── food_inflation.py       # Correção monetária pela inflação de alimentos
│   ├── food_purchasing_power.py # Poder de compra alimentar e cestas básicas
│   ├── inflation.py            # Acúmulo de inflação e correção monetária
│   ├── purchasing_power.py     # Salário real e poder de compra histórico
│   └── indicators.py           # Estatísticas agregadas, mandatos e correlações
│
├── charts/                     # Geração de gráficos interativos com Plotly
│   ├── __init__.py
│   ├── exchange_chart.py       # Gráfico do Dólar vs SELIC
│   ├── food_inflation_chart.py # Comparativo IPCA Geral vs IPCA Alimentos
│   ├── food_purchasing_power_chart.py # Cestas Básicas e YoY growth do salário mínimo
│   ├── inflation_chart.py      # IPCA acumulado de 12 meses e variação mensal
│   └── purchasing_power_chart.py # Salário Nominal vs Real e Poder de Compra
│
├── utils/                      # Funções utilitárias
│   ├── __init__.py
│   └── formatter.py            # Formatação de moedas (BRL, USD), taxas e datas
└── assets/                     # Pasta para imagens ou ícones estáticos
```

---

## 🚀 Como Instalar e Executar

### 1. Pré-requisitos
Certifique-se de possuir o Python 3.12 instalado em sua máquina.

### 2. Clonar o projeto ou entrar na pasta
Entre na pasta onde o projeto está localizado:
```bash
cd real
```

### 3. Criar e Ativar Ambiente Virtual (Recomendado)
Para isolar as dependências do projeto:

**No Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**No macOS/Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 4. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 5. Executar a Aplicação
Com o ambiente ativado e as dependências instaladas, execute:
```bash
streamlit run app.py
```

O dashboard será aberto automaticamente em seu navegador padrão no endereço `http://localhost:8501`.

---

## 🍎 Módulo de Alimentação

### Descrição
Este módulo permite acompanhar a inflação dos alimentos, comparar com o IPCA geral e analisar o impacto no poder de compra da população brasileira ao longo do tempo.

### Indicadores e Análises Incluídas
* **Painel de Alimentos vs Geral**: Comparação direta de inflação acumulada do IPCA vs Alimentação e Bebidas.
* **Poder de Compra em Cestas Básicas**: Medição de quantas cestas básicas (proxy de R$ 800,00 deflacionados retrospectivamente) podem ser adquiridas com um salário mínimo nominal.
* **Gráfico de Evolução Nominal e YoY do Salário Mínimo**: Análise da taxa de crescimento anual do salário mínimo brasileiro.
* **Simulador de Mercado**: Atualiza qualquer valor histórico do carrinho de compras usando a inflação específica de Alimentação e Bebidas do período.

---

## 📊 Fontes de Dados Oficiais Integradas

* **Banco Central do Brasil (SGS)**:
  * Taxa de Câmbio Livre - Dólar Americano Comercial (Venda - Diário) - Série 1
  * Taxa SELIC acumulada diária / taxa meta COPOM (% a.a.) - Série 432
  * IPCA Alimentação e Bebidas (Variação Mensal %) - Série 1635
* **IBGE (SIDRA)**:
  * IPCA Número-Índice (base: dezembro de 1993 = 100) - Tabela 1737, Variável 63
  * IPCA Variação Mensal (%) - Tabela 1737, Variável 2265
* **IPEA (IpeaData)**:
  * Salário Mínimo Vigente - Série MTE12_SALMIN12

---

## 🚀 Próximas Evoluções (Roadmap)

1. **Cache Local Híbrido**: Carregar arquivos estáticos offline se as APIs públicas estiverem temporariamente fora do ar.
2. **Exportação de Relatórios**: Permitir exportação de dados em formatos Excel/CSV e relatórios automáticos em PDF.
3. **Análise por Mandatos Presidenciais**: Filtros específicos para comparar indicadores e variações econômicas entre diferentes governos brasileiros.
4. **Comparativo com a Poupança/Investimentos**: Simular o rendimento do dinheiro em poupança ou CDI contra a inflação no mesmo período escolhido.
