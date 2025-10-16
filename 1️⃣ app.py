import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import StringIO

# ===== CONFIGURAÇÕES =====
st.set_page_config(page_title="Painel ME3", layout="wide")
GITHUB_TOKEN = "cole_seu_token_aqui"
GITHUB_REPO = "jrlaporta/ME3"
GITHUB_FILE = "Consolidado.csv"

# ===== FUNÇÃO PARA BAIXAR CSV DO GITHUB =====
@st.cache_data(ttl=300)
def carregar_dados():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = r.json()["content"]
        csv_bytes = StringIO(requests.utils.unquote(content))
        csv_str = StringIO(pd.util.hash_pandas_object(pd.DataFrame()).to_string())
        df = pd.read_csv(StringIO(requests.utils.unquote(r.json()["content"])), sep=",")
        return df
    else:
        st.error("Erro ao carregar o arquivo do GitHub.")
        return pd.DataFrame()

# ===== LOGIN =====
def login():
    st.sidebar.title("🔐 Login")
    user = st.sidebar.text_input("Usuário")
    pwd = st.sidebar.text_input("Senha", type="password")
    if st.sidebar.button("Entrar"):
        if user == "admin" and pwd == "Claro@123":
            st.session_state["auth"] = True
        else:
            st.sidebar.error("Credenciais inválidas.")

# ===== INTERFACE =====
if "auth" not in st.session_state or not st.session_state["auth"]:
    login()
    st.stop()

st.title("📊 Painel Consolidado - ME3")
st.markdown("Atualização manual via botão abaixo:")

if st.button("🔄 Atualizar Dados"):
    st.cache_data.clear()

df = carregar_dados()

if df.empty:
    st.warning("Nenhum dado carregado.")
    st.stop()

# ===== PRÉ-PROCESSAMENTO =====
df.columns = [c.strip() for c in df.columns]
if "Data Fechamento" in df.columns:
    df["Data Fechamento"] = pd.to_datetime(df["Data Fechamento"], errors="coerce")
    df["Ano"] = df["Data Fechamento"].dt.year
    df["Mês"] = df["Data Fechamento"].dt.month

# ===== FILTROS =====
anos = sorted(df["Ano"].dropna().unique())
meses = sorted(df["Mês"].dropna().unique())
cidades = sorted(df["Cidade"].dropna().unique())

col1, col2, col3 = st.columns(3)
ano_sel = col1.selectbox("Ano", anos)
mes_sel = col2.selectbox("Mês", meses)
cid_sel = col3.multiselect("Cidade", cidades, default=cidades)

df_filt = df[(df["Ano"] == ano_sel) & (df["Mês"] == mes_sel) & (df["Cidade"].isin(cid_sel))]

# ===== DASHBOARDS =====
st.subheader("Resumo Geral")
col1, col2, col3 = st.columns(3)
col1.metric("Total de Eventos", len(df_filt["Incidente"].unique()))
col2.metric("Total de Cidades", df_filt["Cidade"].nunique())
col3.metric("Média Ativos Afetados", int(df_filt["Soma de Ativos Afetados Rev."].mean()))

# ===== GRÁFICOS =====
st.subheader("📆 Eventos por Mês")
eventos_mes = df.groupby(["Ano", "Mês"])["Incidente"].nunique().reset_index()
fig1 = px.line(eventos_mes, x="Mês", y="Incidente", color="Ano", markers=True)
fig1.update_traces(text=eventos_mes["Incidente"], textposition="top center")
st.plotly_chart(fig1, use_container_width=True)

st.subheader("🏙️ Eventos por Cidade")
eventos_cid = df_filt.groupby("Cidade")["Incidente"].nunique().reset_index()
fig2 = px.bar(eventos_cid, x="Cidade", y="Incidente", text_auto=True)
st.plotly_chart(fig2, use_container_width=True)
