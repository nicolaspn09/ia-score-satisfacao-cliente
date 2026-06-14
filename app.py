import streamlit as st
import pandas as pd
import numpy as np
import yaml
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go

from modules.etl import process_etl
from modules.score_calculator import score_clientes

# ========================
# Configuração Streamlit
# ========================
st.set_page_config(
    page_title="Score Simulator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================
# Estilos CSS
# ========================
st.markdown("""
    <style>
    .metric-box {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .score-high {
        color: #28a745;
        font-weight: bold;
    }
    .score-low {
        color: #dc3545;
        font-weight: bold;
    }
    .score-medium {
        color: #ffc107;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# ========================
# Inicialização de Estado
# ========================
if "df_etl" not in st.session_state:
    st.session_state.df_etl = None
if "df_score" not in st.session_state:
    st.session_state.df_score = None
if "config" not in st.session_state:
    st.session_state.config = None
if "metrics_config" not in st.session_state:
    st.session_state.metrics_config = None

# ========================
# Função para carregar config padrão
# ========================
def load_default_config():
    config_path = Path(__file__).parent / "config" / "default_config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# ========================
# SIDEBAR - Controles
# ========================
st.sidebar.title("⚙️ Configurações")

# 1. Upload de arquivo
st.sidebar.subheader("1️⃣ Carregar Dados")
uploaded_file = st.sidebar.file_uploader(
    "Selecione um arquivo CSV",
    type=["csv"],
    help="Arquivo deve conter colunas: CD_CLIENTE, CD_SISTEMA_NEGOCIO, VL_FATURADO_BRUTO, etc."
)

if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file)
    st.session_state.df_etl = process_etl(df_raw)
    st.sidebar.success(f"✅ Arquivo carregado! {len(df_raw)} linhas processadas")

# 2. Carregar configuração padrão
if st.session_state.config is None:
    st.session_state.config = load_default_config()

# 3. Seleção de métricas
st.sidebar.subheader("2️⃣ Selecionar Métricas")

default_config = st.session_state.config
available_metrics = default_config.get("metrics", [])

# Criar colunas para seleção de métricas
selected_metrics = []
for metric in available_metrics:
    col1, col2 = st.sidebar.columns([3, 1])
    
    with col1:
        is_selected = st.checkbox(
            f"✓ {metric['name']}",
            value=True,
            key=f"metric_{metric['name']}"
        )
    
    if is_selected:
        selected_metrics.append(metric)

# 4. Ajuste de pesos
st.sidebar.subheader("3️⃣ Ajustar Pesos")

adjusted_metrics = []
total_weight = 0

for metric in selected_metrics:
    weight = st.sidebar.slider(
        f"{metric['name']} (Peso)",
        min_value=0,
        max_value=100,
        value=int(metric["weight"]),
        step=5,
        key=f"weight_{metric['name']}"
    )
    
    metric_copy = metric.copy()
    metric_copy["weight"] = weight
    adjusted_metrics.append(metric_copy)
    total_weight += weight

# Mostrar total de peso
if total_weight > 0:
    st.sidebar.info(f"📊 Peso Total: {total_weight}")

# 5. Threshold para aceite
st.sidebar.subheader("4️⃣ Definir Threshold")
threshold = st.sidebar.slider(
    "Score Mínimo para Aceite",
    min_value=0,
    max_value=int(total_weight) if total_weight > 0 else 100,
    value=int(total_weight * 0.5) if total_weight > 0 else 50,
    step=1,
    key="threshold"
)

# 6. Botão para executar cálculo
st.sidebar.subheader("5️⃣ Executar Simulação")

if st.sidebar.button("🚀 Calcular Score", use_container_width=True):
    if st.session_state.df_etl is None:
        st.sidebar.error("❌ Por favor, carregue um arquivo CSV primeiro!")
    elif len(adjusted_metrics) == 0:
        st.sidebar.error("❌ Selecione pelo menos uma métrica!")
    else:
        print(st.session_state.df_etl)
        with st.spinner("⏳ Calculando scores..."):
            df_result, score_cols = score_clientes(
                st.session_state.df_etl,
                group_col="CD_SISTEMA_NEGOCIO",
                client_col="CD_CLIENTE",
                metrics_cfg=adjusted_metrics,
                verbose=False
            )
            st.session_state.df_score = df_result
            st.session_state.metrics_config = adjusted_metrics
            st.sidebar.success("✅ Scores calculados com sucesso!")

            print(df_result, score_cols)

# ========================
# MAIN CONTENT
# ========================
st.title("📊 Score Simulator - Simulação de Score de Clientes")

if st.session_state.df_score is None:
    st.info("👈 Configure as métricas e clique em 'Calcular Score' para começar!")
else:
    df_score = st.session_state.df_score
    
    # ========================
    # Estatísticas Gerais
    # ========================
    st.subheader("📈 Estatísticas Gerais")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Clientes", len(df_score))
    
    with col2:
        st.metric("Score Médio", f"{df_score['SCORE_TOTAL'].mean():.2f}")
    
    with col3:
        aceitos = len(df_score[df_score['SCORE_TOTAL'] >= threshold])
        st.metric("Clientes Aceitos", aceitos)
    
    with col4:
        rejeitados = len(df_score[df_score['SCORE_TOTAL'] < threshold])
        st.metric("Clientes Rejeitados", rejeitados)
    
    # ========================
    # Filtro por Sistema de Negócio
    # ========================
    st.subheader("🔍 Filtrar por Sistema de Negócio")
    
    sistemas = sorted(df_score["CD_SISTEMA_NEGOCIO"].unique())
    sistema_selecionado = st.selectbox(
        "Selecione um Sistema de Negócio",
        sistemas,
        key="sistema_select"
    )
    
    df_filtrado = df_score[df_score["CD_SISTEMA_NEGOCIO"] == sistema_selecionado]
    
    # ========================
    # Visualizações
    # ========================
    col_viz1, col_viz2 = st.columns(2)
    
    with col_viz1:
        # Distribuição de Scores
        fig_dist = px.histogram(
            df_filtrado,
            x="SCORE_TOTAL",
            nbins=20,
            title=f"Distribuição de Scores - {sistema_selecionado}",
            labels={"SCORE_TOTAL": "Score Total"},
            color_discrete_sequence=["#1f77b4"]
        )
        fig_dist.add_vline(
            x=threshold,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Threshold: {threshold}",
            annotation_position="top right"
        )
        st.plotly_chart(fig_dist, use_container_width=True)
    
    with col_viz2:
        # Gráfico de Pizza - Aceito/Rejeitado
        aceitos_filtro = len(df_filtrado[df_filtrado['SCORE_TOTAL'] >= threshold])
        rejeitados_filtro = len(df_filtrado[df_filtrado['SCORE_TOTAL'] < threshold])
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=['Aceitos', 'Rejeitados'],
            values=[aceitos_filtro, rejeitados_filtro],
            marker=dict(colors=['#28a745', '#dc3545']),
            textposition='inside',
            textinfo='label+percent'
        )])
        fig_pie.update_layout(
            title=f"Classificação - {sistema_selecionado}",
            height=400
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    # ========================
    # Tabela de Resultados
    # ========================
    st.subheader(f"📋 Ranking de Clientes - {sistema_selecionado}")
    
    # Preparar dados para exibição
    df_display = df_filtrado.copy()
    
    # Adicionar coluna de status
    df_display["Status"] = df_display["SCORE_TOTAL"].apply(
        lambda x: "✅ Aceito" if x >= threshold else "❌ Rejeitado"
    )
    
    # Selecionar colunas para exibir
    colunas_exibir = ["CD_CLIENTE", "SCORE_TOTAL", "Status"]
    
    # Adicionar colunas de scores individuais se existirem
    score_cols = [c for c in df_display.columns if c.startswith("SCORE__")]
    for col in score_cols:
        metric_name = col.replace("SCORE__", "")
        colunas_exibir.append(col)
    
    # Adicionar colunas de dados originais
    for col in ["VL_FATURADO_BRUTO", "FREQUENCIA_DIAS", "TICKET_MEDIO_PEDIDO", "CONSISTENCIA_DESVIO", "INAD_FLAG"]:
        if col in df_display.columns:
            colunas_exibir.append(col)
    
    df_display = df_display[colunas_exibir].reset_index(drop=True)
    
    # Formatar números
    for col in df_display.columns:
        if col.startswith("SCORE__") or col == "SCORE_TOTAL":
            df_display[col] = df_display[col].round(2)
        elif col in ["VL_FATURADO_BRUTO", "TICKET_MEDIO_PEDIDO"]:
            df_display[col] = df_display[col].round(2)
        elif col == "CONSISTENCIA_DESVIO":
            df_display[col] = df_display[col].round(2)
    
    # Exibir tabela
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "SCORE_TOTAL": st.column_config.NumberColumn(
                "Score Total",
                format="%.2f"
            ),
            "CD_CLIENTE": st.column_config.TextColumn("Cliente"),
            "Status": st.column_config.TextColumn("Status"),
        }
    )
    
    # ========================
    # Download de Resultados
    # ========================
    st.subheader("💾 Exportar Resultados")
    
    csv = df_display.to_csv(index=False)
    st.download_button(
        label="📥 Baixar CSV",
        data=csv,
        file_name=f"score_resultado_{sistema_selecionado}.csv",
        mime="text/csv"
    )
    
    # ========================
    # Resumo de Configuração
    # ========================
    st.subheader("⚙️ Configuração Aplicada")
    
    config_info = f"""
    **Métricas Utilizadas:**
    """
    for metric in st.session_state.metrics_config:
        config_info += f"\n- **{metric['name']}**: Peso {metric['weight']} | Método: {metric['method']}"
    
    config_info += f"\n\n**Threshold de Aceite:** {threshold}"
    
    st.info(config_info)
