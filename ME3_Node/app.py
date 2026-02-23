import streamlit as st
import pandas as pd
import plotly.express as px
import os

# ==============================
# ⚙️ CONFIGURAÇÕES GERAIS
# ==============================
st.set_page_config(page_title="Painel ME3", layout="wide")
st.title("📊 Painel Consolidado - ME3")

# ==============================
# 🔐 LOGIN
# ==============================
def login():
    st.sidebar.title("🔐 Login")
    user = st.sidebar.text_input("Usuário")
    pwd = st.sidebar.text_input("Senha", type="password")
    if st.sidebar.button("Entrar"):
        if user == "admin" and pwd == "Claro@123":
            st.session_state["auth"] = True
        else:
            st.sidebar.error("Credenciais inválidas.")

if "auth" not in st.session_state or not st.session_state["auth"]:
    login()
    st.stop()

# ==============================
# 📄 ARQUIVO DENTRO DO REPOSITÓRIO
# (mesma pasta do app.py)
# ==============================
EXCEL_FILENAME = "Consolidado.xlsx"

# ==============================
# 🔄 CARREGAR DADOS (DIRETO DO REPO)
# ==============================
@st.cache_data(ttl=300)
def carregar_dados():
    base_dir = os.path.dirname(__file__)  # pasta onde está o app.py (ME3_Node)
    excel_path = os.path.join(base_dir, EXCEL_FILENAME)

    if not os.path.exists(excel_path):
        st.error("Não foi possível carregar os dados.")
        st.info("Verifique se o arquivo está no repositório neste caminho:")
        st.code(excel_path)
        return pd.DataFrame()

    try:
        df = pd.read_excel(excel_path, engine="openpyxl")
        return df
    except Exception as e:
        st.error("Falha ao ler a planilha Excel.")
        st.exception(e)
        return pd.DataFrame()

# ==============================
# 🔘 BOTÃO DE ATUALIZAÇÃO
# ==============================
if st.button("🔄 Atualizar Dados"):
    st.cache_data.clear()
    st.rerun()

df = carregar_dados()

if df.empty:
    st.stop()

# ==============================
# 🧹 AJUSTES DE DADOS
# ==============================
df.columns = [c.strip() for c in df.columns]
if "Data Fechamento" in df.columns:
    df["Data Fechamento"] = pd.to_datetime(df["Data Fechamento"], errors="coerce")
    # Garantir colunas numéricas
    for col_num in ["ME3 Participação Cons", "ME3 Evento Cidade"]:
        if col_num in df.columns:
            df[col_num] = pd.to_numeric(df[col_num], errors="coerce")
    # Normalizar valores de Cidade para evitar duplicatas aparentes
    if "Cidade" in df.columns:
        df["Cidade"] = (
            df["Cidade"].astype(str)
            .str.replace("\u00a0", " ", regex=False)  # NBSP -> espaço normal
            .str.replace(r"\s+", " ", regex=True)    # múltiplos espaços -> 1
            .str.strip()
            .str.upper()
        )
    df["Ano"] = df["Data Fechamento"].dt.year
    df["Mês"] = df["Data Fechamento"].dt.month
else:
    st.error("Coluna 'Data Fechamento' não encontrada na planilha.")
    st.stop()

# ==============================
# 🎛️ FILTROS
# ==============================
anos = sorted(df["Ano"].dropna().unique())
meses = sorted(df["Mês"].dropna().unique())
cidades = sorted(df["Cidade"].dropna().unique())

# Converter anos para inteiros e meses para nomes abreviados
anos_int = [int(ano) for ano in anos]
meses_nomes = []
meses_abreviados = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
}

for mes in meses:
    mes_int = int(mes)
    meses_nomes.append(f"{meses_abreviados[mes_int]} ({mes_int})")

col1, col2, col3 = st.columns(3)
ano_sel = col1.selectbox("Ano", anos_int)
meses_sel = col2.multiselect("Mês", meses_nomes, default=meses_nomes)
cid_sel = col3.multiselect("Cidade", cidades, default=cidades)

# Converter seleção de meses de volta para números
meses_numeros = [int(txt.split("(")[1].split(")")[0]) for txt in meses_sel]

df_filt = df[(df["Ano"] == ano_sel) & (df["Mês"].isin(meses_numeros)) & (df["Cidade"].isin(cid_sel))]

# ==============================
# 📄 DATASET DE EVENTOS ÚNICOS (por Incidente)
# ==============================
if "Incidente" in df_filt.columns:
    df_eventos = (
        df_filt.sort_values("Data Fechamento")
        .drop_duplicates(subset=["Incidente"], keep="first")
        .copy()
    )
else:
    df_eventos = df_filt.copy()

# Normalizar data para DIA (sem hora) para os gráficos diários
if "Data Fechamento" in df_eventos.columns:
    df_eventos["Dia"] = df_eventos["Data Fechamento"].dt.date

# ==============================
# 📊 CARDS
# ==============================
st.subheader("Resumo Geral")
if df_filt.empty:
    st.info("Selecione filtros para visualizar os dados.")
    st.stop()

col1, col2, col3 = st.columns(3)
col1.metric("Total de Eventos", len(df_filt["Incidente"].unique()))
col2.metric("Total de Cidades", df_filt["Cidade"].nunique())

if "Soma de Ativos Afetados Rev." in df_filt.columns:
    media_ativos = pd.to_numeric(df_filt["Soma de Ativos Afetados Rev."], errors="coerce").mean()
    col3.metric("Média de Ativos Afetados", 0 if pd.isna(media_ativos) else int(media_ativos))
else:
    col3.metric("Média de Ativos Afetados", 0)

# ==============================
# 📈 GRÁFICOS
# ==============================

# 1️⃣ Evolução Diária ME3 Participação Cons (eventos únicos, agrupado por dia)
if "ME3 Participação Cons" in df_eventos.columns and not df_eventos.empty:
    st.subheader("📈 Evolução Diária ME3 Participação Cons")
    evolucao_diaria = df_eventos.groupby("Dia")["ME3 Participação Cons"].sum().reset_index()
    evolucao_diaria = evolucao_diaria.sort_values("Dia")
    evolucao_diaria["ME3 Participação Cons"] = evolucao_diaria["ME3 Participação Cons"].round(2)
    fig_evol = px.line(evolucao_diaria, x="Dia", y="ME3 Participação Cons", markers=True)
    fig_evol.update_traces(text=evolucao_diaria["ME3 Participação Cons"], textposition="top center")
    st.plotly_chart(fig_evol, use_container_width=True)

st.subheader("📆 Eventos por Mês")
eventos_mes = df_eventos.groupby(["Ano", "Mês"])["Incidente"].nunique().reset_index()
if eventos_mes.empty:
    st.info("Sem dados para os filtros selecionados.")
else:
    fig1 = px.bar(eventos_mes, x="Mês", y="Incidente", color="Ano", barmode="group", text_auto=True)
    fig1.update_layout(xaxis=dict(dtick=1), bargap=0.15, bargroupgap=0.1)
    st.plotly_chart(fig1, use_container_width=True)

# 3️⃣ Eventos por Cidade
st.subheader("🏙️ Eventos por Cidade")
eventos_cid = df_eventos.groupby("Cidade")["Incidente"].nunique().reset_index()
if eventos_cid.empty:
    st.info("Sem dados para os filtros selecionados.")
else:
    fig2 = px.bar(eventos_cid, x="Cidade", y="Incidente", text_auto=True)
    st.plotly_chart(fig2, use_container_width=True)

# 4️⃣ ME3 Participação Cons por Cidade (eventos únicos)
if "ME3 Participação Cons" in df_eventos.columns:
    st.subheader("📊 ME3 Participação Cons por Cidade")
    graf3 = df_eventos.groupby("Cidade")["ME3 Participação Cons"].sum().reset_index()
    graf3["ME3 Participação Cons"] = graf3["ME3 Participação Cons"].round(2)
    if graf3.empty:
        st.info("Sem dados para os filtros selecionados.")
    else:
        fig3 = px.bar(graf3, x="Cidade", y="ME3 Participação Cons", text_auto=True)
        fig3.update_layout(yaxis=dict(tickformat=".2f"))
        fig3.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        st.plotly_chart(fig3, use_container_width=True)

# 5️⃣ ME3 Evento Cidade por Cidade (eventos únicos)
if "ME3 Evento Cidade" in df_eventos.columns:
    st.subheader("🏗️ ME3 Evento Cidade por Cidade")
    graf4 = df_eventos.groupby("Cidade")["ME3 Evento Cidade"].sum().reset_index()
    graf4["ME3 Evento Cidade"] = graf4["ME3 Evento Cidade"].round(2)
    if graf4.empty:
        st.info("Sem dados para os filtros selecionados.")
    else:
        fig4 = px.bar(graf4, x="Cidade", y="ME3 Evento Cidade", text_auto=True)
        fig4.update_layout(yaxis=dict(tickformat=".2f"))
        fig4.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        st.plotly_chart(fig4, use_container_width=True)

# 6️⃣ Top 10 Nodes com mais repetições
st.subheader("🔝 Top 10 Nodes com mais repetições")
top_nodes = df_filt["NODE"].value_counts().nlargest(10).reset_index()
top_nodes.columns = ["NODE", "Quantidade de Repetições"]
fig5 = px.bar(top_nodes, x="NODE", y="Quantidade de Repetições", text_auto=True)
st.plotly_chart(fig5, use_container_width=True)

# 7️⃣ Solução Rev (Top 5 causas)
if "Solução Rev." in df_filt.columns:
    st.subheader("⚡ Top 5 Soluções Rev. mais frequentes")
    causas = df_filt["Solução Rev."].value_counts().nlargest(5).reset_index()
    causas.columns = ["Solução Rev.", "Ocorrências"]
    fig6 = px.bar(causas, x="Solução Rev.", y="Ocorrências", text_auto=True)
    st.plotly_chart(fig6, use_container_width=True)

st.success("✅ Painel carregado com sucesso!")

