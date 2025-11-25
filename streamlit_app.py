import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import requests
from io import BytesIO

# ===== CONFIGURAÇÃO DA PÁGINA =====
st.set_page_config(page_title="Validação de Imagens", layout="centered")
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
        
        # Limpeza de dados
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()
        
        df = df.fillna("")
        
        # Adiciona colunas de validação
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

    # ===== EXIBIÇÃO DO PROGRESSO =====
    st.markdown(f"### 📊 Progresso: {idx+1} de {total}")
    progress_percent = (idx / total) * 100 if total > 0 else 0
    st.progress(progress_percent / 100)

    if idx < total:
        linha = df.iloc[idx]
        
        # Detecta coluna de URL
        col_url = None
        url_value = None
        
        for candidate in ["URL_Imagem", "URLImagem", "CAMINHO_LOCAL", "Imagem", "url", "URL"]:
            if candidate in df.columns:
                url_value = str(linha[candidate]).strip()
                if url_value and url_value.lower() != "nan" and url_value != "":
                    col_url = candidate
                    break
        
        # ===== LAYOUT: IMAGEM + INFORMAÇÕES =====
        col_img, col_info = st.columns([1.5, 1])
        
        # --- COLUNA 1: IMAGEM ---
        with col_img:
            st.markdown("#### 🖼️ Imagem")
            
            if col_url and url_value:
                try:
                    # Garante que a URL comece com http
                    if not url_value.startswith("http"):
                        url_value = "https://" + url_value
                    
                    # Baixa a imagem
                    response = requests.get(url_value, timeout=20)
                    response.raise_for_status()
                    
                    # Abre e redimensiona a imagem (9:16)
                    img = Image.open(BytesIO(response.content))
                    
                    largura = 360
                    altura = int(largura * 16 / 9)  # 640
                    img_redimensionada = img.resize((largura, altura), Image.Resampling.LANCZOS)
                    
                    # Exibe a imagem
                    st.image(img_redimensionada, use_column_width=True)
                    
                except requests.exceptions.Timeout:
                    st.error("⏱️ Timeout ao baixar imagem. URL pode estar indisponível.")
                except requests.exceptions.HTTPError as e:
                    st.error(f"❌ Erro HTTP {response.status_code}: URL inválida ou sem permissão")
                except requests.exceptions.RequestException as e:
                    st.error(f"❌ Erro de rede: Verifique a URL e sua conexão")
                except Exception as e:
                    st.error(f"❌ Erro ao processar imagem: {str(e)[:100]}")
            else:
                st.warning("⚠️ Sem URL nesta linha")
        
        # --- COLUNA 2: INFORMAÇÕES ---
        with col_info:
            st.markdown("#### 📋 Dados")
            st.info(f"**ID:** {idx+1}")
            st.write(f"**Categoria:** {linha.get('Categoria', 'N/A')}")
            st.write(f"**Data:** {linha.get('Data', 'N/A')}")
            st.write(f"**CNPJ:** {linha.get('CNPJ', 'N/A')}")
            
            if col_url and url_value:
                with st.expander("🔗 Ver URL"):
                    st.code(url_value, language="text")

        st.markdown("---")

        # ===== FORMULÁRIO DE VALIDAÇÃO =====
        st.subheader("🔍 Validação")
        
        valido = st.radio('Escolha uma opção:', ['Válida ✓', 'Inválida ✗'], key=f"radio_{idx}")
        
        motivos = []
        if valido == 'Inválida ✗':
            st.markdown("**Selecione o(s) motivo(s):**")
            col_cb1, col_cb2 = st.columns(2)
            with col_cb1:
                if st.checkbox('FRAUDE', key=f"cb1_{idx}"):
                    motivos.append('FRAUDE')
                if st.checkbox('OUTRA CATEGORIA', key=f"cb3_{idx}"):
                    motivos.append('OUTRA CATEGORIA')
            with col_cb2:
                if st.checkbox('NÃO É PÉ', key=f"cb2_{idx}"):
                    motivos.append('NÃO É PÉ')
                if st.checkbox('OUTRO PRODUTO', key=f"cb4_{idx}"):
                    motivos.append('OUTRO PRODUTO')

        st.markdown("---")

        # ===== BOTÕES DE AÇÃO =====
        col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
        
        with col_btn1:
            if st.button('⬅️ Voltar', key=f"voltar_{idx}", use_container_width=True):
                if idx > 0:
                    # Limpa validação anterior
                    df.at[idx-1, 'Valida'] = ""
                    df.at[idx-1, 'Motivos'] = ""
                    df.at[idx-1, 'Data_Validacao'] = ""
                    st.session_state.df = df
                    st.session_state.indice = idx - 1
                    st.rerun()
        
        with col_btn2:
            if st.button('💾 Salvar', key=f"salvar_{idx}", use_container_width=True):
                if valido == 'Inválida ✗' and len(motivos) == 0:
                    st.error('❌ Selecione pelo menos um motivo!')
                else:
                    df.at[idx, 'Valida'] = 'SIM' if valido == 'Válida ✓' else 'NÃO'
                    df.at[idx, 'Motivos'] = '; '.join(motivos) if motivos else ""
                    df.at[idx, 'Data_Validacao'] = str(datetime.now())
                    st.session_state.df = df
                    st.session_state.indice = idx + 1
                    st.success('✅ Salvo!')
                    st.rerun()
        
        with col_btn3:
            if st.button('➡️ Próxima', key=f"proxima_{idx}", use_container_width=True):
                st.session_state.indice = idx + 1
                st.rerun()
        
        with col_btn4:
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Baixar",
                data=csv,
                file_name=f"validadas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key=f"download_{idx}",
                use_container_width=True
            )

    else:
        # ===== RESUMO FINAL =====
        st.success('✅ Validação Concluída!')
        
        total_validas = len(df[df['Valida'] == 'SIM'])
        total_invalidas = len(df[df['Valida'] == 'NÃO'])
        
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.metric("✅ Válidas", total_validas)
        with col_s2:
            st.metric("❌ Inválidas", total_invalidas)
        with col_s3:
            taxa = (total_validas / (total_validas + total_invalidas) * 100) if (total_validas + total_invalidas) > 0 else 0
            st.metric("Taxa", f"{taxa:.1f}%")

        st.markdown("---")

        # Download final
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Baixar Resultado Completo",
            data=csv,
            file_name=f"validacao_completa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

        # Reiniciar
        if st.button("🔄 Reiniciar", use_container_width=True):
            st.session_state.indice = 0
            st.rerun()

else:
    st.info('📤 Carregue um arquivo .csv ou .xlsx')
    st.markdown("""
    ### 📋 Formato esperado:
    
    | URL_Imagem | Categoria | Data | CNPJ |
    |-----------|-----------|------|------|
    | https://... | Papel Higiênico | 19/11/2025 | 06057223050357 |
    """)
