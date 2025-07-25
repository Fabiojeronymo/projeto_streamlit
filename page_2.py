# Importar as bibliotecas necessárias
import streamlit as st
import pandas as pd
from datetime import datetime

# Importa as funções que serão reutilizadas da page_1
# Verifica se o arquivo page_1.py está na mesma pasta
try:
    from page_1 import carregar_tickers_acoes, carregar_dados
except ImportError:
    st.error("O arquivo 'page_1.py' não foi encontrado. Certifique-se de que ele está na mesma pasta.")
    st.stop()

# --- FUNÇÕES DE CÁLCULO E PROCESSAMENTO ---
def calcular_variacao_mensal(dados: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula a variação percentual mensal dos preços de fechamento
    Args:
        dados (pd.DataFrame): DataFrame com preços de fechamento diários
                              O índice deve ser do tipo datetime
    Returns:
        pd.DataFrame: DataFrame com a variação percentual mensal para cada ativo
    """
    # Garante que o índice é do tipo datetime
    dados.index = pd.to_datetime(dados.index)
    # Reorganiza para último dia de cada mês e calcula a variação
    df_mensal = dados.resample('ME').last()
    variacao_mensal = df_mensal.pct_change(fill_method=None)
    return variacao_mensal

# --- FUNÇÕES DE INTERFACE E FILTROS ---
def configurar_filtros(dados_variacao: pd.DataFrame) -> pd.DataFrame:
    """
    Configura e exibe todos os filtros na interface e retorna os dados filtrados
    Args:
        dados_variacao (pd.DataFrame): DataFrame com os dados de variação mensal
    Returns:
        pd.DataFrame: DataFrame contendo apenas os dados que passam por todos os filtros
    """
    # --- Filtro de Ações na Sidebar ---
    st.sidebar.header("Filtros de Ações")
    acoes_selecionadas = st.sidebar.multiselect(
        "Escolha as ações para visualizar",
        options=dados_variacao.columns,
        key="page2_acoes"
    )
    if not acoes_selecionadas:
        acoes_selecionadas = dados_variacao.columns.tolist()

    dados_filtrados = dados_variacao[acoes_selecionadas]

    # --- Filtros de Data e Variação no Corpo Principal ---
    st.subheader("Filtros Adicionais")

    # --- Filtro de Datas ---
    data_minima = dados_filtrados.index.min().to_pydatetime()
    data_maxima = dados_filtrados.index.max().to_pydatetime()
    
    # Define um valor para o último ano de dados.
    data_inicial_padrao = data_maxima - pd.DateOffset(years=1)
    if data_inicial_padrao < data_minima:
        data_inicial_padrao = data_minima

    # Layout com duas colunas para as datas
    col1, col2 = st.columns(2)
    with col1:
        data_inicial = st.date_input(
            "Data Inicial",
            value=data_inicial_padrao,
            min_value=data_minima,
            max_value=data_maxima,
            key="page2_data_inicial"
        )
    with col2:
        data_final = st.date_input(
            "Data Final",
            value=data_maxima,
            min_value=data_minima,
            max_value=data_maxima,
            key="page2_data_final"
        )

    # Aplica o filtro de data
    if data_inicial and data_final:
        if data_inicial > data_final:
            st.error("A data inicial não pode ser posterior à data final")
            return pd.DataFrame()
        dados_filtrados = dados_filtrados.loc[data_inicial:data_final]
    else:
        st.warning("Por favor, selecione um intervalo de datas válido")
        return pd.DataFrame()
    # --- Filtro de Popover (Alta/Baixa/Estável) ---
    with st.popover("Alta | Baixa | Estável"):
        filtros_variacao = []
        if st.checkbox("Apenas Altas (> 0%)", key="alta_filtro"):
            filtros_variacao.append("Alta")
        if st.checkbox("Apenas Baixas (< 0%)", key="filtro_filtro"):
            filtros_variacao.append("Baixa")
        if st.checkbox("Apenas Estáveis (0%)", key="estavel_filtro"):
            filtros_variacao.append("Estável")
    # Aplica o filtro de variação (Alta/Baixa/Estável) se alguma opção foi marcada
    if filtros_variacao:
        mascara = pd.DataFrame(False, index=dados_filtrados.index, columns=dados_filtrados.columns)
        if "Alta" in filtros_variacao:
            mascara |= (dados_filtrados > 0)
        if "Baixa" in filtros_variacao:
            mascara |= (dados_filtrados < 0)
        if "Estável" in filtros_variacao:
            mascara |= (dados_filtrados == 0)
        # Mantém a estrutura do DF, preenchendo com NaN onde a condição é falsa
        dados_filtrados = dados_filtrados.where(mascara)
    return dados_filtrados.dropna(how='all') # Remove linhas onde todos os valores são NaN

# --- FUNÇÕES DE PLOTAGEM E EXIBIÇÃO ---
def exibir_dashboard(dados_filtrados: pd.DataFrame):
    """
    Exibe o dashboard principal com o gráfico de barras da variação mensal
    Args:
        dados_filtrados (pd.DataFrame): O DataFrame final, já filtrado
    """
    st.header("Variação Mensal das Ações (%)")
    if dados_filtrados.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados")
        return
    # Formata o índice para o formato Ano/Mês
    dados_para_plotar = dados_filtrados.copy()
    dados_para_plotar.index = dados_para_plotar.index.strftime('%Y-%m')
    # Multiplica por 100 para exibir em formato percentual e usa stack para as barras não serem empilhadas, e sim lado a lado
    st.bar_chart(dados_para_plotar * 100, height=500, stack=False)
    st.write("---")
    st.subheader("Dados Filtrados")
    # Mostra os dados em formato de tabela, formatados como percentual
    st.dataframe(dados_filtrados.style.format("{:.2%}"))

# --- FUNÇÃO PRINCIPAL (MAIN) ---
def main():
    """
    Função principal que organiza e executa o aplicativo Streamlit para a página 2
    """
    # 1. Carregar os dados base (usando as funções da página 1)
    tickers = carregar_tickers_acoes()
    if not tickers:
        return # Para a execução se não encontrar tickers
    dados_diarios = carregar_dados(tickers)
    if dados_diarios.empty:
        st.error("Não foi possível carregar os dados das ações")
        return
    # 2. Processar os dados para obter a variação mensal
    variacao_mensal = calcular_variacao_mensal(dados_diarios)
    # 3. Configurar os filtros e obter os dados finais
    dados_finais_filtrados = configurar_filtros(variacao_mensal)
    # 4. Exibir o dashboard com os dados filtrados
    # A função de exibição só é chamada se houver dados após a filtragem inicial de ações
    if not dados_finais_filtrados.empty:
        exibir_dashboard(dados_finais_filtrados)

# Ponto de entrada do script
if __name__ == "__main__":
    main()
