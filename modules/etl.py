# modules/etl.py
import logging
import numpy as np
import pandas as pd
from utils.logging_utils import setup_logging, p, step, E

logger = logging.getLogger(__name__)

def process_etl(df: pd.DataFrame) -> pd.DataFrame:
    """
    ETL: 1 linha por (CD_SISTEMA_NEGOCIO, CD_CLIENTE)
    """
    p("ETL iniciado", "start")
    logger.info("%s ETL iniciado | linhas=%s colunas=%s", E["spark"], len(df), list(df.columns))

    df_tx = df.copy()
    VALOR_LINHA_COL = "VL_FATURADO_BRUTO"
    CHAVES_PEDIDO = ["CD_EMPRESA", "NR_NFE", "NR_SERIE_NFE"]

    # 1) Filtro tipo de nota
    with step("Filtro ID_TIPO_NOTA=='V'", "filter"):
        if "ID_TIPO_NOTA" in df_tx.columns:
            antes = len(df_tx)
            df_tx = df_tx[df_tx["ID_TIPO_NOTA"] == "V"]
            p(f"Filtrados {antes-len(df_tx)} registros não-V", "filter")
            logger.info("%s Filtro tipo nota | antes=%s depois=%s", E["filter"], antes, len(df_tx))
        else:
            p("Coluna ID_TIPO_NOTA ausente — pulando filtro", "warn")
            logger.warning("%s Coluna ID_TIPO_NOTA ausente", E["warn"])

    # 2) Tipagem
    with step("Normalização de tipos", "calc"):
        df_tx[VALOR_LINHA_COL] = pd.to_numeric(df_tx[VALOR_LINHA_COL], errors="coerce").fillna(0.0)
        df_tx["DT_EMISSAO"] = pd.to_datetime(df_tx["DT_EMISSAO"], errors="coerce")
        n_dt_na = df_tx["DT_EMISSAO"].isna().sum()
        if n_dt_na:
            p(f"Datas DT_EMISSAO inválidas: {n_dt_na}", "warn")
            logger.warning("%s DT_EMISSAO inválidas: %s", E["warn"], n_dt_na)

    # 3) Agregar pedido
    with step("Agregando por pedido (NF)", "group"):
        pedido_keys = ["CD_CLIENTE", "CD_SISTEMA_NEGOCIO"] + CHAVES_PEDIDO + ["DT_EMISSAO"]
        faltantes = [c for c in pedido_keys + [VALOR_LINHA_COL] if c not in df_tx.columns]
        if faltantes:
            p(f"Colunas faltando: {faltantes}", "err")
            logger.error("%s Colunas faltantes: %s", E["err"], faltantes)
            raise KeyError(f"Colunas faltando: {faltantes}")

        pedidos = (
            df_tx
            .groupby(pedido_keys, as_index=False)[VALOR_LINHA_COL]
            .sum()
            .rename(columns={VALOR_LINHA_COL: "VALOR_PEDIDO"})
        )
        p(f"Pedidos criados: {len(pedidos)}", "group")
        logger.info("%s Agregado por pedido | pedidos=%s", E["group"], len(pedidos))

    # 4) Filtrar valor positivo
    with step("Filtrando VALOR_PEDIDO>0", "filter"):
        antes = len(pedidos)
        pedidos = pedidos[pedidos["VALOR_PEDIDO"] > 0]
        p(f"Removidos {antes-len(pedidos)} pedidos sem valor", "filter")
        logger.info("%s VALOR_PEDIDO>0 | antes=%s depois=%s", E["filter"], antes, len(pedidos))

    # 5) Data da compra
    pedidos["DATA_COMPRA"] = pedidos["DT_EMISSAO"].dt.date

    # 6) Métricas por cliente+sistema
    with step("Agregando métricas cliente+sistema", "calc"):
        agg_dias = (
            pedidos
            .groupby(["CD_CLIENTE", "CD_SISTEMA_NEGOCIO"], as_index=False)
            .agg(
                FREQUENCIA_PEDIDOS=("NR_NFE", "nunique"),
                FREQUENCIA_DIAS=("DATA_COMPRA", "nunique"),
                VL_FATURADO_BRUTO=("VALOR_PEDIDO", "sum")
            )
        )
        logger.info("%s Métricas geradas | linhas=%s", E["calc"], len(agg_dias))
        p(f"Métricas geradas: {len(agg_dias)} linhas", "ok")

    # 7) Ticket médio por pedido
    agg_dias["TICKET_MEDIO_PEDIDO"] = (
        agg_dias["VL_FATURADO_BRUTO"] / agg_dias["FREQUENCIA_PEDIDOS"].replace(0, np.nan)
    ).fillna(0.0)

    # 8) Consistência
    def calcular_consistencia_cliente(grupo_pedidos):
        num_pedidos = len(grupo_pedidos)
        if num_pedidos < 2:
            return np.nan
        datas = grupo_pedidos["DT_EMISSAO"].sort_values()
        intervalos = datas.diff().dt.days.dropna()
        if len(intervalos) == 0:
            return np.nan
        desvio = intervalos.std()
        if num_pedidos < 5:
            fator_penalizacao = 1 + (5 - num_pedidos) * 0.5
            desvio_ajustado = desvio * fator_penalizacao
            penalizacao_base = 2.0
            return desvio_ajustado + penalizacao_base
        return desvio

    with step("Calculando consistência (desvio entre compras)", "calc"):
        consistencia_dados = []
        for (cliente, sistema), grupo in pedidos.groupby(["CD_CLIENTE", "CD_SISTEMA_NEGOCIO"]):
            desvio = calcular_consistencia_cliente(grupo)
            consistencia_dados.append({
                "CD_CLIENTE": cliente,
                "CD_SISTEMA_NEGOCIO": sistema,
                "CONSISTENCIA_DESVIO": desvio,
                "NUM_PEDIDOS": len(grupo),
            })
        df_consistencia = pd.DataFrame(consistencia_dados)
        logger.info("%s Consistência calculada | linhas=%s", E["calc"], len(df_consistencia))
        p(f"Consistência calculada para {len(df_consistencia)} grupos", "ok")

    # 9) Merge + preenchimento
    with step("Merge final e penalizações", "merge"):
        df_final = agg_dias.merge(df_consistencia, on=["CD_CLIENTE", "CD_SISTEMA_NEGOCIO"], how="left")

        def penalizacao_sem_consistencia(row):
            if pd.isna(row["CONSISTENCIA_DESVIO"]):
                freq_dias = row.get("FREQUENCIA_DIAS", 1)
                return 8.0 if freq_dias <= 2 else 5.0
            return row["CONSISTENCIA_DESVIO"]

        df_final["CONSISTENCIA_DESVIO"] = df_final.apply(penalizacao_sem_consistencia, axis=1)
        p(f"Linhas finais: {len(df_final)}", "ok")
        logger.info("%s DF final pronto | linhas=%s", E["ok"], len(df_final))

    p("ETL concluído 🎉", "ok")
    return df_final
