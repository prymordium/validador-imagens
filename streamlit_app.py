import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import requests
from io import BytesIO

st.set_page_config(page_title="Validação de Imagens", layout="centered")
st.title("Validador de Imagens")

# Upload do arquivo de dados
uploaded_file = st.file_uploader("Faça upload do arquivo de imagens (.csv, .xlsx)", type=["csv", "xlsx"])

if uploaded_file:
    # Detecta extensão e lê os dados
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    # Adiciona colunas de validação se não existirem
    for col in ["Valida", "Motivos", "Data_Validacao"]:
        if col not in df.columns:
            df[col] = ""
    
    if "indice" not in st.session_state:
        st.session_state.indice = 0
    
    total = len(df)
    idx = st.session_state.indice

    # Só mostra quem ainda não foi validado
    while idx < total and df.iloc[idx]["Valida"] in ["SIM", "NÃO"]:
        idx += 1
        st.session_state.indice = idx

    if idx < total:
        linha = df.iloc[idx]
        col_url = None
        # Tenta detectar coluna de URL
        for candidate in ["CAMINHO_LOCAL", "URL_Imagem", "Imagem"]:  
            if candidate in df.columns:
                col_url = candidate
                break

        st.markdown(f"**ID:** {idx+1}")
        st.markdown(f"**Categoria:** {linha.get('Categoria', '')}")
        st.markdown(f"**Data:** {linha.get('Data', '')}")
        st.markdown(f"**CNPJ:** {linha.get('CNPJ', '')}")
        if col_url and str(linha[col_url]).strip():
            try:
                if "http" in str(linha[col_url]):
                    resp = requests.get(str(linha[col_url]), timeout=15)
                    img = Image.open(BytesIO(resp.content))
                else:
                    img = Image.open(str(linha[col_url]))
                img = img.resize((320, 320))
                st.image(img)
            except Exception as e:
                st.warning(f"Imagem não pôde ser carregada: {e}")
        else:
            st.info("Sem imagem nesta linha")
        
        valido = st.radio('Validação:', ['Válida ✓', 'Inválida ✗'])
        motivos = []
        if valido == 'Inválida ✗':
            motivos = st.multiselect('Selecione motivo(s):', ['FRAUDE', 'NÃO É PÉ', 'OUTRA CATEGORIA', 'OUTRO PRODUTO'])
        if st.button('Salvar resposta'):
            if valido == 'Inválida ✗' and len(motivos) == 0:
                st.error('Selecione pelo menos um motivo para inválida!')
            else:
                df.at[idx, 'Valida'] = 'SIM' if valido == 'Válida ✓' else 'NÃO'
                df.at[idx, 'Motivos'] = '; '.join(motivos)
                df.at[idx, 'Data_Validacao'] = str(datetime.now())
                st.session_state.indice += 1
                st.success('Resposta salva! Clique para continuar...')
                st.experimental_rerun()
    else:
        st.success('Finalizado! Todas as imagens já foram validadas.')
        st.write(df)
        st.download_button("Baixar resultado (.csv)", df.to_csv(index=False), "validadas.csv")
else:
    st.info('Carregue um arquivo .csv ou .xlsx com pelo menos colunas de URL, Categoria, Data, CNPJ.')

