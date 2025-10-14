import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# =============== CONFIGURAÇÕES ===============
st.set_page_config(page_title="Painel ME3_Node", layout="wide")
FILE_PATH = r"C:\Users\N5970028\OneDrive - Claro SA\Área de Trabalho\AutomaçãoSGO\Consolidado.xlsx"
SHEET_NAME = "Consolidada"
SESSION_DURATION_HOURS = 12

# =============== LOGIN ===============
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["login_time"] = None

def login_screen():
    st.title("🔐 Login - Painel ME3_Node")
    user = st.text_input("Usuário")
    pwd = st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if user == "admin" and pwd == "Claro@123":
            st.session_state["authenticated"] = True
            st.session_state["login_time"] = datetime.now()
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")

# =============== VERIFICA LOGIN ===============
if not st.session_state["authenticated"]:
    login_screen()
    st.stop()
else:
    elapsed = (datetime.now() - st.session_state["login_time"]).total_seconds() / 3600
    if elapsed > SESSION_DURATION_HOURS:
        st.session_state["authenticated"] = False
        st.warning("Sessão expirada. Faça login novamente.")
        st.rerun()

# =============== FUNÇÃO PARA LER PLANILHA ===============
@st.cache_data(ttl=300)
def load_data():
    df = pd.read_excel(FILE_PATH, sheet_name=SHEET_NAME)
    df["Data Inicio"] = pd.to_datetime(df["Data Inicio"], errors="coerce")
    df["Ano"] = df["Data Inicio"].dt.year
    df["Mês"] = df["Data Inicio"].dt.month
    return df

# =============== LEITURA E ATUALIZAÇÃO ===============
st.sidebar.title("📁 Controle de Dados")
if st.sidebar.button("🔄 Atualizar dados"):
    st.cache_data.clear()
    st.success("Dados atualizados com sucesso!")
df = load_data()

# =============== FILTROS ===============
st.sidebar.title("Filtros")
anos = sorted(df["Ano"].dropna().unique())
meses = sorted(df["Mês"].dropna().unique())
cidades = sorted(df["Cidade"].dropna().unique())

ano_sel = st.sidebar.multiselect("Ano", anos, default=anos)
mes_sel = st.sidebar.multiselect("Mês", meses, default=meses)
cidade_sel = st.sidebar.multiselect("Cidade", cidades, default=cidades)

df_filt = df[(df["Ano"].isin(ano_sel)) & (df["Mês"].isin(mes_sel)) & (df["Cidade"].isin(cidade_sel))]

# =============== TÍTULO ===============
st.markdown("<h1 style='text-align:center; color:#0078ff;'>Painel de Análise ME3_Node</h1>", unsafe_allow_html=True)
st.divider()

# =============== CARDS SUPERIORES ===============
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📊 Total de Registros", len(df_filt))
with col2:
    st.metric("🏙️ Cidades Únicas", df_filt["Cidade"].nunique())
with col3:
    st.metric("🧩 Nodes Únicos", df_filt["NODE"].nunique())

st.divider()

# =============== GRÁFICOS PRINCIPAIS ===============

# 1️⃣ EVENTOS POR MÊS (sem repetição de incidente)
df_eventos = df_filt.drop_duplicates(subset=["Incidente"])
eventos_mes = df_eventos.groupby(["Ano", "Mês"]).size().reset_index(name="Eventos")
fig1 = px.line(eventos_mes, x="Mês", y="Eventos", color="Ano", markers=True,
               title="📅 Eventos por Mês", text="Eventos")
fig1.update_traces(textposition="top center")
st.plotly_chart(fig1, use_container_width=True)

# 2️⃣ NODES POR EVENTO (TOP 10)
nodes_evento = df_filt.groupby("Incidente")["NODE"].nunique().nlargest(10).reset_index()
fig2 = px.bar(nodes_evento, x="Incidente", y="NODE", text="NODE",
              title="🔟 Top 10 Eventos com Mais Nodes", color="NODE")
fig2.update_traces(textposition="outside")
st.plotly_chart(fig2, use_container_width=True)

# 3️⃣ SOLUÇÃO REV (TOP 5)
solucao_top = df_filt["Solução Rev."].value_counts().nlargest(5).reset_index()
solucao_top.columns = ["Solução Rev.", "Quantidade"]
fig3 = px.bar(solucao_top, x="Solução Rev.", y="Quantidade", text="Quantidade",
              title="⚙️ Top 5 Causas (Solução Rev.)", color="Quantidade")
fig3.update_traces(textposition="outside")
st.plotly_chart(fig3, use_container_width=True)

# 4️⃣ ME3 PARTICIPAÇÃO CONS POR CIDADE
df_part = df_filt.groupby("Cidade")["ME3 Participação Cons"].sum().reset_index()
fig4 = px.bar(df_part, x="Cidade", y="ME3 Participação Cons", text="ME3 Participação Cons",
              title="🏙️ ME3 Participação Cons por Cidade", color="ME3 Participação Cons")
fig4.update_traces(textposition="outside")
st.plotly_chart(fig4, use_container_width=True)

# 5️⃣ ME3 EVENTO CIDADE POR CIDADE
df_evento = df_filt.groupby("Cidade")["ME3 Evento Cidade"].sum().reset_index()
fig5 = px.bar(df_evento, x="Cidade", y="ME3 Evento Cidade", text="ME3 Evento Cidade",
              title="📈 ME3 Evento Cidade por Cidade", color="ME3 Evento Cidade")
fig5.update_traces(textposition="outside")
st.plotly_chart(fig5, use_container_width=True)

st.divider()
st.caption("© 2025 Claro Brasil — Painel ME3_Node | Desenvolvido por Claudioney La Porta")
