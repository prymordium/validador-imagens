import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import requests
from io import BytesIO
import numpy as np

# ===== CONFIGURAÇÃO DA PÁGINA =====
st.set_page_config(page_title="Validação de Imagens", layout="centered", initial_sidebar_state="collapsed")
st.title("✓ Validador de Imagens")

# ===== INICIALIZAR ESTADO DA SESSÃO =====
if "indice" not in st.session_state:
    st.session_state.indice = 0
if "df" not in st.session_state:
    st.session_state.df = None

# ===== UPLOAD DO ARQUIVO =====
uploaded_file = st.file_uploader("📤 Faça upload do arquivo (.csv, .xlsx)", type=["csv", "xlsx"])

if uploaded_file:
    try:
        # Carregar arquivo
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        # Limpeza correta: coluna por coluna
        for col in df.columns:
            if df[col].dtype == 'object':  # Apenas colunas de texto
                df[col] = df[col].astype(str).str.strip()
        
        # Substitui NaN por strings vazias
        df = df.fillna("")
        
        # Adiciona colunas de validação se não existirem
        for col in ["Valida", "Motivos", "Data_Validacao"]:
            if col not in df.columns:
                df[col] = ""
        
        st.session_state.df = df
    except Exception as e:
        st.error(f"❌ Erro ao carregar arquivo: {e}")

# ===== PROCESSAR VALIDAÇÃO =====
if st.session_state.df is not None:
    df = st.session_state.df
    total = len(df)
    idx = st.session_state.indice

    # Pula quem já está validado
    while idx < total and str(df.iloc[idx].get("Valida", "")).upper() in ["SIM", "NÃO"]:
        idx += 1
        st.session_state.indice = idx

    if idx < total:
        linha = df.iloc[idx]
        
        # Detecta coluna de URL com segurança
        col_url = None
        url_value = None
        for candidate in ["URL_Imagem", "URLImagem", "CAMINHO_LOCAL", "Imagem", "url", "URL"]:
            if candidate in df.columns:
                url_value = str(linha[candidate]).strip()
                if url_value and url_value.lower() != "nan" and url_value != "":
                    col_url = candidate
                    break
        
        # ===== HEADER COM PROGRESSO =====
        st.markdown(f"### 📊 Progresso: {idx+1} de {total}")
        progress_percent = (idx / total) * 100
        st.progress(progress_percent / 100)
        
        # ===== INFORMAÇÕES DO ITEM =====
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**ID:** {idx+1}")
            st.markdown(f"**Categoria:** {linha.get('Categoria', 'N/A')}")
        with col2:
            st.markdown(f"**Data:** {linha.get('Data', 'N/A')}")
            st.markdown(f"**CNPJ:** {linha.get('CNPJ', 'N/A')}")
        
        st.markdown("---")
        
        # ===== EXIBIÇÃO DE IMAGEM (9:16) =====
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
                
                # Exibe imagem centralizada
                col_img = st.columns()
                with col_img:
                    st.image(img, use_column_width=True)
                
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Erro ao baixar imagem (URL inválida ou servidor indisponível)")
            except FileNotFoundError:
                st.error(f"❌ Arquivo local não encontrado: {url_value}")
            except Exception as e:
                st.error(f"❌ Erro ao processar imagem: {e}")
        else:
            st.warning("⚠️ Sem URL válida nesta linha")

        st.markdown("---")
        
        # ===== FORMULÁRIO DE VALIDAÇÃO =====
        st.subheader("🔍 Validação")
        
        col_radio1, col_radio2 = st.columns(2)
        with col_radio1:
            valido = st.radio('Escolha uma opção:', ['Válida ✓', 'Inválida ✗'], key=f"radio_{idx}")
        
        motivos = []
        if valido == 'Inválida ✗':
            st.markdown("**Selecione o(s) motivo(s):**")
            col_cb1, col_cb2 = st.columns(2)
            with col_cb1:
                cb1 = st.checkbox('FRAUDE', key=f"cb1_{idx}")
                cb3 = st.checkbox('OUTRA CATEGORIA', key=f"cb3_{idx}")
            with col_cb2:
                cb2 = st.checkbox('NÃO É PÉ', key=f"cb2_{idx}")
                cb4 = st.checkbox('OUTRO PRODUTO', key=f"cb4_{idx}")
            
            if cb1: motivos.append('FRAUDE')
            if cb2: motivos.append('NÃO É PÉ')
            if cb3: motivos.append('OUTRA CATEGORIA')
            if cb4: motivos.append('OUTRO PRODUTO')
        
        # ===== BOTÕES DE AÇÃO =====
        st.markdown("---")
        col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
        
        with col_btn1:
            if st.button('⬅️ Voltar', key=f"voltar_{idx}", use_container_width=True):
                if idx > 0:
                    # Limpa validação anterior
                    prev_row = idx - 1
                    while prev_row >= 0 and str(df.iloc[prev_row].get("Valida", "")).upper() in ["SIM", "NÃO"]:
                        prev_row -= 1
                    
                    if prev_row >= 0:
                        df.at[prev_row, 'Valida'] = ""
                        df.at[prev_row, 'Motivos'] = ""
                        df.at[prev_row, 'Data_Validacao'] = ""
                        st.session_state.df = df
                        st.session_state.indice = prev_row
                        st.rerun()
        
        with col_btn2:
            if st.button('💾 Salvar Resposta', key=f"salvar_{idx}", use_container_width=True):
                if valido == 'Inválida ✗' and len(motivos) == 0:
                    st.error('❌ Selecione pelo menos um motivo para inválida!')
                else:
                    df.at[idx, 'Valida'] = 'SIM' if valido == 'Válida ✓' else 'NÃO'
                    df.at[idx, 'Motivos'] = '; '.join(motivos)
                    df.at[idx, 'Data_Validacao'] = str(datetime.now())
                    st.session_state.df = df
                    st.session_state.indice = idx + 1
                    st.success('✅ Resposta salva!')
                    st.rerun()
        
        with col_btn3:
            if st.button('➡️ Próxima', key=f"proxima_{idx}", use_container_width=True):
                st.session_state.indice = idx + 1
                st.rerun()
        
        with col_btn4:
            if st.button('📥 Baixar CSV', key=f"download_{idx}", use_container_width=True):
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Clique para baixar",
                    data=csv,
                    file_name=f"validadas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key=f"download_btn_{idx}"
                )

    else:
        st.success('✅ Finalizado! Todas as imagens foram validadas.')
        
        # Exibe resumo
        total_validadas = len(df[df['Valida'] == 'SIM'])
        total_invalidadas = len(df[df['Valida'] == 'NÃO'])
        
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.metric("Total Validadas", total_validadas, delta=f"{(total_validadas/(total_validadas+total_invalidadas)*100):.1f}%")
        with col_s2:
            st.metric("Total Inválidas", total_invalidadas)
        with col_s3:
            st.metric("Progresso", f"{total_validadas + total_invalidadas}/{total}")
        
        st.markdown("---")
        
        # Download final
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Baixar Resultado Final (CSV)",
            data=csv,
            file_name=f"validacao_completa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
        
        # Reiniciar
        if st.button("🔄 Reiniciar Validação", use_container_width=True):
            st.session_state.indice = 0
            st.rerun()

else:
    st.info('📤 Carregue um arquivo .csv ou .xlsx com colunas: URL_Imagem, Categoria, Data, CNPJ')
    st.markdown("""
    ### 📋 Formato esperado do arquivo:
    
    | URL_Imagem | Categoria | Data | CNPJ |
    |-----------|-----------|------|------|
    | https://... | Papel Higiênico | 19/11/2025 | 06057223050357 |
    | https://... | Papel Toalha | 18/11/2025 | 75315333050357 |
    """)
