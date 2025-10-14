import streamlit as st
import pandas as pd
import requests
import io
import os
from datetime import datetime
import plotly.express as px

# ===========================
# 🔐 CONFIGURAÇÕES GERAIS
# ===========================
st.set_page_config(page_title="Painel ME3", layout="wide")
LOCAL_PATH = "Consolidado.xlsx"
SHEET_NAME = "Consolidada"
SESSION_DURATION_HOURS = 12

# Repositório GitHub privado
GITHUB_URL = "https://raw.githubusercontent.com/jrlaporta/ME3/main/Consolidado.xlsx"
GITHUB_TOKEN = "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"  # ← substitua pelo token gerado
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

# ===========================
# 🔒 LOGIN DO ADMIN
# ===========================
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["login_time"] = None

def login_screen():
    st.title("🔐 Login - Painel ME3")
    user = st.text_input("Usuário")
    pwd = st.text_input("Senha", type="password")
    if st.button("Entrar", use_container_width=True):
        if user == "admin" and pwd == "Claro@123":
            st.session_state["authenticated"] = True
            st.session_state["login_time"] = datetime.now()
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")

if not st.session_state["authenticated"]:
    login_screen()
    st.stop()
else:
    elapsed = (datetime.now() - st.session_state["login_time"]).total_seconds() / 3600
    if elapsed > SESSION_DURATION_HOURS:
        st.session_state["authenticated"] = False
        st.warning("Sessão expirada. Faça login novamente.")
        st.rerun()

# ===========================
# 📥 FUNÇÃO DE LEITURA HÍBRIDA
# ===========================
@st.cache_data(ttl=1800)
def load_data():
    # 1️⃣ Tenta ler arquivo local
    if os.path.exists(LOCAL_PATH):
        st.info("📂 Carregando dados locais...")
        try:
            df = pd.read_excel(LOCAL_PATH, sheet_name=SHEET_NAME)
            st.success("✅ Dados carregados do arquivo local.")
            return df
        except Exception as e:
            st.warning(f"⚠️ Erro ao ler arquivo local: {e}. Tentando baixar do GitHub...")

    # 2️⃣ Tenta baixar do GitHub
    try:
        st.info("🌐 Baixando dados atualizados do GitHub...")
        response = requests.get(GITHUB_URL, headers=HEADERS)
        response.raise_for_status()
        df = pd.read_excel(io.BytesIO(response.content), sheet_name=SHEET_NAME)
        st.success("✅ Dados carregados com sucesso do GitHub!")
        # salva localmente como cache
        with open(LOCAL_PATH, "wb") as f:
            f.write(response.content)
        return df
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {e}")
        return pd.DataFrame()

# ===========================
# 🧠 INTERFACE PRINCIPAL
# ===========================
st.sidebar.title("📊 Controle de Dados")
if st.sidebar.button("🔄 Atualizar dados"):
    st.cache_data.clear()
    st.rerun()

df = load_data()
if df.empty:
    st.stop()

# ===========================
# 🎯 FILTROS
# ===========================
st.sidebar.title("Filtros")
df["Data Inicio"] = pd.to_datetime(df["Data Inicio"], errors="coerce")
df["Ano"] = df["Data Inicio"].dt.year
df["Mês"] = df["Data Inicio"].dt.month

anos = sorted(df["Ano"].dropna().unique())
meses = sorted(df["Mês"].dropna().unique())
cidades = sorted(df["Cidade"].dropna().unique())

ano_sel = st.sidebar.multiselect("Ano", anos, default=anos)
mes_sel = st.sidebar.multiselect("Mês", meses, default=meses)
cidade_sel = st.sidebar.multiselect("Cidade", cidades, default=cidades)

df_filt = df[(df["Ano"].isin(ano_sel)) & (df["Mês"].isin(mes_sel)) & (df["Cidade"].isin(cidade_sel))]

# ===========================
# 🧮 CARDS SUPERIORES
# ===========================
st.markdown("<h1 style='text-align:center; color:#0078ff;'>Painel de Análise ME3</h1>", unsafe_allow_html=True)
st.divider()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📊 Total de Registros", len(df_filt))
with col2:
    st.metric("🏙️ Cidades Únicas", df_filt["Cidade"].nunique())
with col3:
    st.metric("🧩 Nodes Únicos", df_filt["NODE"].nunique())

st.divider()

# ===========================
# 📈 GRÁFICOS
# ===========================

# 1️⃣ Eventos por Mês
df_eventos = df_filt.drop_duplicates(subset=["Incidente"])
eventos_mes = df_eventos.groupby(["Ano", "Mês"]).size().reset_index(name="Eventos")
fig1 = px.line(eventos_mes, x="Mês", y="Eventos", color="Ano", markers=True, title="📅 Eventos por Mês", text="Eventos")
fig1.update_traces(textposition="top center")
st.plotly_chart(fig1, use_container_width=True)

# 2️⃣ Total de Eventos por Cidade
df_cid = df_eventos.groupby("Cidade").size().reset_index(name="Eventos")
fig2 = px.bar(df_cid, x="Cidade", y="Eventos", text="Eventos", title="🏙️ Total de Eventos por Cidade", color="Eventos")
fig2.update_traces(textposition="outside")
st.plotly_chart(fig2, use_container_width=True)

# 3️⃣ ME3 Participação Cons
df_part = df_filt.groupby("Cidade")["ME3 Participação Cons"].sum().reset_index()
fig3 = px.bar(df_part, x="Cidade", y="ME3 Participação Cons", text="ME3 Participação Cons",
              title="📊 ME3 Participação Cons por Cidade", color="ME3 Participação Cons")
fig3.update_traces(textposition="outside")
st.plotly_chart(fig3, use_container_width=True)

# 4️⃣ ME3 Evento Cidade
df_evt = df_filt.groupby("Cidade")["ME3 Evento Cidade"].sum().reset_index()
fig4 = px.bar(df_evt, x="Cidade", y="ME3 Evento Cidade", text="ME3 Evento Cidade",
              title="📈 ME3 Evento Cidade por Cidade", color="ME3 Evento Cidade")
fig4.update_traces(textposition="outside")
st.plotly_chart(fig4, use_container_width=True)

# 5️⃣ Nodes por Evento
nodes_top = df_filt.groupby("Incidente")["NODE"].nunique().nlargest(10).reset_index()
fig5 = px.bar(nodes_top, x="Incidente", y="NODE", text="NODE", title="🔟 Top 10 Eventos com Mais Nodes", color="NODE")
fig5.update_traces(textposition="outside")
st.plotly_chart(fig5, use_container_width=True)

# 6️⃣ Solução Rev (Top 5)
solucao_top = df_filt["Solução Rev."].value_counts().nlargest(5).reset_index()
solucao_top.columns = ["Solução Rev.", "Quantidade"]
fig6 = px.bar(solucao_top, x="Solução Rev.", y="Quantidade", text="Quantidade",
              title="⚙️ Top 5 Causas (Solução Rev.)", color="Quantidade")
fig6.update_traces(textposition="outside")
st.plotly_chart(fig6, use_container_width=True)

st.divider()
st.caption("© 2025 Claro Brasil — Painel ME3 | Desenvolvido por Claudioney La Porta")
