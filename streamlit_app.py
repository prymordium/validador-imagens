import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import requests
from io import BytesIO

st.set_page_config(page_title="Validação de Imagens", layout="wide")
st.title("Validador de Imagens")

uploaded_file = st.file_uploader("Faça upload do arquivo de imagens (.csv, .xlsx)", type=["csv", "xlsx"])

if "indice" not in st.session_state:
    st.session_state.indice = 0
if "df" not in st.session_state:
    st.session_state.df = None

if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        try:
            df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='utf-8')
        except:
            uploaded_file.seek(0)
            try:
                df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8')
            except:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=',', encoding='latin-1')
    else:
        df = pd.read_excel(uploaded_file)

    st.write("**Colunas detectadas:**", df.columns.tolist())
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

    while idx < total and str(df.iloc[idx].get("Valida", "")).upper() in ["SIM", "NÃO"]:
        idx += 1

    # Barra de navegação
    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    with col_nav1:
        total_validadas = len(df[df['Valida'].isin(['SIM', 'NÃO'])])
        progresso = total_validadas / total if total > 0 else 0
        st.metric("Progresso", f"{total_validadas}/{total}")
    with col_nav2:
        st.progress(progresso)
    with col_nav3:
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

    # Downloads
    st.markdown("### 📥 Opções de Download")
    col_down1, col_down2 = st.columns(2)
    with col_down1:
        csv_completa = df.to_csv(index=False, sep=";", encoding='utf-8-sig')
        st.download_button(
            label="📥 Base COMPLETA",
            data=csv_completa,
            file_name=f"validacao_{datetime.now().strftime('%d_%m_%Y_%H%M%S')}.csv",
            mime="text/csv"
        )
    with col_down2:
        df_validados = df[df['Valida'].isin(['SIM', 'NÃO'])].copy()
        csv_validados = df_validados.to_csv(index=False, sep=";", encoding='utf-8-sig')
        st.download_button(
            label="✅ Apenas VALIDADAS",
            data=csv_validados,
            file_name=f"validadas_{datetime.now().strftime('%d_%m_%Y_%H%M%S')}.csv",
            mime="text/csv"
        )
    st.divider()

    if idx < total:
        linha = df.iloc[idx]
        col_url = "URL_Imagem" if "URL_Imagem" in df.columns else None
        col_categoria = "Categoria" if "Categoria" in df.columns else None
        col_data = "Data" if "Data" in df.columns else None
        col_cnpj = "CNPJ" if "CNPJ" in df.columns else None

        # Carrega imagem
        tem_imagem = False
        url_imagem = ""
        erro_imagem = ""
        img = None
        
        if col_url and pd.notna(linha[col_url]):
            url_imagem = str(linha[col_url]).strip()
            
            # Limpeza da URL
            if url_imagem and url_imagem.lower() != "nan" and url_imagem != "":
                # Garantir protocolo HTTPS
                if not (url_imagem.startswith("http://") or url_imagem.startswith("https://")):
                    url_imagem = "https://" + url_imagem
                
                try:
                    # Headers para simular navegador e evitar bloqueios
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Connection': 'keep-alive',
                    }
                    
                    # Requisição com timeout maior e headers
                    response = requests.get(
                        url_imagem, 
                        timeout=30, 
                        allow_redirects=True,
                        headers=headers,
                        verify=True  # Verificar SSL
                    )
                    response.raise_for_status()
                    
                    # Verificar se é realmente uma imagem
                    content_type = response.headers.get('content-type', '')
                    if 'image' not in content_type.lower() and len(response.content) < 100:
                        erro_imagem = f"URL não retorna imagem válida (tipo: {content_type})"
                    else:
                        img = Image.open(BytesIO(response.content))
                        # Converter para RGB se necessário
                        if img.mode in ('RGBA', 'LA', 'P'):
                            img = img.convert('RGB')
                        tem_imagem = True
                        
                except requests.exceptions.Timeout:
                    erro_imagem = "⏱️ Timeout: Servidor demorou muito para responder"
                except requests.exceptions.ConnectionError:
                    erro_imagem = "🔌 Erro de conexão: Não foi possível conectar ao servidor"
                except requests.exceptions.HTTPError as e:
                    erro_imagem = f"❌ HTTP {e.response.status_code}: {e.response.reason}"
                except requests.exceptions.SSLError:
                    erro_imagem = "🔒 Erro SSL: Certificado inválido ou problema de segurança"
                except Exception as e:
                    erro_imagem = f"⚠️ Erro: {str(e)[:100]}"
            else:
                erro_imagem = "URL vazia ou inválida"
        else:
            erro_imagem = "Coluna URL_Imagem não encontrada"

        # Layout
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"## Imagem {idx+1} de {total}")
            if tem_imagem and img:
                try:
                    # Redimensionar mantendo proporção 9:16 (vertical)
                    largura = 360
                    altura = int(largura * 16 / 9)
                    img_resized = img.resize((largura, altura), Image.Resampling.LANCZOS)
                    st.image(img_resized, use_container_width=False)
                except Exception as e:
                    st.error(f"Erro ao processar imagem: {str(e)}")
                    st.code(f"URL: {url_imagem}", language=None)
            elif erro_imagem:
                st.error(f"❌ {erro_imagem}")
                st.code(f"URL: {url_imagem}", language=None)
                # Botão para testar URL no navegador
                st.markdown(f"[🔗 Testar URL no navegador]({url_imagem})")
            else:
                st.warning("⚠️ Sem imagem disponível")
        
        with col2:
            st.markdown("### Informações do Item")
            if col_url:
                url_val = str(linha[col_url]) if pd.notna(linha[col_url]) else "N/A"
                st.text_area("**URL:**", url_val, height=80, disabled=True)
            if col_categoria:
                cat = str(linha[col_categoria]) if pd.notna(linha[col_categoria]) else "N/A"
                st.text_input("**Categoria:**", cat, disabled=True)
            if col_data:
                data = str(linha[col_data]) if pd.notna(linha[col_data]) else "N/A"
                st.text_input("**Data:**", data, disabled=True)
            if col_cnpj:
                cnpj = str(linha[col_cnpj]) if pd.notna(linha[col_cnpj]) else "N/A"
                st.text_input("**CNPJ:**", cnpj, disabled=True)

        st.divider()
        st.markdown("### Validação")
        
        if not tem_imagem:
            st.info("ℹ️ Marcado como **Inválida** (sem imagem)")
            motivo_selecionado = "SEM IMAGEM"
            st.markdown(f"**Motivo:** {motivo_selecionado}")
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            with col_btn1:
                if st.button('✔ Salvar', use_container_width=True, key=f"btn_s_{idx}"):
                    df.at[idx, 'Valida'] = 'NÃO'
                    df.at[idx, 'Motivos'] = motivo_selecionado
                    df.at[idx, 'Data_Validacao'] = str(datetime.now())
                    st.session_state.indice = idx + 1
                    st.session_state.df = df
                    st.rerun()
            with col_btn2:
                if st.button('← Voltar', use_container_width=True, key=f"btn_v_{idx}"):
                    if idx > 0:
                        st.session_state.indice = idx - 1
                        st.rerun()
            with col_btn3:
                if st.button('→ Próxima', use_container_width=True, key=f"btn_p_{idx}"):
                    st.session_state.indice = idx + 1
                    st.rerun()
        else:
            valido = st.radio('Validação:', ['Válida ✔', 'Inválida ✗'], key=f"radio_{idx}")
            motivo_selecionado = None
            if valido == 'Inválida ✗':
                st.markdown("**Selecione motivo:**")
                motivos_opcoes = ['FRAUDE', 'NÃO É PÉ', 'OUTRA CATEGORIA', 'OUTRO PRODUTO']
                motivo_selecionado = st.radio(
                    'M:',
                    motivos_opcoes,
                    key=f"mot_{idx}",
                    label_visibility="collapsed"
                )
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            with col_btn1:
                if st.button('✔ Salvar', use_container_width=True, key=f"btn_s_{idx}"):
                    if valido == 'Inválida ✗' and motivo_selecionado is None:
                        st.error('Selecione um motivo!')
                    else:
                        df.at[idx, 'Valida'] = 'SIM' if valido == 'Válida ✔' else 'NÃO'
                        df.at[idx, 'Motivos'] = motivo_selecionado if motivo_selecionado else ""
                        df.at[idx, 'Data_Validacao'] = str(datetime.now())
                        st.session_state.indice = idx + 1
                        st.session_state.df = df
                        st.rerun()
            with col_btn2:
                if st.button('← Voltar', use_container_width=True, key=f"btn_v_{idx}"):
                    if idx > 0:
                        st.session_state.indice = idx - 1
                        st.rerun()
            with col_btn3:
                if st.button('→ Próxima', use_container_width=True, key=f"btn_p_{idx}"):
                    st.session_state.indice = idx + 1
                    st.rerun()

    else:
        st.success('✅ Todas as imagens foram validadas!')
        total_validas = len(df[df['Valida'] == 'SIM'])
        total_invalidas = len(df[df['Valida'] == 'NÃO'])
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("Total Validadas", total_validadas)
        with col_stat2:
            st.metric("Válidas", total_validas)
        with col_stat3:
            st.metric("Inválidas", total_invalidas)
        st.dataframe(df, use_container_width=True)
        if st.button("🔄 Reiniciar"):
            st.session_state.indice = 0
            st.rerun()
else:
    st.info('📤 Carregue um CSV ou XLSX com: URL_Imagem, Categoria, Data, CNPJ')
