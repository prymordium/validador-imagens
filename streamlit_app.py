import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import requests
from io import BytesIO

st.set_page_config(page_title="Validação de Imagens", layout="wide")
st.title("Validador de Imagens")

# Inicializar session_state
if "indice" not in st.session_state:
    st.session_state.indice = 0
if "df" not in st.session_state:
    st.session_state.df = None
if "uploaded_file_id" not in st.session_state:
    st.session_state.uploaded_file_id = None

uploaded_file = st.file_uploader("Faça upload do arquivo de imagens (.csv, .xlsx)", type=["csv", "xlsx"])

# Carregar arquivo apenas uma vez
if uploaded_file is not None:
    file_id = uploaded_file.file_id
    
    # Se é um novo arquivo, recarregar
    if st.session_state.uploaded_file_id != file_id:
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
        
        # Mostrar amostra das primeiras linhas para debug
        with st.expander("🔍 Ver amostra dos dados"):
            st.dataframe(df.head(3))
        
        # Adicionar colunas de validação se não existirem
        for col in ["Valida", "Motivos", "Data_Validacao"]:
            if col not in df.columns:
                df[col] = ""
        
        # Converter colunas para string para evitar problemas
        df['Valida'] = df['Valida'].astype(str)
        df['Motivos'] = df['Motivos'].astype(str)
        df['Data_Validacao'] = df['Data_Validacao'].astype(str)

        st.session_state.df = df
        st.session_state.uploaded_file_id = file_id
        st.session_state.indice = 0

# Usar o DataFrame do session_state
if st.session_state.df is not None:
    df = st.session_state.df
    total = len(df)
    idx = st.session_state.indice

    # Função para verificar se está validada
    def esta_validada(row):
        val = str(row.get("Valida", "")).strip()
        return val != "" and val != "nan"

    # Pular imagens já validadas APENAS se não estamos em navegação manual
    if "navegacao_manual" not in st.session_state:
        st.session_state.navegacao_manual = False
    
    if not st.session_state.navegacao_manual:
        while idx < total and esta_validada(df.iloc[idx]):
            idx += 1
    
    # Resetar flag de volta - REMOVIDO para manter estado na interação
    # st.session_state.voltando = False
    
    # Atualizar índice
    if idx != st.session_state.indice:
        st.session_state.indice = idx

    # Calcular progresso
    total_validadas = sum(df.apply(esta_validada, axis=1))
    progresso = total_validadas / total if total > 0 else 0

    # Barra de navegação
    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    with col_nav1:
        st.metric("Progresso", f"{total_validadas}/{total}")
    with col_nav2:
        st.progress(progresso)
    with col_nav3:
        linha_saltar = st.number_input(
            "Ir para linha:",
            min_value=1,
            max_value=total,
            value=idx + 1,
            key=f"nav_input_{idx}"
        )
        if st.button("Ir", key=f"btn_ir_{idx}"):
            st.session_state.indice = linha_saltar - 1
            st.session_state.navegacao_manual = True
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
            mime="text/csv",
            key=f"down_completa_{idx}"
        )
    with col_down2:
        df_validados = df[df.apply(esta_validada, axis=1)].copy()
        csv_validados = df_validados.to_csv(index=False, sep=";", encoding='utf-8-sig')
        st.download_button(
            label="✅ Apenas VALIDADAS",
            data=csv_validados,
            file_name=f"validadas_{datetime.now().strftime('%d_%m_%Y_%H%M%S')}.csv",
            mime="text/csv",
            key=f"down_validadas_{idx}"
        )
    st.divider()

    if idx < total:
        linha = df.iloc[idx]
        
        # Detectar coluna de URL
        col_url = None
        possiveis_urls = ['URL_Imagem', 'url_imagem', 'URL', 'url', 'link', 'Link', 'image_url', 'imagem']
        for col in possiveis_urls:
            if col in df.columns:
                col_url = col
                break
        
        if not col_url:
            for col in df.columns:
                if 'url' in col.lower() or 'link' in col.lower():
                    col_url = col
                    break
        
        if not col_url:
            for col in df.columns:
                amostra = str(df[col].iloc[0]) if len(df) > 0 else ""
                if amostra.startswith('http://') or amostra.startswith('https://'):
                    col_url = col
                    break
        
        col_categoria = "Categoria" if "Categoria" in df.columns else None
        col_data = "Data" if "Data" in df.columns else None
        col_cnpj = "CNPJ" if "CNPJ" in df.columns else None

        # Carrega imagem
        tem_imagem = False
        url_imagem = ""
        erro_imagem = ""
        img = None
        
        if col_url:
            st.info(f"📍 Coluna de URL detectada: **{col_url}**")
        else:
            st.error(f"❌ Nenhuma coluna de URL encontrada. Colunas disponíveis: {df.columns.tolist()}")
        
        if col_url and pd.notna(linha[col_url]):
            url_imagem = str(linha[col_url]).strip()
            
            if url_imagem and url_imagem.lower() != "nan" and url_imagem != "":
                if not (url_imagem.startswith("http://") or url_imagem.startswith("https://")):
                    url_imagem = "https://" + url_imagem
                
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                    }
                    
                    response = requests.get(url_imagem, timeout=30, allow_redirects=True, headers=headers, verify=True)
                    response.raise_for_status()
                    
                    content_type = response.headers.get('content-type', '')
                    if 'image' not in content_type.lower() and len(response.content) < 100:
                        erro_imagem = f"URL não retorna imagem válida (tipo: {content_type})"
                    else:
                        img = Image.open(BytesIO(response.content))
                        if img.mode in ('RGBA', 'LA', 'P'):
                            img = img.convert('RGB')
                        tem_imagem = True
                        
                except requests.exceptions.Timeout:
                    erro_imagem = "⏱️ Timeout: Servidor demorou muito para responder"
                except requests.exceptions.ConnectionError:
                    erro_imagem = "🔌 Erro de conexão: Não foi possível conectar ao servidor"
                except requests.exceptions.HTTPError as e:
                    erro_imagem = f"❌ HTTP {e.response.status_code}: {e.response.reason}"
                except Exception as e:
                    erro_imagem = f"⚠️ Erro: {str(e)[:100]}"
            else:
                erro_imagem = "URL vazia ou inválida"
        else:
            erro_imagem = "Sem URL"

        # Layout
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"## Imagem {idx+1} de {total}")
            if tem_imagem and img:
                try:
                    largura = 360
                    altura = int(largura * 16 / 9)
                    img_resized = img.resize((largura, altura), Image.Resampling.LANCZOS)
                    st.image(img_resized, use_container_width=False)
                except Exception as e:
                    st.error(f"Erro ao processar imagem: {str(e)}")
                    st.code(f"URL: {url_imagem}", language=None)
            elif erro_imagem:
                st.error(f"❌ {erro_imagem}")
                if url_imagem:
                    st.code(f"URL: {url_imagem}", language=None)
                    st.markdown(f"[🔗 Testar URL no navegador]({url_imagem})")
            else:
                st.warning("⚠️ Sem imagem disponível")
        
        with col2:
            st.markdown("### Info Item Anterior")
            if idx > 0:
                linha_ant = df.iloc[idx - 1]
                
                if col_url:
                    url_val_ant = str(linha_ant[col_url]) if pd.notna(linha_ant[col_url]) else "N/A"
                    st.text_area("**URL (Ant):**", url_val_ant, height=80, disabled=True, key=f"url_ant_{idx}")
                if col_categoria:
                    cat_ant = str(linha_ant[col_categoria]) if pd.notna(linha_ant[col_categoria]) else "N/A"
                    st.text_input("**Categoria (Ant):**", cat_ant, disabled=True, key=f"cat_ant_{idx}")
                if col_data:
                    data_ant = str(linha_ant[col_data]) if pd.notna(linha_ant[col_data]) else "N/A"
                    st.text_input("**Data (Ant):**", data_ant, disabled=True, key=f"data_ant_{idx}")
                if col_cnpj:
                    cnpj_ant = str(linha_ant[col_cnpj]) if pd.notna(linha_ant[col_cnpj]) else "N/A"
                    st.text_input("**CNPJ (Ant):**", cnpj_ant, disabled=True, key=f"cnpj_ant_{idx}")
                
                valida_ant = str(linha_ant['Valida'])
                motivo_ant = str(linha_ant['Motivos'])
                st.info(f"**Status:** {valida_ant}\n\n{motivo_ant}")
            else:
                st.info("Este é o primeiro item.")

        with col3:
            st.markdown("### Informações do Item")
            if col_url:
                url_val = str(linha[col_url]) if pd.notna(linha[col_url]) else "N/A"
                st.text_area("**URL:**", url_val, height=80, disabled=True, key=f"url_{idx}")
            if col_categoria:
                cat = str(linha[col_categoria]) if pd.notna(linha[col_categoria]) else "N/A"
                st.text_input("**Categoria:**", cat, disabled=True, key=f"cat_{idx}")
            if col_data:
                data = str(linha[col_data]) if pd.notna(linha[col_data]) else "N/A"
                st.text_input("**Data:**", data, disabled=True, key=f"data_{idx}")
            if col_cnpj:
                cnpj = str(linha[col_cnpj]) if pd.notna(linha[col_cnpj]) else "N/A"
                st.text_input("**CNPJ:**", cnpj, disabled=True, key=f"cnpj_{idx}")
            
            # Mostrar quantas duplicatas existem
            if col_url and col_categoria and pd.notna(linha[col_url]) and pd.notna(linha[col_categoria]):
                url_atual = str(linha[col_url]).strip()
                cat_atual = str(linha[col_categoria]).strip()
                
                # Contar duplicatas (mesma URL + Categoria)
                duplicatas_totais = 0
                duplicatas_pendentes = 0
                for i in range(len(df)):
                    row = df.iloc[i]
                    url_row = str(row[col_url]).strip() if pd.notna(row[col_url]) else None
                    cat_row = str(row[col_categoria]).strip() if pd.notna(row[col_categoria]) else None
                    
                    if url_row == url_atual and cat_row == cat_atual:
                        duplicatas_totais += 1
                        if str(row['Valida']).strip() == "":
                            duplicatas_pendentes += 1
                
                if duplicatas_totais > 1:
                    st.info(f"🔄 **{duplicatas_totais} linha(s) com mesma URL + Categoria**\n\n{duplicatas_pendentes} ainda não validadas")

        st.divider()
        st.markdown("### Validação")
        
        # Debug info
        with st.expander("🐛 Debug Info"):
            st.write(f"Índice atual: {idx}")
            st.write(f"Valida atual: '{df.iloc[idx]['Valida']}'")
            st.write(f"Total validadas: {total_validadas}")
            st.write(f"Navegação Manual: {st.session_state.navegacao_manual}")
        
        # Mostrar status da linha atual
        linha_ja_validada = esta_validada(linha)
        if linha_ja_validada:
            valida_anterior = df.iloc[idx]['Valida']
            motivo_anterior = df.iloc[idx]['Motivos']
            mensagem_motivo = f" - {motivo_anterior}" if motivo_anterior else ""
            st.warning(f"⚠️ Esta linha já foi validada anteriormente como: **{valida_anterior}**{mensagem_motivo}")
            st.info("💡 Você pode revisar e salvar novamente para alterar a validação.")
        
        if not tem_imagem:
            st.warning("⚠️ Imagem não carregou - será marcada como **SEM IMAGEM**")
            
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            with col_btn1:
                if st.button('✔ Salvar SEM IMAGEM', use_container_width=True, key=f"btn_sem_{idx}", type="primary"):
                    data_validacao = str(datetime.now())
                    
                    # Salvar linha atual
                    st.session_state.df.loc[idx, 'Valida'] = 'NÃO'
                    st.session_state.df.loc[idx, 'Motivos'] = 'SEM IMAGEM'
                    st.session_state.df.loc[idx, 'Data_Validacao'] = data_validacao
                    
                    # REPLICAÇÃO AUTOMÁTICA para SEM IMAGEM
                    url_atual = str(linha[col_url]).strip() if col_url and pd.notna(linha[col_url]) else None
                    categoria_atual = str(linha[col_categoria]).strip() if col_categoria and pd.notna(linha[col_categoria]) else None
                    
                    linhas_replicadas = 0
                    if url_atual and categoria_atual:
                        for i in range(len(st.session_state.df)):
                            if i != idx:
                                row = st.session_state.df.iloc[i]
                                url_row = str(row[col_url]).strip() if col_url and pd.notna(row[col_url]) else None
                                cat_row = str(row[col_categoria]).strip() if col_categoria and pd.notna(row[col_categoria]) else None
                                valida_row = str(row['Valida']).strip()
                                
                                if url_row == url_atual and cat_row == categoria_atual and valida_row in ["", "nan"]:
                                    st.session_state.df.loc[i, 'Valida'] = 'NÃO'
                                    st.session_state.df.loc[i, 'Motivos'] = 'SEM IMAGEM'
                                    st.session_state.df.loc[i, 'Data_Validacao'] = data_validacao + " (replicado)"
                                    linhas_replicadas += 1
                    
                    st.session_state.indice = idx + 1
                    st.session_state.navegacao_manual = False
                    
                    if linhas_replicadas > 0:
                        st.success(f"✅ Salvo como SEM IMAGEM!\n\n🔄 **{linhas_replicadas} linha(s) duplicada(s) replicada(s) automaticamente!**")
                    else:
                        st.success("✅ Salvo como SEM IMAGEM!")
                    
                    st.rerun()
            with col_btn2:
                if st.button('← Voltar', use_container_width=True, key=f"btn_v_sem_{idx}"):
                    # Voltar para a linha anterior
                    if idx > 0:
                        st.session_state.indice = idx - 1
                        st.session_state.navegacao_manual = True
                        st.rerun()
            with col_btn3:
                if st.button('→ Pular', use_container_width=True, key=f"btn_p_sem_{idx}"):
                    st.session_state.indice = idx + 1
                    st.session_state.navegacao_manual = False
                    st.rerun()
        else:
            # Radio buttons - armazenar seleção no session_state para evitar rerun
            radio_key = f"radio_{idx}"
            
            # Verificar se já foi validada antes para pré-selecionar
            if linha_ja_validada:
                valida_anterior = df.iloc[idx]['Valida']
                default_valido = 'Válida ✔' if valida_anterior == 'SIM' else 'Inválida ✗'
            else:
                default_valido = 'Válida ✔'
            
            valido = st.radio('Como deseja classificar esta imagem?', 
                            ['Válida ✔', 'Inválida ✗'], 
                            key=radio_key,
                            index=0 if default_valido == 'Válida ✔' else 1)
            
            motivo_selecionado = ""
            motivo_key = f"mot_{idx}"
            
            if valido == 'Inválida ✗':
                st.markdown("**Selecione o motivo da invalidação:**")
                motivos_opcoes = ['FRAUDE', 'NÃO É PÉ', 'OUTRA CATEGORIA', 'OUTRO PRODUTO']
                
                # Pré-selecionar motivo anterior se existir
                index_anterior = 0
                if linha_ja_validada:
                    motivo_anterior = str(df.iloc[idx]['Motivos'])
                    if motivo_anterior in motivos_opcoes:
                        index_anterior = motivos_opcoes.index(motivo_anterior)
                
                motivo_selecionado = st.radio(
                    'Motivo:',
                    motivos_opcoes,
                    key=motivo_key,
                    label_visibility="collapsed",
                    index=index_anterior
                )
            
            # Botões de ação
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            with col_btn1:
                if st.button('✔ Salvar e Avançar', use_container_width=True, key=f"btn_s_{idx}", type="primary"):
                    # Salvar no DataFrame
                    resultado = 'SIM' if valido == 'Válida ✔' else 'NÃO'
                    data_validacao = str(datetime.now())
                    
                    # Salvar linha atual
                    st.session_state.df.loc[idx, 'Valida'] = resultado
                    st.session_state.df.loc[idx, 'Motivos'] = motivo_selecionado
                    st.session_state.df.loc[idx, 'Data_Validacao'] = data_validacao
                    
                    # REPLICAÇÃO AUTOMÁTICA: Buscar linhas duplicadas (mesma URL + Categoria)
                    url_atual = str(linha[col_url]).strip() if col_url and pd.notna(linha[col_url]) else None
                    categoria_atual = str(linha[col_categoria]).strip() if col_categoria and pd.notna(linha[col_categoria]) else None
                    
                    linhas_replicadas = 0
                    if url_atual and categoria_atual:
                        # Encontrar todas as linhas com mesma URL e Categoria que ainda não foram validadas
                        for i in range(len(st.session_state.df)):
                            if i != idx:  # Não replicar na própria linha
                                row = st.session_state.df.iloc[i]
                                url_row = str(row[col_url]).strip() if col_url and pd.notna(row[col_url]) else None
                                cat_row = str(row[col_categoria]).strip() if col_categoria and pd.notna(row[col_categoria]) else None
                                valida_row = str(row['Valida']).strip()
                                
                                # Se URL e Categoria são iguais e ainda não foi validada
                                if url_row == url_atual and cat_row == categoria_atual and valida_row in ["", "nan"]:
                                    st.session_state.df.loc[i, 'Valida'] = resultado
                                    st.session_state.df.loc[i, 'Motivos'] = motivo_selecionado
                                    st.session_state.df.loc[i, 'Data_Validacao'] = data_validacao + " (replicado)"
                                    linhas_replicadas += 1
                    
                    # Limpar session_state dos radio buttons (se existirem)
                    radio_key_atual = f"radio_{idx}"
                    motivo_key_atual = f"mot_{idx}"
                    
                    if radio_key_atual in st.session_state:
                        del st.session_state[radio_key_atual]
                    if motivo_key_atual in st.session_state:
                        del st.session_state[motivo_key_atual]
                    
                    # Avançar
                    st.session_state.indice = idx + 1
                    st.session_state.navegacao_manual = False
                    
                    # Feedback com informação de replicação
                    mensagem_base = f"✅ Salvo como: {resultado} {f'- {motivo_selecionado}' if motivo_selecionado else ''}"
                    if linhas_replicadas > 0:
                        st.success(f"{mensagem_base}\n\n🔄 **{linhas_replicadas} linha(s) duplicada(s) replicada(s) automaticamente!**")
                    else:
                        st.success(mensagem_base)
                    
                    st.rerun()
            
            with col_btn2:
                if st.button('← Voltar', use_container_width=True, key=f"btn_v_{idx}"):
                    # Voltar para a linha anterior (permite revisar validadas)
                    if idx > 0:
                        st.session_state.indice = idx - 1
                        st.session_state.navegacao_manual = True
                        st.rerun()
            
            with col_btn3:
                if st.button('→ Pular (não salvar)', use_container_width=True, key=f"btn_p_{idx}"):
                    st.session_state.indice = idx + 1
                    st.session_state.navegacao_manual = False
                    st.rerun()

    else:
        st.success('🎉 Todas as imagens foram validadas!')
        
        total_validas = len(df[df['Valida'] == 'SIM'])
        total_invalidas = len(df[df['Valida'] == 'NÃO'])
        
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("Total Validadas", total_validadas)
        with col_stat2:
            st.metric("✅ Válidas", total_validas)
        with col_stat3:
            st.metric("❌ Inválidas", total_invalidas)
        
        st.dataframe(df, use_container_width=True)
        
        if st.button("🔄 Reiniciar Validação"):
            st.session_state.indice = 0
            st.rerun()
else:
    st.info('📤 **Carregue um arquivo CSV ou XLSX para começar a validação**')
    st.markdown("""
    O arquivo deve conter:
    - Uma coluna com URLs das imagens
    - Colunas opcionais: Categoria, Data, CNPJ
    """)
