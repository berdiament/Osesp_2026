from collections import defaultdict
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

# --- Config ---
DATA_FILE = Path("concertos_2026.parquet")
RATINGS_DIR = Path("ratings")
RATINGS_DIR.mkdir(exist_ok=True)
USERS_FILE = Path("users.csv")

st.set_page_config(page_title="🎶 Concert Selector", layout="wide",
                   initial_sidebar_state="expanded", menu_items=None)

# ============ LOGIN/CADASTRO ============
def load_users():
    if USERS_FILE.exists():
        return pd.read_csv(USERS_FILE)
    return pd.DataFrame(columns=["email", "nome", "senha"])

def save_user(email, nome, senha):
    users = load_users()
    if email not in users["email"].values:
        new_user = pd.DataFrame({"email": [email], "nome": [nome], "senha": [senha]})
        users = pd.concat([users, new_user], ignore_index=True)
        users.to_csv(USERS_FILE, index=False)
        return True
    return False

def login_or_register():
    st.title("🔐 Login / Cadastro")
    
    tab1, tab2 = st.tabs(["Login", "Cadastro"])
    
    with tab1:
        email = st.text_input("Email:", key="login_email")
        senha = st.text_input("Senha:", type="password", key="login_senha")
        
        if st.button("Entrar"):
            users = load_users()
            user_row = users[users["email"] == email]
            
            if not user_row.empty:
                if user_row.iloc[0]["senha"] == senha:
                    st.session_state["logged_in"] = True
                    st.session_state["user_email"] = email
                    st.session_state["user_nome"] = user_row.iloc[0]["nome"]
                    st.rerun()
                else:
                    st.error("Senha incorreta!")
            else:
                st.error("Email não cadastrado!")
    
    with tab2:
        email = st.text_input("Email:", key="register_email")
        nome = st.text_input("Nome completo:")
        senha = st.text_input("Senha:", type="password", key="register_senha")
        senha_confirm = st.text_input("Confirme a senha:", type="password")
        
        if st.button("Cadastrar"):
            if email and nome and senha:
                if senha == senha_confirm:
                    if save_user(email, nome, senha):
                        st.success("✓ Cadastro realizado! Faça login agora.")
                    else:
                        st.error("Email já cadastrado!")
                else:
                    st.error("As senhas não coincidem!")
            else:
                st.error("Preencha todos os campos!")

# ← VERIFICA LOGIN
if "logged_in" not in st.session_state:
    login_or_register()
    st.stop()

# Depois, customize a largura do sidebar com CSS
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        min-width: 400px;
        width: 500px;
    }
    
    [data-testid="stSidebarContent"] {
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- Load dataset ---
@st.cache_data
def load_data():
    return pd.read_parquet(DATA_FILE)

df = load_data()
program_ids = df['program_id'].unique()

# --- Helper functions ---
def abv_month(mes):
    meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", 
             "Outubro", "Novembro", "Dezembro"]
    return meses[mes-1][:3]

def num_month(abv):
    meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", 
             "Outubro", "Novembro", "Dezembro"]
    return [x[0:3] for x in meses].index(abv) + 1

def get_available_options(df, current_filters):
    """Get available options based on current filters, but show ALL months/series/etc."""
    subset = df.copy()
    
    # Apply only the active filters
    for col, selected in current_filters.items():
        if selected:
            subset = subset[subset[col].isin(selected)]
    
    # Return all unique values from ORIGINAL dataframe, not subset
    # This prevents options from disappearing
    options = {
        "mês": sorted(df["mês"].dropna().unique()),
        "dia_semana": sorted(df["dia_semana"].dropna().unique()),
        "serie": sorted(df["serie"].dropna().unique()),
        "compositor": sorted(subset["compositor"].dropna().unique())
    }
    return subset, options

# --- Callback functions ---
def clear_all_filters():
    """Callback para limpar todos os filtros"""
    st.session_state["series_sel"] = []
    st.session_state["composers_sel"] = []
    st.session_state["weekday_sel"] = []
    st.session_state["month_sel_labels"] = []

def reset_full_session():
    """Limpa filtros E ratings, mostra mensagem"""
    # Pergunta ao usuário
    st.session_state["show_reset_confirmation"] = True

def confirm_reset():
    """Confirma e limpa tudo"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.success("✓ Sessão completamente resetada!")
    st.balloons()

def custom_divider(height="1px", color="#b1b1b1", margin="0.5rem"):
    st.markdown(f"""
    <hr style="
        height: {height};
        background-color: {color};
        border: none;
        margin: {margin} 0;
    ">
    """, unsafe_allow_html=True)

# --- Initialize session state ---
for key in ["series_sel", "composers_sel", "weekday_sel", "month_sel_labels", "ratings"]:
    st.session_state.setdefault(key, [] if key != "ratings" else {})

# --- Build filters ---
filters = {
    "serie": st.session_state.get("series_sel", []),
    "compositor": st.session_state.get("composers_sel", []),
    "dia_semana": st.session_state.get("weekday_sel", []),
    "mês": st.session_state.get("month_sel", [])
}
_, options = get_available_options(df, filters)

# Convert all available month numbers to labels for display
month_labels_available = [abv_month(m) for m in options["mês"]]

# --- SIDEBAR ---
with st.sidebar:
    st.title("🎵 Avaliação de concertos - Temporada 2026")
    st.caption("Avalie os programas e encontre a sua melhor série.")

    # --- SAVE / LOAD SECTION ---
    custom_divider(margin="0.5rem")
    user_email = st.session_state["user_email"]
    st.caption(f"👤 {st.session_state['user_nome']}")
    st.caption(f"📧 {st.session_state['user_email']}")
    ratings_df = pd.DataFrame(
        [{"index": k, "rating": v} for k, v in st.session_state["ratings"].items()]
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 Salvar minhas avaliações"):
            ratings_df.to_csv(RATINGS_DIR / f"{st.session_state['user_email']}_ratings.csv", index=False)
            st.success("Avaliações salvas!!")

    with col2:
        if st.button("📂 Carregar minhas avaliações"):
            file = RATINGS_DIR / f"{st.session_state['user_email']}_ratings.csv"
            if file.exists():
                saved = pd.read_csv(file)
                for _, r in saved.iterrows():
                    st.session_state["ratings"][r["index"]] = int(r["rating"])
                st.rerun()
            else:
                st.warning("Nenhuma avaliação salva até o momento.")
    
    # ← CARREGUE AUTOMATICAMENTE ao entrar
    if not st.session_state.get("ratings_loaded", False):
        file_path = RATINGS_DIR / f"{user_email}_ratings.csv"
        if file_path.exists():
            saved = pd.read_csv(file_path)
            for _, r in saved.iterrows():
                st.session_state["ratings"][r["index"]] = int(r["rating"])
        st.session_state["ratings_loaded"] = True
    
    # ← ADICIONE LOGOUT
    custom_divider(margin="0.5rem")
    if st.button("🔴 Sair", use_container_width=True, key="btn_logout"):
        st.session_state.clear()
        st.rerun()

    # --- FILTER WIDGETS ---
    col3, col4 = st.columns(2)
    with col3:
        months_sel = st.multiselect("Mês", month_labels_available, key="month_sel_labels")
    with col4:
        weekdays_sel = st.multiselect("Dia da semana", options["dia_semana"], key="weekday_sel")
    
    col5, col6 = st.columns(2)
    with col5:
        series_sel = st.multiselect("Série", options["serie"], key="series_sel")

    filters_for_compositor = {
        "serie": series_sel,  # ← Variável local (atual)
        "compositor": [],
        "dia_semana": weekdays_sel,  # ← Variável local (atual)
        "mês": [num_month(x) for x in months_sel],  # ← Variável local (atual)
    }
    _, options_for_compositor = get_available_options(df, filters_for_compositor)
    
    with col6:
        composers_sel = st.multiselect("Compositor", options_for_compositor["compositor"], key="composers_sel")

    # --- TOGGLE ENTRE ANÁLISE E PROGRAMAS ---
    custom_divider(margin="0.5rem")
    st.subheader("📊 Análise")
    col9, col10 = st.columns(2, gap="small")
    with col9:
        if st.button("📈 Ver Cobertura de Ratings", use_container_width=True):
            st.session_state["page"] = "analise"
    with col10:
        if st.button("🎵 Avaliar os Programas", use_container_width=True):
            st.session_state["page"] = "programas"

    # --- RESET FILTERS ---
    custom_divider(margin="0.5rem")
    col7, col8 = st.columns(2, gap="small")
    
    with col7:
        st.button("🔄 Limpar filtros", on_click=clear_all_filters, use_container_width=True, key = "btn_clear")
    
    with col8:
        if st.button("🔴 Resetar Tudo", use_container_width=True, key="btn_reset"):
            st.session_state["show_reset_confirmation"] = True

    # Mostra confirmação
    if st.session_state.get("show_reset_confirmation", False):
        st.warning("⚠️ Isso apagará TODOS os ratings e filtros!")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("✓ Sim, resetar", key="confirm_yes"):
                # ← Salva dados de login
                logged_in = st.session_state.get("logged_in")
                user_email = st.session_state.get("user_email")
                user_nome = st.session_state.get("user_nome")
                
                # ← Deleta todo session_state
                st.session_state.clear()
                
                # ← Restaura login
                st.session_state["logged_in"] = logged_in
                st.session_state["user_email"] = user_email
                st.session_state["user_nome"] = user_nome

                st.session_state["ratings"] = {}
                st.session_state["ratings_loaded"] = True
                
                st.success("✓ Dados resetados! Você continua logado.")
                st.rerun()
        with col_no:
            if st.button("✗ Cancelar", key="confirm_no"):
                st.session_state["show_reset_confirmation"] = False
                st.rerun()
    


# --- Convert month labels to numbers for filtering ---
month_nums = [num_month(m) for m in st.session_state.get("month_sel_labels", [])]

# # --- Build filters ---
filters = {
    "serie": series_sel,
    "compositor": composers_sel,
    "dia_semana": weekdays_sel,
    "mês": [num_month(x) for x in months_sel],
}

# Apply filters to get available options
filtered, options = get_available_options(df, filters)

# Inicializa página padrão
if "page" not in st.session_state:
    st.session_state["page"] = "programas"

# --- MAIN CONTENT ---
if st.session_state["page"] == "programas":
    st.subheader("🎵 Programas e Avaliação")
    st.subheader("Avalie cada programa: 3- Imperdível; 2- Muito bom; 1- Interessante; 0- Não me agrada")
    st.subheader(f"{len(filtered['program_id'].unique())} programas num total de {len(filtered['titulo'].unique())} obras executadas")

    # --- SHOW + RATE PROGRAMS ---
    df_show = (
        filtered.groupby(["program_id", "work_order", "titulo", "compositor"], sort=False)
        .agg({"regente": set, "concerto": list})
        .reset_index()
    )

    def join_regente(val):
        if not val or (isinstance(val, float) and pd.isna(val)):
            return ""
        return ", ".join(str(v) for v in val if pd.notna(v))

    df_show["regente"] = df_show["regente"].apply(join_regente)
    df_show["concerto"] = df_show["concerto"].apply(lambda x: ", ".join(sorted(set(x))))

    custom_divider(margin="0.5rem")
    st.subheader("🎵 Programas e Avaliação")

    for pid, g in df_show.groupby("program_id", sort=False):
        with st.container(border=True):
            cols = st.columns([5, 1])
            with cols[0]:
                st.markdown(f"### 🎼 Programa {pid}")
                for _, row in g.iterrows():
                    st.markdown(f"- **{row['titulo']}** — *{row['compositor']}*")
                regentes = ", ".join(sorted(set(g["regente"]) - {""}))
                concertos = ", ".join(sorted(set(", ".join(g["concerto"]).split(", "))))
                st.caption(f"👨‍🏫 Regente(s): {regentes}\n\n📅 Concertos: {concertos}")
            with cols[1]:
                current_rating = st.session_state["ratings"].get(pid, 0)
                st.radio("⭐ Avaliação", [0, 1, 2, 3],
                    horizontal=True, key=f"r_{pid}",
                    index=current_rating)
    for pid in df_show["program_id"].unique():
        st.session_state["ratings"][pid] = st.session_state.get(f"r_{pid}", 0)

elif st.session_state["page"] == "analise":

    st.subheader("📊 Cobertura de Avaliações por Série")

    rated_programs = [pid for pid, rating in st.session_state["ratings"].items() if rating > 0]

    if len(rated_programs) > 0:
        coverage_data = defaultdict(dict)
        for rate in range(1, 4):
            programs_in_rate = [pid for pid, rating in st.session_state["ratings"].items() if rating == rate]
            if len(programs_in_rate) > 0:
                for serie in sorted(df["serie"].dropna().unique()):
                    programs_in_serie = df[df["serie"] == serie]["program_id"].unique()
                    abs_cov = len(set(programs_in_rate).intersection(set(programs_in_serie)))
                    rel_cov = abs_cov / len(programs_in_rate) * 100
                    coverage_data[serie][rate] = rel_cov
        
        
        # Calcula um score de prioridade para cada série
        # Prioriza rating 3, depois 2, depois 1

        series_scores = {}

        for serie in coverage_data.keys():
            score = (
                coverage_data[serie].get(3, 0) * 5 +
                coverage_data[serie].get(2, 0) * 3 +
                coverage_data[serie].get(1, 0) * 1
            )
            series_scores[serie] = score

        # Ordena por score decrescente (maior primeiro)
        series_names = sorted(coverage_data.keys(), key=lambda x: series_scores[x], reverse=True)
        series_weeks = []
        for serie in series_names:
            weekdays = df[df['serie']==serie]['dia_semana'].value_counts().index.tolist()
            series_weeks.append(weekdays)
        
        series_axis_names = [n + ' (' + ' '.join(w) + ')' for n,w in zip(series_names,series_weeks)]

        ratings = [1, 2, 3]

        fig = go.Figure()

        colors = {
            1: "#FF6B6B",  # Vermelho
            2: "#FFA500",  # Laranja
            3: "#4ECDC4"   # Teal
        }
        for rate in ratings:
            coverages = [coverage_data[serie].get(rate, 0) for serie in series_names]
            fig.add_trace(go.Bar(
                name=f"Rating {rate} ⭐",
                x=series_axis_names,
                y=coverages,
                text=[f"{cov:.0f}%" for cov in coverages],
                textposition="auto",
                marker=dict(color=colors[rate]),
                hovertemplate="<b>%{x}</b><br>Cobertura: %{y:.1f}%<extra></extra>"
            ))

        fig.update_layout(
            barmode='group',
            title="Cobertura de Ratings por Série",
            xaxis_title="Série",
            yaxis_title="Cobertura (%)",
            hovermode='x unified',
            height=700
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("💡 Comece a avaliar programas para ver a cobertura!")