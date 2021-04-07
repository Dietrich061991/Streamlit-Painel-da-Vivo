import pandas as pd
import numpy as np
from datetime import datetime
import altair as alt
import streamlit as st
from PIL import Image
from os import listdir
from os.path import isfile, join





#--------------------------definido as configuraçãoes da pagina initial-------------------------#

icone = Image.open(r"C:\Users\sdietrich\Desktop\projeto painel\logo\icone.jpg")
st.set_page_config(
         page_title="Luiza Dashboad",
         page_icon= icone,
         layout="wide",
         initial_sidebar_state="expanded",
        )




def main():

  
   #---------------------------------submenu desenvolvedor/ version ------------------#
  st.sidebar.markdown("""
    # Menu
    """ ) 
  select_option = st.sidebar.selectbox(" ",('Processamento Diário','Arquivos Recebidos','Arquivos Não Recebidos'))


  with st.sidebar.beta_expander('Versão',expanded=False):
    st.code("Desenvolvedores:" )
    st.code("Sedami Dietrich Montcho" )
    st.code("Yuri Oliveira ")
    st.code("José Flavio Dias Da Costa Filho" )
    st.code("Versão 1.0")


  #----------------------------template html---------------------------#
  html_temp = """
  <div style="background-color:DarkMagenta;border - radius:20px"><p style="color:white;font-size:40px;padding:15px", align="center"> VIVO - LUIZA RENEGOCIAÇÃO 💼</p></div>
    """
  st.markdown(html_temp,unsafe_allow_html=True)

 #-------------------------Affichar imagem vivo--------------------------------------#
  image = Image.open(r"C:\Users\sdietrich\Desktop\projeto painel\logo\vivo.jpg")
  st.image(image,use_column_width=True)

 #--------------------------definir cor horafim_max-----------------------------------#
  @st.cache
  def cor_tempo(val):
    temp_max = val == val.max()
    return ['background-color: Plum' if tempo else '' for tempo in temp_max]

 #---------------------definir cor arquivos nao recebidos(billing)-------------------#
  @st.cache
  def cor_billing(val):
    keywords = ["billing", "Billing", "BILLING"]
    return ['background-color: LightSalmon' if any(word in objeto for word in keywords)  else '' for objeto in val]


  #----------------------Calculo duracao---------------------------------------------#
  @st.cache
  def calculaduracaomalhas(inicioProcesso, fimProcesso):
    inicioProcesso = datetime.strptime(inicioProcesso, '%H:%M:%S')
    fimProcesso = datetime.strptime(fimProcesso, '%H:%M:%S')

    return str(fimProcesso - inicioProcesso)

  def calculaTabelaTempoDeProcessamento(df_logs):
      tabelaTempoDeProcessamento = []
      for malha in range(1, 23):
          df_malha = df_logs[(df_logs['MALHA'] == malha) & (df_logs['DATA INICIO'] == tipo_data)]    
          df_malha = df_malha[['ETAPA', 'HORA INICIO', 'HORA FIM']]
          
          #Tentativa com 
          df_ING = df_malha[df_malha['ETAPA'] == 'ING']
          df_DUM = df_malha[df_malha['ETAPA'] == 'DUM']
          
          horaInicioMalha = df_ING['HORA INICIO'].min()
          horaFimMalha = df_DUM['HORA FIM'].max()
          
          #print("malha: ", malha)
          #print("horaFimMalha: ", horaFimMalha)
          if type(horaFimMalha) != str:
              horaFimMalha = df_ING['HORA FIM'].max()
              
          duracaoMalha = calculaduracaomalhas(horaInicioMalha, horaFimMalha)
          tabelaTempoDeProcessamento.append([malha, horaFimMalha, duracaoMalha])
      
      df_tempoDeProcessamentoPorMalha = pd.DataFrame(tabelaTempoDeProcessamento, columns = ['MALHA', 'HORA FIM', 'DURACAO MALHA'])
      df_tempoDeProcessamentoPorMalha = df_tempoDeProcessamentoPorMalha.set_index('MALHA')
      return df_tempoDeProcessamentoPorMalha

   #-----------------------Quantidade etaps e quantidade statu groupby----------------------------#
  @st.cache
  def quantidad_etapa_descricao(df_diaAtual):
    df_groupby_statu_etapa = df_diaAtual.groupby(['ETAPA','STATUS']).size().reset_index(name='QUANTIDADE')
    df_groupby_statu_etapa = pd.pivot_table(df_groupby_statu_etapa , index = ['ETAPA'],columns=['STATUS'] ,fill_value=0 ,aggfunc=np.sum)
    
    #pegar a coluna apos pivot table para definir elementos da etapa como colunas
    df_groupby_statu_etapa = df_groupby_statu_etapa["QUANTIDADE"]
    
    # colocar o index em uma lista 
    nome_index = df_groupby_statu_etapa.index.unique().to_list()
    
    #contar quantas vesez aparecem os elementos do index do dataframe df_groupby_statu_etapa
    contagem_nome_index_etapa_fim = df_groupby_statu_etapa.index.value_counts().to_list()
    
    ## renomear index
    nome_index_novo=[]
    for y, content in enumerate(contagem_nome_index_etapa_fim):
      for x in range(content):
        nome_index_novo.append(nome_index[y] +'_'+ str(x))

    df_groupby_statu_etapa.index=nome_index_novo

    ## resetar o index para gente poder reordenar (aplicar lista comprehension)
    ordem = [x for x in nome_index_novo if x.startswith('ING')]
    ordem.extend([x for x in nome_index_novo if x.startswith('DIF')])
    ordem.extend([x for x in nome_index_novo if x.startswith('ENR')])
    ordem.extend([x for x in nome_index_novo if x.startswith('DUM')])
    df_groupby_statu_etapa = df_groupby_statu_etapa.reindex(index=ordem)
    
    #renomear os indinces
    df_groupby_statu_etapa.rename(index={'ING_0': 'ING', 'DIF_0': 'DIF','ENR_0': 'ENR', 'DUM_0': 'DUM'}, inplace=True)
    
    #calcular subtotal e total por etape e descrição
    df_groupby_statu_etapa = df_groupby_statu_etapa.append(df_groupby_statu_etapa.sum().rename('TOTAL')).assign(TOTAL=lambda d: d.sum(1))
    return df_groupby_statu_etapa


  #-----------------------recebimento arquivos----------------------------#

  @st.cache
  def retornaQuantidadeCodStatus(codigos, df_diaAtual):
    df_diaAtual_codigo = df_diaAtual[df_diaAtual['COD_STATUS'].isin(codigos)]
    return len(df_diaAtual_codigo)

  @st.cache
  def geraTabelaArquivosRecebidos(df_diaAtual):
    #Arquivos Nao recebidos mas dentro do prazo
    CodigosNaoRecebidoMasDentroDoPrazo = [48,49,50,51]
    qtdeArquivosNaoRecebidoMasDentroDoPrazo = retornaQuantidadeCodStatus(CodigosNaoRecebidoMasDentroDoPrazo, df_diaAtual)
    #Arquivos nao recebidos
    CodigosArquivosNaoRecebidos = [1]
    qtdeArquivosNaoRecebidos = retornaQuantidadeCodStatus(CodigosArquivosNaoRecebidos, df_diaAtual)
    #Arquivos recebidos com problema
    codigosArquivosRecebidosComProblema = [2,3,4,5,6,7]
    qtdeArquivosRecebidosComProblema = retornaQuantidadeCodStatus(codigosArquivosRecebidosComProblema, df_diaAtual)
    #Arquivos Recebidos
    df_arquivosRecebidos = df_diaAtual[(df_diaAtual['ETAPA'] == 'ING') & (df_diaAtual['STATUS'] == 'SUCCESS')]
    qtdeArquivosRecebidos = len(df_arquivosRecebidos)
    recebimento = {'RECEBIMENTO DE ARQUIVOS': ['Recebidos', 'Não Recebidos', 'Recebidos com problemas', 'Não Recebidos (Dentro do Prazo)'],
                            'QUANTIDADE': [qtdeArquivosRecebidos, qtdeArquivosNaoRecebidos, qtdeArquivosRecebidosComProblema, qtdeArquivosNaoRecebidoMasDentroDoPrazo]}
    recebimento_arquivos = pd.DataFrame (recebimento, columns = ['RECEBIMENTO DE ARQUIVOS', 'QUANTIDADE'])
    recebimento_arquivos = recebimento_arquivos.sort_values(by = 'QUANTIDADE', ascending=False)
    recebimento_arquivos = recebimento_arquivos.set_index('RECEBIMENTO DE ARQUIVOS')
    return recebimento_arquivos

  
  def imprimirorigemnaorecebidos():
    arquivonaorecebidos = df_diaAtual.query('DESCRICAO == "Arquivo nao recebido"')
    arquivonaorecebidos = arquivonaorecebidos[['OBJETO','ORIGEM','PRODUTO','DESCRICAO']]
    arquivonaorecebidos.set_index('ORIGEM',inplace =True)
    arquivonaorecebidos["DESCRICAO"].replace({"Arquivo nao recebido": "Arquivo não recebido"}, inplace = True)
    arquivonaorecebidos = arquivonaorecebidos.rename(columns = {"DESCRICAO":"DESCRIÇÃO"})
    return arquivonaorecebidos
 
 
 
 #funcao que calcula e retorna a Duracao de um Processo
 
  def calculaDuracaoProcesso(inicioProcesso, fimProcesso):
      try:
          inicioProcesso = datetime.strptime(inicioProcesso, '%d/%m/%Y %H:%M:%S')
          fimProcesso = datetime.strptime(fimProcesso, '%d/%m/%Y %H:%M:%S')
    
          return str(fimProcesso - inicioProcesso)
      except:
          return 'NA'
  


  #--------------------------------------ler arquivo log--------------------------------#
  df_logs = pd.read_csv(r"C:\Users\sdietrich\Documents\gerarrelatorio\pastaprocess\process.csv", delimiter= ';', index_col = False, header = None)
 
  #---------------------------------definir colunas para o arquivo de log---------------#
  df_logs.columns = ['DATA INICIO', 'DATA FIM', 'MALHA', 'ETAPA', 'OBJETO',
                    'COD', 'ORIGEM', 'PRODUTO', 'STATUS', 'COD_STATUS', 'DESCRICAO']

  #remove as linhas com NA do dataframe
  df_logs = df_logs[df_logs['DATA FIM'].notna()]

  #calcula DURACAO PROCESSO
  df_logs['DURACAO'] = df_logs.apply(lambda x: calculaDuracaoProcesso(x['DATA INICIO'], x['DATA FIM']), axis=1)

  #Quebra coluna DATA em duas colunas: DATA e HORA
  df_logs[['DATA INICIO', 'HORA INICIO']] = df_logs['DATA INICIO'].str.split(' ', 1, expand = True)
  df_logs[['DATA FIM', 'HORA FIM']] = df_logs['DATA FIM'].str.split(' ', 1, expand = True)

  df_logs = df_logs[['DATA INICIO', 'HORA INICIO', 'DATA FIM', 'HORA FIM',
                    'DURACAO', 'MALHA', 'COD', 'ETAPA', 'OBJETO',
                    'ORIGEM', 'PRODUTO', 'STATUS', 'COD_STATUS', 'DESCRICAO']]

  df_logs['COD_STATUS'] = df_logs['COD_STATUS'].fillna(0)
  df_logs['DESCRICAO'] = df_logs['DESCRICAO'].fillna("")

#--------------------------------------ler arquivo recebidos--------------------------------#
  arquivorecebidos = pd.read_csv(r"C:\Users\sdietrich\Documents\gerarrelatorio\pastarecevfile\received.csv",  delimiter= ';', index_col = False, header = None)

#---------------------------------definir colunas para o recebidos ------------------------#
  arquivorecebidos.columns = ['DATA INICIO','MALHA', 'OBJETO', 'COD', 'ORIGEM', 'PRODUTO','NOME_ARQUIVO']
 
  #Quebra coluna DATA em duas colunas: DATA e HORA
  arquivorecebidos[['DATA INICIO', 'HORA DE RECEBIMENTO']] = arquivorecebidos['DATA INICIO'].str.split(' ', 1, expand = True)
  
  #reordenar as colunas do datagrame
  arquivorecebidos = arquivorecebidos[['DATA INICIO','HORA DE RECEBIMENTO','MALHA', 'OBJETO', 'COD', 'ORIGEM', 'PRODUTO','NOME_ARQUIVO']]
                    

#---------------------Opçao escolhidono menu-----------------------------------------------#
  if select_option == 'Processamento Diário':
    unique_data = df_logs['DATA INICIO'].unique().tolist()
  
    unique_data_date = [datetime.strptime(data, '%d/%m/%Y').date() for data in unique_data]
    unique_ix = unique_data_date.index(max(unique_data_date))
    tipo_data = st.selectbox("Data do Processamento", unique_data, index=unique_ix)
      
    st.info('Relatório do dia: ' + tipo_data)
    df_diaAtual = df_logs.loc[df_logs['DATA INICIO'] == tipo_data]   
    st.write((df_diaAtual).style.set_properties(**{'background-color': 'black',                                                   
                                    'color': 'Lime',                       
                                    'border-color': 'white'})
                                    .format({"MALHA": "{:.0f}"})
                                    .format({"COD": "{:.0f}"})
                                    .format({"COD_STATUS": "{:.0f}"}))

    #---------------------template html etapa_statu---------------------# 
    html_groupby_etapa_statu = """
    <div style="background-color:DarkMagenta; border:0px solid black;border - radius:5px"><p style="color:white;font-size:14px;padding:10px", align="center">Status do Processamentos por Etapa 📝</p></div>
    """
    st.markdown(html_groupby_etapa_statu,unsafe_allow_html=True)
    st.table(quantidad_etapa_descricao(df_diaAtual))

    #-------------------------template html duracao----------------------#
    html_tempo_duracao = """
    <div style="background-color:DarkMagenta; border:0px solid black;border - radius:5px"><p style="color:white;font-size:14px;padding:10px", align="center">Tempo de Processamento por Malha ⌚</p></div>
    """
    st.markdown(html_tempo_duracao,unsafe_allow_html=True)
    st.table(calculaTabelaTempoDeProcessamento(df_logs).style.apply(cor_tempo, subset =['HORA FIM']))

    #--------------------template recebimento arquivos----------------------#
    html_recebimento_arquivos = """
    <div style="background-color:DarkMagenta; border:0px solid black;border - radius:5px"><p style="color:white;font-size:14px;padding:10px", align="center">Controle de Recebimento de Arquivos 📝</p></div>
    """
    st.markdown(html_recebimento_arquivos,unsafe_allow_html=True)
    st.table(geraTabelaArquivosRecebidos(df_diaAtual))
      
    #--------------------Tabela arquivos não recebidos----------------------#
    html_recebimento_arquivos = """
    <div style="background-color:DarkMagenta; border:0px solid black;border - radius:5px"><p style="color:white;font-size:14px;padding:10px", align="center"> Arquivos Não Recebidos ⚠</p></div>
    """
    st.markdown(html_recebimento_arquivos,unsafe_allow_html=True)
    st.table((imprimirorigemnaorecebidos()).style.apply(cor_billing, subset =['OBJETO']))
    quantidade = str(((imprimirorigemnaorecebidos())['DESCRIÇÃO'].value_counts().sum()))
    if quantidade == 0:
      st.success('Quantidade de Arquivo(s) Não Recebido(s): ' + quantidade)
    else:
      st.warning('Quantidade de Arquivo(s) Não Recebido(s): ' + quantidade)


#-------------------------Processo periodico e arquivo nao recebido por periodo------------------------------#
  
  def processoperiodico_arquivo_naorecebidos():
    st.markdown("""
    ### Selecione o Período: 
    """ )
    c1,c2 = st.beta_columns(2)
    with c1:
      data_inicio = st.date_input('Data Início [Ano/Mês/Dia]')
      data_inicio_formatado = data_inicio.strftime("%d/%m/%Y")
    with c2:
      data_fim = st.date_input('Data Fim [Ano/Mês/Dia]')
      data_fim_formatado = data_fim.strftime("%d/%m/%Y")

    data_filtrado = df_logs.set_index(pd.to_datetime(df_logs['DATA INICIO'])).loc[data_inicio_formatado:data_fim_formatado].reset_index(drop=True)
    
    if  data_inicio_formatado == data_fim_formatado:
        st.code('Tabela dos processos executados no dia ' + data_inicio_formatado + " ⏳")
    else:
        st.code('Tabela dos processos executados do dia ' + data_inicio_formatado + " Até o dia " +  data_fim_formatado  + " ⏳")
    
    st.dataframe(data_filtrado.style.set_properties(**{'background-color': 'black',                                                   
                                    'color': 'Lime',                       
                                    'border-color': 'white'})
                                    .format({"MALHA": "{:.0f}"})
                                    .format({"COD": "{:.0f}"})
                                    .format({"COD_STATUS": "{:.0f}"}))

    st.info('Quantidade de Processos Executados: ' +  str(data_filtrado.shape[0]))    
    
    html_recebimento_arquivos = """
    <div style="background-color:DarkMagenta; border:0px solid black;border - radius:5px"><p style="color:white;font-size:14px;padding:10px", align="center">Tabela dos Arquivos Não Recebidos por Origem ⚠</p></div>      
    """   
    st.markdown(html_recebimento_arquivos,unsafe_allow_html=True)         
    
    if  data_inicio_formatado == data_fim_formatado:
        st.code('Tabela dos arquivos não recebidos no dia ' + data_inicio_formatado + " ⏳")
    else:
        st.code('Tabela dos arquivos não recebidos do dia ' + data_inicio_formatado + " até o dia " +  data_fim_formatado  + " ⏳")
    
    data_filtrado_arquivo_nao_recebidos = data_filtrado[data_filtrado["DESCRICAO"] == 'Arquivo nao recebido']
    data_filtrado_arquivo_nao_recebidos = data_filtrado_arquivo_nao_recebidos[['DATA INICIO','OBJETO','ORIGEM','PRODUTO','DESCRICAO']]
    data_filtrado_arquivo_nao_recebidos.set_index(['OBJETO'], inplace = True)

    data_filtrado_arquivo_nao_recebidos = data_filtrado_arquivo_nao_recebidos.groupby(by = ['ORIGEM','PRODUTO']).size().reset_index(name='QTD ARQUIVOS NÃO RECEBIDOS')
    data_filtrado_arquivo_nao_recebidos['ORIGEM_PRODUTO'] = data_filtrado_arquivo_nao_recebidos['ORIGEM'] + '_'+ data_filtrado_arquivo_nao_recebidos['PRODUTO']
    #colocando a utima coluna para frente
    data_filtrado_arquivo_nao_recebidos = data_filtrado_arquivo_nao_recebidos.loc[:,::-1]
    data_filtrado_arquivo_nao_recebidos = data_filtrado_arquivo_nao_recebidos[['ORIGEM_PRODUTO', 'QTD ARQUIVOS NÃO RECEBIDOS']]
    st.table(data_filtrado_arquivo_nao_recebidos.style.apply(cor_billing, subset =['ORIGEM_PRODUTO']))
    totalarquivonaorecebidos = data_filtrado_arquivo_nao_recebidos['QTD ARQUIVOS NÃO RECEBIDOS'].sum()
    if totalarquivonaorecebidos == 0:
      st.success("Total de arquivos não recebidos: " + str(totalarquivonaorecebidos))
    else:
      st.warning("Total de arquivos não recebidos: " + str(totalarquivonaorecebidos))

  #------------------------Gerar grafico arquivos nao recebidos----------------------------#
    if data_inicio_formatado == data_fim_formatado:
        fig = alt.Chart(data_filtrado_arquivo_nao_recebidos).mark_bar(color='DarkMagenta').encode(
        x = alt.X('QTD ARQUIVOS NÃO RECEBIDOS', axis=alt.Axis(title='QTD ARQUIVOS NÃO RECEBIDOS')),
        y= 'ORIGEM_PRODUTO' 
        )
        text = fig.mark_text(
        align='left',
        baseline='middle',
        dx=3
        ).encode(
        text='QTD ARQUIVOS NÃO RECEBIDOS'
        )
        st.write((fig  + text).properties(width=615, height=500 , title=(("Arquivos não recebidos no dia "+ data_inicio_formatado))))
    else:
        fig = alt.Chart(data_filtrado_arquivo_nao_recebidos).mark_bar(color='DarkMagenta').encode(
        x = alt.X('QTD ARQUIVOS NÃO RECEBIDOS', axis=alt.Axis(title='QTD ARQUIVOS NÃO RECEBIDOS')),
        y= 'ORIGEM_PRODUTO' 
        )
        text = fig.mark_text(
        align='left',
        baseline='middle',
        dx=3
        ).encode(
        text='QTD ARQUIVOS NÃO RECEBIDOS'
        )
        st.write((fig  + text).properties(width=615, height=500 , title=(("Arquivos não recebidos do dia "+ data_inicio_formatado) + (" até " + data_fim_formatado))))
    


  #-------------------------Processo recebimentos  arquivo  ------------------------------#
  def arquivorecebidosporperiodo():
    st.markdown("""
    ### Selecione o Período: 
    """ ) 
    c1,c2 = st.beta_columns(2)
    with c1:
      data_inicio = st.date_input('Data Início [Ano/Mês/Dia]')
      data_inicio_formatado = data_inicio.strftime("%d/%m/%Y")
    with c2:
      data_fim = st.date_input('Data Fim [Ano/Mês/Dia]')
      data_fim_formatado = data_fim.strftime("%d/%m/%Y")

    data_filtrado = df_logs.set_index(pd.to_datetime(df_logs['DATA INICIO'])).loc[data_inicio_formatado:data_fim_formatado].reset_index(drop=True)
    
    if data_inicio_formatado == data_fim_formatado:
        st.code('Processo do dia ' + data_inicio_formatado +" ⏳")
    else:
        st.code('Processos do dia ' + data_inicio_formatado + " até o dia " +  data_fim_formatado  + " ⏳")
    
    
    st.write(data_filtrado.style.set_properties(**{'background-color': 'black',                                                   
                                    'color': 'Lime',                       
                                    'border-color': 'white'})
                                    .format({"MALHA": "{:.0f}"})
                                    .format({"COD": "{:.0f}"})
                                    .format({"COD_STATUS": "{:.0f}"}))
    st.info('Quantidade de Processos Executados: ' +  str(data_filtrado.shape[0]))

    html_arquivos_recebidos = """
    <div style="background-color:DarkMagenta; border:0px solid black;border - radius:5px"><p style="color:white;font-size:14px;padding:10px", align="center">Tabela dos Arquivos Recebidos por Origem 📝 </p></div>      
    """   
    st.markdown(html_arquivos_recebidos,unsafe_allow_html=True) 

    if data_inicio_formatado == data_fim_formatado:
        st.code('Arquivos recebidos no dia ' + data_inicio_formatado +" ⏳")
    else:
        st.code('Arquivos recebidos do dia ' + data_inicio_formatado + " até o dia " +  data_fim_formatado  + " ⏳")

    arquivorecebidos_por_periode = arquivorecebidos.set_index(pd.to_datetime(arquivorecebidos['DATA INICIO'])).loc[data_inicio_formatado:data_fim_formatado].reset_index(drop=True)

    arquivorecebidos_por_periode.set_index(['OBJETO'], inplace = True)
    
    arquivorecebidos_por_periode = arquivorecebidos_por_periode.groupby(by = ['ORIGEM','PRODUTO']).size().reset_index(name='QTD ARQUIVOS RECEBIDOS') 
    arquivorecebidos_por_periode['ORIGEM_PRODUTO'] = arquivorecebidos_por_periode['ORIGEM'] + '_'+ arquivorecebidos_por_periode['PRODUTO']
    #colocando a utima coluna para frente
    arquivorecebidos_por_periode = arquivorecebidos_por_periode.loc[:,::-1]
    arquivorecebidos_por_periode = arquivorecebidos_por_periode[['ORIGEM_PRODUTO', 'QTD ARQUIVOS RECEBIDOS']]
    st.table(arquivorecebidos_por_periode.style.bar(subset=['QTD ARQUIVOS RECEBIDOS'], color='#DDA0DD'))
    st.success("Total de Arquivos Recebidos: " + str(arquivorecebidos_por_periode['QTD ARQUIVOS RECEBIDOS'].sum()))

  if select_option == 'Arquivos Recebidos':
    return(arquivorecebidosporperiodo())

  if select_option == 'Arquivos Não Recebidos':
    return(processoperiodico_arquivo_naorecebidos())


if __name__ == '__main__':
    	main()



