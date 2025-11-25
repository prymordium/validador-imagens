import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import requests
from io import BytesIO

st.set_page_config(page_title="Validação de Imagens", layout="wide")
st.title("Validador de Imagens")

uploaded_file = st.file_uploader("Faça upload do arquivo de imagens (.csv, .xlsx)", type=["csv", "xlsx"])

# Controle de índice na sessão para navegação
if "indice" not in st.session_state:
    st.session_state.indice = 0
if "df" not in st.session_state:
    st.session_state.df = None

if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.write("**Colunas detectadas no arquivo:**", df.columns.tolist())
    
    # Adiciona colunas de validação se não existirem
    for col in ["Valida", "Motivos", "Data_Validacao"]:
        if col not in df.columns:
            df[col] = ""

    st.session_state.df = df
else:
    df = st.session_state.df

if st.session_state.df is not None:
    df = st.session_state.df
    total = len(df)
    idx = st.session_state.indice

    # Pula quem já está validado
    while idx < total and str(df.iloc[idx].get("Valida", "")).upper() in ["SIM", "NÃO"]:
        idx += 1

    if idx < total:
        linha = df.iloc[idx]
        
        # Detecta nomes de coluna flexivelmente
        col_url = None
        col_categoria = None
        col_data = None
        col_cnpj = None
        
        # Busca URL/Imagem
        for candidate in ["CAMINHO_LOCAL", "URL_Imagem", "Imagem", "URL", "url", "link"]:
            if candidate in df.columns:
                col_url = candidate
                break
        
        # Busca Categoria
        for candidate in ["Categoria", "categoria", "Categoria_Item", "category"]:
            if candidate in df.columns:
                col_categoria = candidate
                break
        
        # Busca Data
        for candidate in ["Data", "data", "Data_Envio", "date"]:
            if candidate in df.columns:
                col_data = candidate
                break
        
        # Busca CNPJ
        for candidate in ["CNPJ", "cnpj", "Fornecedor", "supplier"]:
            if candidate in df.columns:
                col_cnpj = candidate
                break

        # Layout com imagem em destaque
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"## Imagem {idx+1} de {total}")
            
            # Imagem da web ou local
            if col_url and str(linha[col_url]).strip():
                try:
                    if "http" in str(linha[col_url]):
                        resp = requests.get(str(linha[col_url]), timeout=15)
                        img = Image.open(BytesIO(resp.content))
                    else:
                        img = Image.open(str(linha[col_url]))
                    
                    # Resize para 9:16 (vertical)
                    largura = 360
                    altura = int(largura * 16 / 9)  # 360 x 640
                    img = img.resize((largura, altura))
                    st.image(img, use_column_width=True)
                except Exception as e:
                    st.error(f"Erro ao carregar imagem: {e}")
            else:
                st.warning("Sem imagem nesta linha")
        
        with col2:
            st.markdown("### Informações do Item")
            
            # Exibe dados com fallback se vazios
            if col_url:
                st.text_area("**URL/Caminho:**", str(linha[col_url]), height=60, disabled=True)
            
            if col_categoria:
                categoria = str(linha[col_categoria]) if pd.notna(linha[col_categoria]) else "N/A"
                st.text_input("**Categoria:**", categoria, disabled=True)
            
            if col_data:
                data = str(linha[col_data]) if pd.notna(linha[col_data]) else "N/A"
                st.text_input("**Data:**", data, disabled=True)
            
            if col_cnpj:
                cnpj = str(linha[col_cnpj]) if pd.notna(linha[col_cnpj]) else "N/A"
                st.text_input("**CNPJ:**", cnpj, disabled=True)

        st.divider()
        
        st.markdown("### Validação")
        valido = st.radio('Selecione a validação:', ['Válida ✓', 'Inválida ✗'])
        
        motivos = []
        if valido == 'Inválida ✗':
            st.markdown("**Selecione pelo menos um motivo:**")
            motivos = st.multiselect(
                'Motivos:',
                ['FRAUDE', 'NÃO É PÉ', 'OUTRA CATEGORIA', 'OUTRO PRODUTO'],
                key=f"motivos_{idx}"
            )
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            btn_salvar = st.button('✓ Salvar resposta', use_container_width=True)
        
        with col_btn2:
            btn_proximo = st.button('→ Próxima imagem', use_container_width=True)

        if btn_salvar:
            if valido == 'Inválida ✗' and len(motivos) == 0:
                st.error('⚠️ Selecione pelo menos um motivo para marcar como inválida!')
            else:
                df.at[idx, 'Valida'] = 'SIM' if valido == 'Válida ✓' else 'NÃO'
                df.at[idx, 'Motivos'] = '; '.join(motivos)
                df.at[idx, 'Data_Validacao'] = str(datetime.now())
                st.session_state.indice = idx + 1
                st.session_state.df = df
                st.success('✅ Resposta salva com sucesso!')
                st.balloons()
        
        if btn_proximo:
            st.session_state.indice = idx + 1

    else:
        st.success('✅ Finalizado! Todas as imagens já foram validadas.')
        st.write(st.session_state.df)
        
        # Download do resultado
        csv = st.session_state.df.to_csv(index=False)
        st.download_button(
            label="📥 Baixar resultado (.csv)",
            data=csv,
            file_name="validacao_resultado.csv",
            mime="text/csv"
        )
        
        # Reiniciar
        if st.button("🔄 Reiniciar validação"):
            st.session_state.indice = 0
else:
    st.info('📤 Carregue um arquivo .csv ou .xlsx com colunas: URL_Imagem, Categoria, Data, CNPJ')

