import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import requests
from io import BytesIO

# ===== CONFIGURAÇÃO DA PÁGINA =====
st.set_page_config(page_title="Validação de Imagens", layout="wide")
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
        
        # ===== LAYOUT: IMAGEM + INFORMAÇÕES (FLUTUADOR) =====
        col_img, col_info = st.columns([2, 1], gap="large")
        
        # --- COLUNA 1: IMAGEM (MAIOR) ---
        with col_img:
            st.markdown("#### 🖼️ Imagem da Validação")
            
            if col_url and url_value:
                try:
                    # Garante que a URL comece com http
                    if not url_value.startswith("http"):
                        url_value = "https://" + url_value
                    
                    st.write(f"🔗 Carregando: `{url_value[:80]}...`")
                    
                    # Baixa a imagem com timeout maior
                    response = requests.get(url_value, timeout=30)
                    response.raise_for_status()
                    
                    # Abre a imagem
                    img = Image.open(BytesIO(response.content))
                    
                    # Redimensiona para 9:16 (vertical)
                    largura = 500  # Aumentado para melhor visualização
                    altura = int(largura * 16 / 9)  # 888
                    img_redimensionada = img.resize((largura, altura), Image.Resampling.LANCZOS)
                    
                    # ===== EXIBE A IMAGEM EM CONTAINER =====
                    st.image(img_redimensionada, use_column_width=True, caption=f"ID: {idx+1}")
                    
                    st.success("✅ Imagem carregada com sucesso!")
                    
                except requests.exceptions.Timeout:
                    st.error("⏱️ Timeout: URL indisponível ou muito lenta")
                except requests.exceptions.HTTPError as e:
                    st.error(f"❌ Erro HTTP {response.status_code}: URL inválida")
                except requests.exceptions.RequestException as e:
                    st.error(f"❌ Erro de rede: {str(e)[:100]}")
                except Exception as e:
                    st.error(f"❌ Erro ao processar imagem: {str(e)[:100]}")
            else:
                st.warning("⚠️ Sem URL nesta linha")
        
        # --- COLUNA 2: INFORMAÇÕES (FLUTUADOR) ---
        with col_info:
            st.markdown("#### 📋 Informações")
            
            # Card com informações
            st.info(f"**ID da Imagem:**\n{idx+1}")
            
            info_items = {
                "Categoria": linha.get('Categoria', 'N/A'),
                "Data": linha.get('Data', 'N/A'),
                "CNPJ": linha.get('CNPJ', 'N/A')
            }
            
            for label, valor in info_items.items():
                st.write(f"**{label}:**")
                st.write(valor)
                st.divider()
            
            if col_url and url_value:
                with st.expander("🔗 Ver URL Completa"):
                    st.code(url_value, language="text")

        st.markdown("---")

        # ===== FORMULÁRIO DE VALIDAÇÃO =====
        st.subheader("🔍 Validação")
        
        col_val1, col_val2 = st.columns(2)
        
        with col_val1:
            valido = st.radio('Escolha uma opção:', 
                             ['Válida ✓', 'Inválida ✗'], 
                             key=f"radio_{idx}")
        
        motivos = []
        with col_val2:
            if valido == 'Inválida ✗':
                st.write("**Motivo(s):**")
                if st.checkbox('FRAUDE', key=f"cb1_{idx}"):
                    motivos.append('FRAUDE')
                if st.checkbox('NÃO É PÉ', key=f"cb2_{idx}"):
                    motivos.append('NÃO É PÉ')
                if st.checkbox('OUTRA CATEGORIA', key=f"cb3_{idx}"):
                    motivos.append('OUTRA CATEGORIA')
                if st.checkbox('OUTRO PRODUTO', key=f"cb4_{idx}"):
                    motivos.append('OUTRO PRODUTO')

        st.markdown("---")

        # ===== BOTÕES DE AÇÃO =====
        col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
        
        with col_btn1:
            if st.button('⬅️ Voltar', key=f"voltar_{idx}", use_container_width=True):
                if idx > 0:
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
                    st.success('✅ Salvo com sucesso!')
                    st.rerun()
        
        with col_btn3:
            if st.button('➡️ Próxima', key=f"proxima_{idx}", use_container_width=True):
                st.session_state.indice = idx + 1
                st.rerun()
        
        with col_btn4:
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Baixar CSV",
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
            st.metric("Taxa Aprovação", f"{taxa:.1f}%")

        st.markdown("---")

        col_d1, col_d2 = st.columns(2)
        
        with col_d1:
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Baixar Todas",
                data=csv,
                file_name=f"validacao_completa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col_d2:
            if st.button("🔄 Reiniciar", use_container_width=True):
                st.session_state.indice = 0
                st.rerun()

else:
    st.info('📤 Carregue um arquivo .csv ou .xlsx')
    st.markdown("""
    ### 📋 Formato esperado:
    
    | URL_Imagem | Categoria | Data | CNPJ |
    |-----------|-----------|------|------|
    | https://promo-app-v1.s3.amazonaws.com/... | Papel Higiênico | 19/11/2025 | 06057223050357 |
    """)
