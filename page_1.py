# Importar as bibliotecas necessárias
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import timedelta

# --- CONSTANTES ---
ARQUIVO_TICKERS = "IBOV.csv"
DATA_INICIO = "2010-01-01"
DATA_FIM = "2025-01-01"

# --- FUNÇÕES DE CARREGAMENTO DE DADOS ---
@st.cache_data
def carregar_tickers_acoes() -> list[str]:
    """
    Carrega a lista de tickers a partir de um arquivo CSV local.
    Adiciona o sufixo '.SA' para consulta no Yahoo Finance.
    Trata o erro caso o arquivo não seja encontrado.

    Returns:
        list[str]: Uma lista de tickers (ex: ['PETR4.SA', 'VALE3.SA']).
                   Retorna uma lista vazia se o arquivo não for encontrado.
    """
    try:
        base_tickers = pd.read_csv(ARQUIVO_TICKERS, sep=";")
        tickers = base_tickers["Código"].tolist()
        return [f"{item}.SA" for item in tickers]
    except FileNotFoundError:
        st.error(f"Erro: O arquivo '{ARQUIVO_TICKERS}' não foi encontrado.")
        st.info("Por favor, certifique-se de que o arquivo está na mesma pasta que o seu script Streamlit.")
        # Retorna uma lista vazia para que o app não quebre completamente.
        # A verificação na função main() impedirá a continuação.
        return []

@st.cache_data
def carregar_dados(empresas: list[str]) -> pd.DataFrame:
    """
    Baixa os dados históricos de preços de fechamento para uma lista de tickers.

    Args:
        empresas (list[str]): Lista de tickers para baixar os dados.

    Returns:
        pd.DataFrame: DataFrame com as datas no índice e os preços de fechamento
                      de cada empresa em uma coluna.
    """
    dados_brutos = yf.download(
        tickers=empresas,
        start=DATA_INICIO,
        end=DATA_FIM,
        group_by="ticker",
        auto_adjust=True,
        threads=True
    )
    # Extrai apenas a coluna 'Close' de cada ticker, tratando o MultiIndex
    fechamento = pd.DataFrame()
    for ticker in empresas:
        # Verifica se o ticker foi baixado com sucesso antes de tentar acessá-lo
        if ticker in dados_brutos.columns.levels[0]:
            fechamento[ticker] = dados_brutos[ticker]['Close']
    return fechamento

# --- FUNÇÕES DE INTERFACE E FILTROS ---
def configurar_sidebar(dados: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Configura a barra lateral (sidebar) com os filtros de ações e datas.

    Args:
        dados (pd.DataFrame): O DataFrame completo com todos os dados das ações.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]:
            - O DataFrame filtrado apenas pelas ações selecionadas.
            - O DataFrame filtrado pelas ações E pelo intervalo de datas.
    """
    st.sidebar.header("Filtros")

    # --- Filtro de Ações ---
    lista_acoes = st.sidebar.multiselect("Escolha as ações para visualizar", dados.columns, key="page1_acoes")

    # Caso 1: Nenhuma ação selecionada
    if not lista_acoes:
        # Retorna o dataframe original, uma lista vazia e None
        # O filtro de data será aplicado sobre o dataframe completo
        dados_filtrados = dados
        acao_unica = None
    
    # Caso 2: Uma ou mais ações selecionadas
    else:
        dados_filtrados = dados[lista_acoes]
        acao_unica = None
        # Se só uma ação foi selecionada, renomeia a coluna para "Close"
        if len(lista_acoes) == 1:
            acao_unica = lista_acoes[0]
            dados_filtrados = dados_filtrados.rename(columns={acao_unica: "Close"})

    # Aplica o filtro de datas sobre o resultado da seleção de ações
    data_inicial = dados_filtrados.index.min().to_pydatetime()
    data_final = dados_filtrados.index.max().to_pydatetime()
    intervalo_data = st.sidebar.slider(
        "Selecione o período",
        min_value=data_inicial,
        max_value=data_final,
        value=(data_inicial, data_final),
        step=timedelta(days=30),
        format="DD/MM/YYYY"
    )
    
    dados_filtrados_final = dados_filtrados.loc[intervalo_data[0]:intervalo_data[1]]
    
    return dados_filtrados_final, lista_acoes, acao_unica


# --- FUNÇÕES DE CÁLCULO E PLOTAGEM ---
def calcular_performance(dados: pd.DataFrame, lista_acoes: list[str], acao_unica: str) -> str:
    """
    Calcula a performance de cada ativo no DataFrame fornecido.
    Lida corretamente com ações que possuem dados faltantes no início do período.

    Args:
        dados_periodo (pd.DataFrame): DataFrame com os dados do período selecionado.

    Returns:
        str: Uma string formatada em Markdown com a performance de cada ativo.
    """
    texto_performance = ""
    # Itera sobre cada coluna (ação) do DataFrame do período
    if len(lista_acoes) == 1:
        # Nesse caso, os dados têm a coluna "Close", que representa a única ação
        dados = dados.rename(columns={"Close": acao_unica})
    
    if not lista_acoes:
        return "Nenhuma ação selecionada para calcular a performance."
    
    for acao in lista_acoes:
        
        # 1. Cria uma série para a ação e REMOVE os valores NaN.
        #    Isso é crucial para pegar o primeiro valor real da ação no período.
        serie_acao_sem_nan = dados[acao].dropna()

        # 2. Garante que, após remover os NaNs, ainda temos pelo menos 2 pontos para o cálculo.
        if len(serie_acao_sem_nan) > 1:
            # 3. Pega o primeiro e o último valor da SÉRIE LIMPA.
            valor_inicial = serie_acao_sem_nan.iloc[0]
            valor_final = serie_acao_sem_nan.iloc[-1]

            # Garante que não estamos dividindo por zero
            if valor_inicial != 0:
                performance = (valor_final / valor_inicial) - 1
                cor = "green" if performance > 0 else "red" if performance < 0 else "gray"
                texto_performance += f"**{acao}**: :{cor}[{performance:.2%}]  \n"
            else:
                texto_performance += f"**{acao}**: Não foi possível calcular (valor inicial é zero).  \n"
        else:
            # Se não houver dados suficientes informa o usuário.
            texto_performance += f"**{acao}**: Dados insuficientes para cálculo no período.  \n"
    
    return texto_performance

def plotar_grafico(dados: pd.DataFrame):
    """
    Plota um gráfico de linha com os dados fornecidos.

    Args:
        dados (pd.DataFrame): DataFrame com as séries temporais a serem plotadas.
    """
    if dados.empty:
        st.warning("Não foram encontrados dados para os tickers e período selecionados.")
    else:
        st.line_chart(dados)

# --- FUNÇÃO PRINCIPAL (MAIN) ---

def main():
    """Função principal que executa a página."""
    st.title("Evolução e Performance das Ações")

    dados_completos = carregar_dados(carregar_tickers_acoes())
    
    # A função de filtro agora retorna 3 valores
    dados_filtrados, lista_acoes, acao_unica = configurar_sidebar(dados_completos)

    # Se a lista de ações estiver vazia, mostra uma mensagem.
    # Caso contrário, exibe os dashboards.
    if not lista_acoes:
        st.info("Por favor, selecione ao menos uma ação na barra lateral para visualizar os dados.")
    else:
        st.subheader("Evolução dos Preços das Ações")
        plotar_grafico(dados_filtrados)

        st.subheader("Performance dos Ativos no Período")
        texto_performance = calcular_performance(dados_filtrados, lista_acoes, acao_unica)
        st.markdown(texto_performance)


# Ponto de entrada do script:
# Este bloco garante que a função main() só será executada quando
# o script for rodado diretamente (e não quando for importado por outro script).
if __name__ == "__main__":
    main()