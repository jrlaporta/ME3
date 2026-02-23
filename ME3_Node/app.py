import os
import streamlit as st
import pandas as pd
import plotly.express as px

# ==============================
# ⚙️ CONFIGURAÇÕES GERAIS
# ==============================
st.set_page_config(page_title="Painel ME3", layout="wide")
st.title("📊 Painel Consolidado - ME3")

# ==============================
# 🔐 LOGIN (mantive como você tinha)
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
# 📄 LEITURA DIRETO DO REPOSITÓRIO
# (arquivo na mesma pasta do app.py: ME3_Node/Consolidado.xlsx)
# ==============================
EXCEL_FILENAME = "Consolidado.xlsx"

@st.cache_data(ttl=300)
def carregar_dados():
    base_dir = os.path.dirname(__file__)  # pasta do app.py (ME3_Node)
    excel_path = os.path.join(base_dir, EXCEL_FILENAME)

    if not os.path.exists(excel_path):
        st.error("Não foi possível carregar os dados (arquivo não encontrado no repositório).")
        st.info("Caminho esperado (no Streamlit Cloud):")
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
col_btn, col_info = st.columns([1, 5])
with col_btn:
    if st.button("🔄 Atualizar Dados"):
        st.cache_data.clear()
        st.rerun()

df = carregar_dados()
if df.empty:
    st.stop()

# ==============================
# 🧹 AJUSTES / NORMALIZAÇÃO
# ==============================
df.columns = [c.strip() for c in df.columns]

# Validar coluna principal de data
if "Data Fechamento" not in df.columns:
    st.error("Coluna 'Data Fechamento' não encontrada na planilha.")
    st.stop()

df["Data Fechamento"] = pd.to_datetime(df["Data Fechamento"], errors="coerce")

# Normalizar Cidade
if "Cidade" in df.columns:
    df["Cidade"] = (
        df["Cidade"].astype(str)
        .str.replace("\u00a0", " ", regex=False)  # NBSP -> espaço normal
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
        .str.upper()
    )
else:
    st.error("Coluna 'Cidade' não encontrada na planilha.")
    st.stop()

# Colunas numéricas (se existirem)
for col_num in ["ME3 Participação Cons", "ME3 Evento Cidade", "Soma de Ativos Afetados Rev."]:
    if col_num in df.columns:
        df[col_num] = pd.to_numeric(df[col_num], errors="coerce")

df["Ano"] = df["Data Fechamento"].dt.year
df["Mês"] = df["Data Fechamento"].dt.month

# Colunas úteis
for must in ["Incidente", "NODE"]:
    if must not in df.columns:
        st.warning(f"Coluna '{must}' não encontrada. Alguns gráficos/tabela podem ficar incompletos.")

# ==============================
# 🎛️ FILTROS GLOBAIS (Cidade global + Ano global)
# ==============================
anos = sorted([int(a) for a in df["Ano"].dropna().unique()])
cidades = sorted(df["Cidade"].dropna().unique())

f1, f2 = st.columns(2)
ano_sel = f1.selectbox("Ano (global)", anos, key="ano_global")

cid_sel = f2.multiselect(
    "Cidade (global)",
    cidades,
    default=cidades,
    key="cidade_global"
)

df_base = df[(df["Ano"] == ano_sel) & (df["Cidade"].isin(cid_sel))].copy()
if df_base.empty:
    st.info("Sem dados para os filtros globais selecionados.")
    st.stop()

# Meses disponíveis conforme filtros globais
meses_disponiveis = sorted([int(m) for m in df_base["Mês"].dropna().unique()])

meses_abreviados = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
}
meses_nomes_disp = [f"{meses_abreviados[m]} ({m})" for m in meses_disponiveis]

def meses_para_numeros(meses_txt):
    return [int(txt.split("(")[1].split(")")[0]) for txt in meses_txt]

def filtrar_por_meses(df_in, meses_txt):
    if not meses_txt:
        return df_in.iloc[0:0].copy()
    meses_num = meses_para_numeros(meses_txt)
    return df_in[df_in["Mês"].isin(meses_num)].copy()

def eventos_unicos_por_incidente(df_in):
    if "Incidente" in df_in.columns:
        return (
            df_in.sort_values("Data Fechamento")
            .drop_duplicates(subset=["Incidente"], keep="first")
            .copy()
        )
    return df_in.copy()

# ==============================
# 📊 CARDS (global: Ano + Cidade)
# ==============================
st.subheader("Resumo Geral (filtros globais)")

c1, c2, c3 = st.columns(3)

if "Incidente" in df_base.columns:
    c1.metric("Total de Incidentes (únicos)", int(df_base["Incidente"].nunique()))
else:
    c1.metric("Total de Registros", int(len(df_base)))

c2.metric("Total de Cidades", int(df_base["Cidade"].nunique()))

if "Soma de Ativos Afetados Rev." in df_base.columns:
    media_ativos = df_base["Soma de Ativos Afetados Rev."].mean()
    c3.metric("Média de Ativos Afetados", 0 if pd.isna(media_ativos) else int(media_ativos))
else:
    c3.metric("Média de Ativos Afetados", 0)

st.divider()

# ==============================
# 📈 GRÁFICOS (cada um com filtro próprio de mês)
# Regras:
# - Cidade é global (df_base já vem filtrado)
# - Cada gráfico tem seu multiselect de meses (key único)
# - Todos os gráficos com rótulos
# ==============================

# 1) Evolução diária - ME3 Participação Cons (eventos únicos por incidente)
st.subheader("📈 Evolução Diária - ME3 Participação Cons")
meses_g1 = st.multiselect(
    "Mês (somente este gráfico)",
    meses_nomes_disp,
    default=meses_nomes_disp,
    key="meses_g1"
)
df_g1 = eventos_unicos_por_incidente(filtrar_por_meses(df_base, meses_g1))

if "ME3 Participação Cons" in df_g1.columns and not df_g1.empty:
    df_g1["Dia"] = df_g1["Data Fechamento"].dt.date
    evolucao = df_g1.groupby("Dia")["ME3 Participação Cons"].sum().reset_index()
    evolucao = evolucao.sort_values("Dia")
    evolucao["ME3 Participação Cons"] = evolucao["ME3 Participação Cons"].round(2)

    fig = px.line(evolucao, x="Dia", y="ME3 Participação Cons", markers=True)
    fig.update_traces(text=evolucao["ME3 Participação Cons"], textposition="top center")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sem dados para este gráfico (ou coluna 'ME3 Participação Cons' inexistente).")

st.divider()

# 2) Eventos por mês (incidentes únicos)
st.subheader("📆 Incidentes por Mês (únicos)")
meses_g2 = st.multiselect(
    "Mês (somente este gráfico)",
    meses_nomes_disp,
    default=meses_nomes_disp,
    key="meses_g2"
)
df_g2 = eventos_unicos_por_incidente(filtrar_por_meses(df_base, meses_g2))

if "Incidente" in df_g2.columns and not df_g2.empty:
    eventos_mes = df_g2.groupby(["Mês"])["Incidente"].nunique().reset_index()
    eventos_mes = eventos_mes.sort_values("Mês")
    eventos_mes["MesLabel"] = eventos_mes["Mês"].apply(lambda m: meses_abreviados[int(m)])

    fig = px.bar(eventos_mes, x="MesLabel", y="Incidente", text="Incidente")
    fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sem dados para este gráfico (ou coluna 'Incidente' inexistente).")

st.divider()

# 3) Incidentes por cidade (incidentes únicos)
st.subheader("🏙️ Incidentes por Cidade (únicos)")
meses_g3 = st.multiselect(
    "Mês (somente este gráfico)",
    meses_nomes_disp,
    default=meses_nomes_disp,
    key="meses_g3"
)
df_g3 = eventos_unicos_por_incidente(filtrar_por_meses(df_base, meses_g3))

if "Incidente" in df_g3.columns and not df_g3.empty:
    eventos_cid = df_g3.groupby("Cidade")["Incidente"].nunique().reset_index()
    eventos_cid = eventos_cid.sort_values("Incidente", ascending=False)

    fig = px.bar(eventos_cid, x="Cidade", y="Incidente", text="Incidente")
    fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sem dados para este gráfico (ou coluna 'Incidente' inexistente).")

st.divider()

# 4) ME3 Participação Cons por cidade (eventos únicos)
st.subheader("📊 ME3 Participação Cons por Cidade (eventos únicos)")
meses_g4 = st.multiselect(
    "Mês (somente este gráfico)",
    meses_nomes_disp,
    default=meses_nomes_disp,
    key="meses_g4"
)
df_g4 = eventos_unicos_por_incidente(filtrar_por_meses(df_base, meses_g4))

if "ME3 Participação Cons" in df_g4.columns and not df_g4.empty:
    graf = df_g4.groupby("Cidade")["ME3 Participação Cons"].sum().reset_index()
    graf["ME3 Participação Cons"] = graf["ME3 Participação Cons"].round(2)
    graf = graf.sort_values("ME3 Participação Cons", ascending=False)

    fig = px.bar(graf, x="Cidade", y="ME3 Participação Cons", text="ME3 Participação Cons")
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sem dados para este gráfico (ou coluna 'ME3 Participação Cons' inexistente).")

st.divider()

# 5) ME3 Evento Cidade por cidade (eventos únicos)
st.subheader("🏗️ ME3 Evento Cidade por Cidade (eventos únicos)")
meses_g5 = st.multiselect(
    "Mês (somente este gráfico)",
    meses_nomes_disp,
    default=meses_nomes_disp,
    key="meses_g5"
)
df_g5 = eventos_unicos_por_incidente(filtrar_por_meses(df_base, meses_g5))

if "ME3 Evento Cidade" in df_g5.columns and not df_g5.empty:
    graf = df_g5.groupby("Cidade")["ME3 Evento Cidade"].sum().reset_index()
    graf["ME3 Evento Cidade"] = graf["ME3 Evento Cidade"].round(2)
    graf = graf.sort_values("ME3 Evento Cidade", ascending=False)

    fig = px.bar(graf, x="Cidade", y="ME3 Evento Cidade", text="ME3 Evento Cidade")
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sem dados para este gráfico (ou coluna 'ME3 Evento Cidade' inexistente).")

st.divider()

# 6) Top 10 NODES com mais repetições (aqui é em cima dos registros, não eventos únicos)
st.subheader("🔝 Top 10 NODES com mais repetições (registros)")
meses_g6 = st.multiselect(
    "Mês (somente este gráfico)",
    meses_nomes_disp,
    default=meses_nomes_disp,
    key="meses_g6"
)
df_g6 = filtrar_por_meses(df_base, meses_g6)

if "NODE" in df_g6.columns and not df_g6.empty:
    top_nodes = df_g6["NODE"].astype(str).value_counts().nlargest(10).reset_index()
    top_nodes.columns = ["NODE", "Quantidade de Repetições"]

    fig = px.bar(top_nodes, x="NODE", y="Quantidade de Repetições", text="Quantidade de Repetições")
    fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sem dados para este gráfico (ou coluna 'NODE' inexistente).")

st.divider()

# 7) Top 5 Soluções Rev. (registros)
st.subheader("⚡ Top 5 Soluções Rev. mais frequentes (registros)")
meses_g7 = st.multiselect(
    "Mês (somente este gráfico)",
    meses_nomes_disp,
    default=meses_nomes_disp,
    key="meses_g7"
)
df_g7 = filtrar_por_meses(df_base, meses_g7)

if "Solução Rev." in df_g7.columns and not df_g7.empty:
    causas = df_g7["Solução Rev."].astype(str).value_counts().nlargest(5).reset_index()
    causas.columns = ["Solução Rev.", "Ocorrências"]

    fig = px.bar(causas, x="Solução Rev.", y="Ocorrências", text="Ocorrências")
    fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sem dados para este gráfico (ou coluna 'Solução Rev.' inexistente).")

st.divider()

# ==============================
# 📋 TABELA FINAL: Incidentes agrupados com NODES do mesmo incidente
# (Aqui NÃO deduplicamos, porque precisamos juntar todos os NODES do incidente)
# ==============================
st.subheader("🧾 Incidentes agrupados com NODES envolvidos")

tcol1, tcol2 = st.columns([2, 3])
meses_tab = tcol1.multiselect(
    "Mês (somente para esta tabela)",
    meses_nomes_disp,
    default=meses_nomes_disp,
    key="meses_tabela"
)
buscar = tcol2.text_input("Buscar por incidente ou node", value="", key="busca_tabela")

df_tab = filtrar_por_meses(df_base, meses_tab)

# Validar colunas essenciais da tabela
for c in ["Incidente", "NODE", "Cidade", "Data Fechamento"]:
    if c not in df_tab.columns:
        st.error(f"Coluna obrigatória para a tabela não encontrada: {c}")
        st.stop()

tabela = (
    df_tab.groupby("Incidente")
    .agg(
        Data_Primeiro_Fechamento=("Data Fechamento", "min"),
        Data_Ultimo_Fechamento=("Data Fechamento", "max"),
        Cidades=("Cidade", lambda s: ", ".join(sorted(set(map(str, s.dropna()))))),
        Nodes=("NODE", lambda s: ", ".join(sorted(set(map(str, s.dropna()))))),
        Qtde_Nodes=("NODE", lambda s: len(set(map(str, s.dropna())))),
        Registros=("NODE", "size"),
    )
    .reset_index()
    .sort_values(["Qtde_Nodes", "Registros"], ascending=False)
)

if buscar.strip():
    b = buscar.strip().upper()
    tabela = tabela[
        tabela["Incidente"].astype(str).str.upper().str.contains(b, na=False)
        | tabela["Nodes"].astype(str).str.upper().str.contains(b, na=False)
        | tabela["Cidades"].astype(str).str.upper().str.contains(b, na=False)
    ]

st.dataframe(tabela, use_container_width=True)

st.success("✅ Painel carregado com sucesso!")

