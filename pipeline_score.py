# pipeline_score.py
from modules.etl import process_etl
from modules.score_calculator import score_clientes
from database.database import conectar_oracle
import pandas as pd
import yaml
from pathlib import Path
import logging
from utils.logging_utils import setup_logging, p, step, E

logger = logging.getLogger(__name__)

def pipeline_score(path_configs: Path | str):
    # Inicializa logging + prints com emojis
    setup_logging(level="INFO", log_file="logs/pipeline.log", with_emoji=True, enable_prints=True)

    with step("Lendo YAML de configuração", "conf"):
        with open(path_configs, 'r', encoding='utf-8') as file:
            configs = yaml.safe_load(file)
        available_metrics = configs.get("metrics", [])
        querys = configs.get('query', {})
        query_inadimplencia = querys.get('inadimplencia')
        query_vendas = querys.get('vendas')
        p(f"Métricas configuradas: {len(available_metrics)}", "conf")

    with step("Conectando ao Oracle e executando SQL", "sql"):
        conexao = conectar_oracle()
        with open(query_vendas, 'r', encoding='utf-8') as file:
            sql_vendas = yaml.safe_load(file)
        with open(query_inadimplencia, 'r', encoding='utf-8') as file:
            sql_inad = yaml.safe_load(file)

        df_vendas = pd.read_sql(sql_vendas, conexao)
        df_inadimplencia = pd.read_sql(sql_inad, conexao)

        p(f"Vendas: {len(df_vendas)} linhas | Inadimplência: {len(df_inadimplencia)} linhas", "sql")
        logger.info("%s Tabelas carregadas | vendas=%s inad=%s", E["sql"], len(df_vendas), len(df_inadimplencia))

    with step("Executando ETL de vendas", "start"):
        df_etl = process_etl(df_vendas)
        clientes_vendas = df_etl['CD_CLIENTE'].drop_duplicates().to_list()
        p(f"Clientes com movimentação: {len(clientes_vendas)}", "info")

    with step("Identificando clientes sem movimentação", "filter"):
        df_sem_score = df_vendas[~df_vendas['CD_CLIENTE'].isin(clientes_vendas)]
        p(f"Sem movimentação: {df_sem_score['CD_CLIENTE'].nunique()} clientes", "warn")

    with step("Aplicando flag de inadimplência", "merge"):
        df_inadimplencia['INAD_FLAG'] = True
        df_inadimplencia = df_inadimplencia[["CD_CLIENTE", "INAD_FLAG"]].drop_duplicates()
        df_com_inadimplencia = pd.merge(
            df_etl,
            df_inadimplencia,
            on="CD_CLIENTE",
            how="left"
        )
        df_com_inadimplencia['INAD_FLAG'] = df_com_inadimplencia['INAD_FLAG'].fillna(False).astype(bool)
        p(f"Inadimplentes marcados: {df_com_inadimplencia['INAD_FLAG'].sum()}", "merge")

    with step("Preparando métricas e pesos", "calc"):
        adjusted_metrics = []
        total_weight = 0
        for metric in available_metrics:
            metric_copy = metric.copy()
            weight = int(metric_copy.get("weight", 0))
            adjusted_metrics.append(metric_copy)
            total_weight += weight
        p(f"Métricas ativas: {len(adjusted_metrics)} | peso total={total_weight}", "calc")

    with step("Calculando SCORE por cliente", "calc"):
        df_score, score_cols = score_clientes(
            df_com_inadimplencia,
            group_col="CD_SISTEMA_NEGOCIO",
            client_col="CD_CLIENTE",
            metrics_cfg=adjusted_metrics,
            verbose=False
        )
        p(f"Score gerado: {len(df_score)} linhas | {len(score_cols)} colunas de score", "ok")

    p("Pipeline concluído 🏁", "ok")
    return df_score, df_sem_score
