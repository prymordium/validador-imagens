import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import requests
from io import BytesIO
import numpy as np

st.set_page_config(page_title="Validação de Imagens", layout="centered")
st.title("Validador de Imagens")

uploaded_file = st.file_uploader("Faça upload do arquivo de imagens (.csv, .xlsx)", type=["csv", "xlsx"])

# Controle de índice na sessão
if "indice" not in st.session_state:
    st.session_state.indice = 0
if "df" not in st.session_state:
    st.session_state.df = None

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        # Limpeza e validação do DataFrame
        df = df.fillna("")  # Substitui NaN por strings vazias
        df = df.astype(str).str.strip()  # Remove espaços em branco
        
        # Adiciona colunas de validação se não existirem
        for col in ["Valida", "Motivos", "Data_Validacao"]:
            if col not in df.columns:
                df[col] = ""
        
        st.session_state.df = df
    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {e}")
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
        
        # Detecta coluna de URL com segurança
        col_url = None
        url_value = None
        for candidate in ["URL_Imagem", "CAMINHO_LOCAL", "Imagem", "url", "URL"]:
            if candidate in df.columns:
                url_value = str(linha[candidate]).strip()
                if url_value and url_value.lower() != "nan" and url_value != "":
                    col_url = candidate
                    break
        
        st.markdown(f"**ID:** {idx+1} de {total}")
        st.markdown(f"**Categoria:** {linha.get('Categoria', 'N/A')}")
        st.markdown(f"**Data:** {linha.get('Data', 'N/A')}")
        st.markdown(f"**CNPJ:** {linha.get('CNPJ', 'N/A')}")
        
        # Debug: mostra qual coluna foi detectada
        if col_url:
            st.caption(f"Coluna detectada: {col_url}")
            st.caption(f"URL: {url_value[:80]}...")  # Primeiros 80 caracteres

        # Tenta carregar e exibir a imagem
        if col_url and url_value and url_value.lower() != "nan":
            try:
                # Se for URL da web
                if url_value.startswith("http://") or url_value.startswith("https://"):
                    resp = requests.get(url_value, timeout=15)
                    resp.raise_for_status()
                    img = Image.open(BytesIO(resp.content))
                else:
                    # Se for caminho local
                    img = Image.open(url_value)
                
                # Redimensiona para 9:16 (vertical)
                largura = 360
                altura = int(largura * 16 / 9)  # 640
                img = img.resize((largura, altura), Image.Resampling.LANCZOS)
                st.image(img, use_column_width=False)
                
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Erro ao baixar imagem (URL inválida ou servidor indisponível): {e}")
            except FileNotFoundError:
                st.error(f"❌ Arquivo local não encontrado: {url_value}")
            except Exception as e:
                st.error(f"❌ Erro ao processar imagem: {e}")
        else:
            st.warning("⚠️ Sem URL válida nesta linha. Verifique se a coluna URL_Imagem existe e contém dados.")

        st.markdown("---")
        valido = st.radio('Validação:', ['Válida ✓', 'Inválida ✗'], key=f"radio_{idx}")
        motivos = []
        if valido == 'Inválida ✗':
            motivos = st.multiselect('Selecione motivo(s):', ['FRAUDE', 'NÃO É PÉ', 'OUTRA CATEGORIA', 'OUTRO PRODUTO'], key=f"multi_{idx}")
        
        btn = st.button('Salvar resposta', key=f"btn_{idx}")

        if btn:
            if valido == 'Inválida ✗' and len(motivos) == 0:
                st.error('Selecione pelo menos um motivo para inválida!')
            else:
                df.at[idx, 'Valida'] = 'SIM' if valido == 'Válida ✓' else 'NÃO'
                df.at[idx, 'Motivos'] = '; '.join(motivos)
                df.at[idx, 'Data_Validacao'] = str(datetime.now())
                st.session_state.indice = idx + 1
                st.session_state.df = df
                st.success('✅ Resposta salva!')

    else:
        st.success('✅ Finalizado! Todas as imagens já foram validadas.')
        st.write(df)
        csv = df.to_csv(index=False)
        st.download_button("📥 Baixar resultado (.csv)", csv, "validadas.csv")
        
        if st.button("🔄 Reiniciar validação"):
            st.session_state.indice = 0
            st.rerun()
else:
    st.info('📤 Carregue um arquivo .csv ou .xlsx com colunas: URL_Imagem, Categoria, Data, CNPJ')
