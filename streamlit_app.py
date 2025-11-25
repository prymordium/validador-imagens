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
        try:
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
        except:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=';')
    else:
        df = pd.read_excel(uploaded_file)

    st.write("**Colunas detectadas no arquivo:**", df.columns.tolist())
    st.write(f"**Total de linhas:** {len(df)}")
    
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

    # ===== BARRA SUPERIOR COM NAVEGAÇÃO RÁPIDA =====
    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    
    with col_nav1:
        total_validadas = len(df[df['Valida'].isin(['SIM', 'NÃO'])])
        progresso = total_validadas / total if total > 0 else 0
        st.metric("Progresso", f"{total_validadas}/{total}")
    
    with col_nav2:
        st.progress(progresso)
    
    with col_nav3:
        # Saltador de linha
        linha_saltar = st.number_input(
            "Ir para linha:",
            min_value=1,
            max_value=total,
            value=idx + 1,
            key="nav_input"
        )
        if linha_saltar != idx + 1:
            st.session_state.indice = linha_saltar - 1
            st.rerun()

    st.divider()

    # ===== DOWNLOADS (sempre visível) =====
    st.markdown("### 📥 Opções de Download")
    col_down1, col_down2 = st.columns(2)
    
    with col_down1:
        csv_completa = df.to_csv(index=False, sep=";")
        st.download_button(
            label="📥 Base COMPLETA (continuar depois)",
            data=csv_completa,
            file_name=f"validacao_resultado_{datetime.now().strftime('%d_%m_%Y_%H%M%S')}.csv",
            mime="text/csv",
            help="Baixe para continuar validação depois"
        )
    
    with col_down2:
        df_validados = df[df['Valida'].isin(['SIM', 'NÃO'])].copy()
        csv_validados = df_validados.to_csv(index=False, sep=";")
        st.download_button(
            label="✅ Apenas VALIDADAS",
            data=csv_validados,
            file_name=f"validadas_{datetime.now().strftime('%d_%m_%Y_%H%M%S')}.csv",
            mime="text/csv",
            help="Apenas imagens já validadas"
        )
    
    st.divider()

    if idx < total:
        linha = df.iloc[idx]
        
        # ===== DEBUG: Mostra TODAS as colunas e valores =====
        with st.expander("🔍 DEBUG - Colunas e Valores"):
            st.write("**Todas as colunas do DataFrame:**")
            st.write(df.columns.tolist())
            st.write("**Valores da linha atual:**")
            for col in df.columns:
                st.write(f"- {col}: `{linha[col]}`")
        
        # Normaliza nomes das colunas
        colunas_normalizadas = {col.strip().lower(): col for col in df.columns}
        
        col_url = None
        col_categoria = None
        col_data = None
        col_cnpj = None
        
        for candidate in ["url_imagem", "url", "imagem", "link", "caminho_local", "image", "url_da_imagem"]:
            if candidate in colunas_normalizadas:
                col_url = colunas_normalizadas[candidate]
                st.info(f"✅ Coluna de URL detectada: `{col_url}`")
                break
        
        if not col_url:
            st.error("❌ Nenhuma coluna de URL detectada! Colunas disponíveis: " + str(df.columns.tolist()))
        
        for candidate in ["categoria", "category", "categoria_item"]:
            if candidate in colunas_normalizadas:
                col_categoria = colunas_normalizadas[candidate]
                break
        
        for candidate in ["data", "date", "data_envio"]:
            if candidate in colunas_normalizadas:
                col_data = colunas_normalizadas[candidate]
                break
        
        for candidate in ["cnpj", "fornecedor", "supplier"]:
            if candidate in colunas_normalizadas:
                col_cnpj = colunas_normalizadas[candidate]
                break

        # Verifica se tem imagem com debugging completo
        tem_imagem = False
        url_imagem = ""
        erro_imagem = ""
        
        if col_url:
            valor_bruto = linha[col_url]
            st.write(f"**Valor bruto da coluna URL:** `{repr(valor_bruto)}`")
            st.write(f"**Tipo:** {type(valor_bruto)}")
            
            if pd.notna(valor_bruto):
                url_imagem = str(valor_bruto).strip()
                st.write(f"**URL após tratamento:** `{url_imagem}`")
                
                if url_imagem and url_imagem.lower() != "nan" and url_imagem != "":
                    try:
                        if url_imagem.startswith("http://") or url_imagem.startswith("https://"):
                            st.write(f"📡 **Tentando carregar de URL:** `{url_imagem}`")
                            response = requests.get(url_imagem, timeout=15, allow_redirects=True)
                            response.raise_for_status()
                            
                            content_type = response.headers.get('content-type', '')
                            st.write(f"**Content-Type:** {content_type}")
                            st.write(f"**Status Code:** {response.status_code}")
                            st.write(f"**Tamanho:** {len(response.content)} bytes")
                            
                            img = Image.open(BytesIO(response.content))
                            tem_imagem = True
                            st.success("✅ Imagem carregada com sucesso!")
                        else:
                            st.write(f"📁 **Tentando carregar arquivo local:** `{url_imagem}`")
                            try:
                                img = Image.open(url_imagem)
                                tem_imagem = True
                                st.success("✅ Imagem local carregada com sucesso!")
                            except FileNotFoundError:
                                erro_imagem = f"Arquivo não encontrado: {url_imagem}"
                    except requests.exceptions.MissingSchema:
                        erro_imagem = f"URL inválida (falta http/https): {url_imagem}"
                    except requests.exceptions.ConnectionError:
                        erro_imagem = f"Erro de conexão ao acessar: {url_imagem}"
                    except requests.exceptions.Timeout:
                        erro_imagem = f"Timeout ao carregar imagem (URL muito lenta)"
                    except requests.exceptions.HTTPError as e:
                        erro_imagem = f"Erro HTTP {response.status_code}: {url_imagem}"
                    except Exception as e:
                        erro_imagem = f"Erro: {type(e).__name__}: {str(e)}"
                else:
                    erro_imagem = "URL vazia ou inválida (NaN)"
            else:
                erro_imagem = "Valor da URL é vazio (NaN)"
        else:
            erro_imagem = "Coluna de URL não foi detectada"

        st.divider()

        # Layout
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"## Imagem {idx+1} de {total}")
            
            if tem_imagem:
                try:
                    largura = 360
                    altura = int(largura * 16 / 9)
                    img = img.resize((largura, altura))
                    st.image(img, use_column_width=True)
                except Exception as e:
                    st.error(f"❌ Erro ao redimensionar: {str(e)}")
            elif erro_imagem:
                st.error(f"❌ {erro_imagem}")
            else:
                st.warning("⚠️ Sem imagem nesta linha")
        
        with col2:
            st.markdown("### Informações do Item")
            
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
        
        if not tem_imagem:
            valido = "Inválida ✗"
            st.info("ℹ️ Como não há imagem, esta validação foi marcada automaticamente como **Inválida**.")
            motivo_selecionado = "SEM IMAGEM"
            st.markdown(f"**Motivo registrado:** {motivo_selecionado}")
            
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            
            with col_btn1:
                btn_salvar = st.button('✓ Salvar resposta', use_container_width=True, key=f"btn_salvar_{idx}")
            with col_btn2:
                btn_voltar = st.button('← Voltar', use_container_width=True, key=f"btn_voltar_{idx}")
            with col_btn3:
                btn_proximo = st.button('→ Próxima', use_container_width=True, key=f"btn_proximo_{idx}")

            if btn_salvar:
                df.at[idx, 'Valida'] = 'NÃO'
                df.at[idx, 'Motivos'] = motivo_selecionado
                df.at[idx, 'Data_Validacao'] = str(datetime.now())
                st.session_state.indice = idx + 1
                st.session_state.df = df
                st.success('✅')
            
            if btn_voltar:
                if idx > 0:
                    st.session_state.indice = idx - 1
                else:
                    st.warning("⚠️ Primeira imagem")
            
            if btn_proximo:
                st.session_state.indice = idx + 1
        
        else:
            valido = st.radio('Selecione a validação:', ['Válida ✓', 'Inválida ✗'], key=f"radio_{idx}")
            
            motivo_selecionado = None
            if valido == 'Inválida ✗':
                st.markdown("**Selecione o motivo:**")
                motivos_opcoes = ['FRAUDE', 'NÃO É PÉ', 'OUTRA CATEGORIA', 'OUTRO PRODUTO']
                motivo_selecionado = st.radio(
                    'Motivos:',
                    motivos_opcoes,
                    key=f"motivos_{idx}",
                    label_visibility="collapsed"
                )
            
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            
            with col_btn1:
                btn_salvar = st.button('✓ Salvar resposta', use_container_width=True, key=f"btn_salvar_{idx}")
            with col_btn2:
                btn_voltar = st.button('← Voltar', use_container_width=True, key=f"btn_voltar_{idx}")
            with col_btn3:
                btn_proximo = st.button('→ Próxima', use_container_width=True, key=f"btn_proximo_{idx}")

            if btn_salvar:
                if valido == 'Inválida ✗' and motivo_selecionado is None:
                    st.error('⚠️ Selecione um motivo!')
                else:
                    df.at[idx, 'Valida'] = 'SIM' if valido == 'Válida ✓' else 'NÃO'
                    df.at[idx, 'Motivos'] = motivo_selecionado if motivo_selecionado else ""
                    df.at[idx, 'Data_Validacao'] = str(datetime.now())
                    st.session_state.indice = idx + 1
                    st.session_state.df = df
                    st.success('✅')
            
            if btn_voltar:
                if idx > 0:
                    st.session_state.indice = idx - 1
                else:
                    st.warning("⚠️ Primeira imagem")
            
            if btn_proximo:
                st.session_state.indice = idx + 1

    else:
        st.success
