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
        # Pandas detecta automaticamente o separador
        try:
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
        except:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=';')
    else:
        df = pd.read_excel(uploaded_file)

    st.write("**Colunas detectadas no arquivo:**", df.columns.tolist())
    st.write(f"**Total de linhas:** {len(df)}")
    
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
        
        # Detecta nomes de coluna flexivelmente (remove espaços)
        col_url = None
        col_categoria = None
        col_data = None
        col_cnpj = None
        
        # Normaliza nomes das colunas
        colunas_normalizadas = {col.strip().lower(): col for col in df.columns}
        
        # Busca URL/Imagem
        for candidate in ["url_imagem", "url", "imagem", "link", "caminho_local"]:
            if candidate in colunas_normalizadas:
                col_url = colunas_normalizadas[candidate]
                break
        
        # Busca Categoria
        for candidate in ["categoria", "category", "categoria_item"]:
            if candidate in colunas_normalizadas:
                col_categoria = colunas_normalizadas[candidate]
                break
        
        # Busca Data
        for candidate in ["data", "date", "data_envio"]:
            if candidate in colunas_normalizadas:
                col_data = colunas_normalizadas[candidate]
                break
        
        # Busca CNPJ
        for candidate in ["cnpj", "fornecedor", "supplier"]:
            if candidate in colunas_normalizadas:
                col_cnpj = colunas_normalizadas[candidate]
                break

        # Verifica se tem imagem
        tem_imagem = False
        if col_url and str(linha[col_url]).strip():
            try:
                url_imagem = str(linha[col_url]).strip()
                if "http" in url_imagem:
                    resp = requests.get(url_imagem, timeout=15)
                    img = Image.open(BytesIO(resp.content))
                else:
                    img = Image.open(url_imagem)
                tem_imagem = True
            except Exception as e:
                tem_imagem = False

        # Layout com imagem em destaque
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"## Imagem {idx+1} de {total}")
            
            # Imagem da web ou local
            if tem_imagem:
                try:
                    url_imagem = str(linha[col_url]).strip()
                    if "http" in url_imagem:
                        resp = requests.get(url_imagem, timeout=15)
                        img = Image.open(BytesIO(resp.content))
                    else:
                        img = Image.open(url_imagem)
                    
                    # Resize para 9:16 (vertical)
                    largura = 360
                    altura = int(largura * 16 / 9)  # 360 x 640
                    img = img.resize((largura, altura))
                    st.image(img, use_column_width=True)
                except Exception as e:
                    st.error(f"❌ Erro ao carregar imagem: {e}")
            else:
                st.warning("⚠️ Sem imagem nesta linha")
        
        with col2:
            st.markdown("### Informações do Item")
            
            # Exibe dados com fallback se vazios
            if col_url:
                url_val = str(linha[col_url]) if pd.notna(linha[col_url]) else "N/A"
                st.text_area("**URL/Caminho:**", url_val, height=60, disabled=True)
            
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
        
        # Se não tem imagem, força Inválido
        if not tem_imagem:
            valido = "Inválida ✗"
            st.info("ℹ️ Como não há imagem, esta validação foi marcada automaticamente como **Inválida**.")
            motivo_selecionado = "SEM IMAGEM"
            
            st.markdown(f"**Motivo registrado:** {motivo_selecionado}")
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                btn_salvar = st.button('✓ Salvar resposta', use_container_width=True, key=f"btn_salvar_{idx}")
            
            with col_btn2:
                btn_proximo = st.button('→ Próxima imagem', use_container_width=True, key=f"btn_proximo_{idx}")

            if btn_salvar:
                df.at[idx, 'Valida'] = 'NÃO'
                df.at[idx, 'Motivos'] = motivo_selecionado
                df.at[idx, 'Data_Validacao'] = str(datetime.now())
                st.session_state.indice = idx + 1
                st.session_state.df = df
                st.success('✅ Resposta salva com sucesso!')
                st.balloons()
            
            if btn_proximo:
                st.session_state.indice = idx + 1
        
        else:
            # Se tem imagem, permite seleção normal
            valido = st.radio('Selecione a validação:', ['Válida ✓', 'Inválida ✗'], key=f"radio_{idx}")
            
            motivo_selecionado = None
            if valido == 'Inválida ✗':
                st.markdown("**Selecione o motivo (apenas 1):**")
                motivos_opcoes = ['FRAUDE', 'NÃO É PÉ', 'OUTRA CATEGORIA', 'OUTRO PRODUTO']
                motivo_selecionado = st.radio(
                    'Motivos:',
                    motivos_opcoes,
                    key=f"motivos_{idx}",
                    label_visibility="collapsed"
                )
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                btn_salvar = st.button('✓ Salvar resposta', use_container_width=True, key=f"btn_salvar_{idx}")
            
            with col_btn2:
                btn_proximo = st.button('→ Próxima imagem', use_container_width=True, key=f"btn_proximo_{idx}")

            if btn_salvar:
                if valido == 'Inválida ✗' and motivo_selecionado is None:
                    st.error('⚠️ Selecione um motivo para marcar como inválida!')
                else:
                    df.at[idx, 'Valida'] = 'SIM' if valido == 'Válida ✓' else 'NÃO'
                    df.at[idx, 'Motivos'] = motivo_selecionado if motivo_selecionado else ""
                    df.at[idx, 'Data_Validacao'] = str(datetime.now())
                    st.session_state.indice = idx + 1
                    st.session_state.df = df
                    st.success('✅ Resposta salva com sucesso!')
                    st.balloons()
            
            if btn_proximo:
                st.session_state.indice = idx + 1

    else:
        st.success('✅ Finalizado! Todas as imagens já foram validadas.')
        st.dataframe(st.session_state.df, use_container_width=True)
        
        # Download do resultado
        csv = st.session_state.df.to_csv(index=False, sep=";")
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
