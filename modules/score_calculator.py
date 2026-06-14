# modules/score_calculator.py
import logging
import numpy as np
import pandas as pd
from utils.logging_utils import p, step, E

logger = logging.getLogger(__name__)

def _winsorize(s, p_low=0.01, p_high=0.99):
    lo, hi = s.quantile(p_low), s.quantile(p_high)
    return s.clip(lo, hi)

def _percentile_score(group_s, weight, higher_is_better=True, tie_method="dense"):
    r = group_s.rank(pct=True, ascending=higher_is_better, method=tie_method)
    return (r * abs(weight)).clip(0, abs(weight))

def _minmax_score(group_s, weight, higher_is_better=True):
    s = group_s if higher_is_better else -group_s
    smin, smax = s.min(), s.max()
    if pd.isna(smin) or pd.isna(smax) or smax == smin:
        return pd.Series(np.full(len(s), float(abs(weight))), index=s.index)
    norm = (s - smin) / (smax - smin)
    return (norm * abs(weight)).clip(0, abs(weight))

def _minmax_log_winsor_score(group_s, weight, higher_is_better=True, p_low=0.01, p_high=0.99):
    s = _winsorize(group_s, p_low, p_high).clip(lower=0)
    s = np.log1p(s)
    return _minmax_score(s, weight, higher_is_better)

def _binary_flag_score(group_s, weight, true_is_bad=True):
    s = group_s.fillna(False).astype(bool)
    return pd.Series(np.where(s if true_is_bad else ~s, 0.0, float(weight)), index=s.index)

def _capped_rate_score(group_s, weight, cap=0.03, higher_is_better=False):
    s = pd.to_numeric(group_s, errors="coerce").fillna(0.0).clip(lower=0.0)
    norm = (s / cap).clip(0, 1)
    return (norm * float(weight)) if higher_is_better else ((1 - norm) * float(weight))

def _capped_count_score(group_s, weight, cap=3, higher_is_better=False):
    s = pd.to_numeric(group_s, errors="coerce").fillna(0).clip(lower=0)
    norm = (s / cap).clip(0, 1)
    return (norm * float(weight)) if higher_is_better else ((1 - norm) * float(weight))

def score_clientes(df_base: pd.DataFrame, group_col: str, client_col: str, metrics_cfg: list, verbose=False):
    p("Iniciando cálculo de SCORE", "start")
    logger.info("%s score_clientes | linhas=%s", E["spark"], len(df_base))

    df = df_base.copy()
    key_cols = [group_col, client_col]

    if df.duplicated(key_cols).any():
        with step("Consolidando duplicatas por soma", "group"):
            num_cols = df.select_dtypes(include=[np.number]).columns.difference(key_cols)
            df = df.groupby(key_cols, as_index=False).agg({c: "sum" for c in num_cols})
            p(f"Consolidadas duplicatas -> {len(df)} linhas únicas", "ok")

    # Processa cada métrica
    with step("Aplicando métricas", "calc"):
        for m in metrics_cfg:
            name = m["name"]; col = m["col"]; weight = float(m["weight"])
            method = m.get("method", "percentile")
            hib = bool(m.get("higher_is_better", True))

            if col not in df.columns:
                p(f"[AVISO] Coluna ausente: {col} (métrica {name})", "warn")
                logger.warning("%s Coluna ausente '%s' para métrica '%s'", E["warn"], col, name)
                continue

            df[col] = pd.to_numeric(df[col], errors="coerce").replace([np.inf, -np.inf], np.nan)

            def _apply(g):
                gs = g[col]
                if gs.notna().sum() == 0:
                    return pd.Series(np.zeros(len(gs)), index=g.index)
                valid = gs.fillna(gs.median())
                if method == "percentile":
                    return _percentile_score(valid, weight, hib, m.get("tie_method", "dense"))
                elif method == "minmax":
                    return _minmax_score(valid, weight, hib)
                elif method == "minmax_log_winsor":
                    return _minmax_log_winsor_score(valid, weight, hib, m.get("p_low", 0.01), m.get("p_high", 0.99))
                elif method == "binary_flag":
                    return _binary_flag_score(valid.astype(bool), weight, m.get("true_is_bad", True))
                elif method == "capped_rate":
                    return _capped_rate_score(valid, weight, m.get("cap", 0.03), hib)
                elif method == "capped_count":
                    return _capped_count_score(valid, weight, m.get("cap", 3), hib)
                else:
                    raise ValueError(f"Método desconhecido: {method}")

            score_col = f"SCORE__{name}"
            df[score_col] = df.groupby(group_col, group_keys=False).apply(_apply)
            p(f"Métrica aplicada: {name} ➜ {score_col}", "calc")
            logger.info("%s Métrica '%s' aplicada", E["calc"], name)

    # Score total e ordenação
    with step("Calculando SCORE_TOTAL e ordenando", "calc"):
        score_cols = [c for c in df.columns if c.startswith("SCORE__")]
        df["SCORE_TOTAL"] = df[score_cols].sum(axis=1)
        df = df.sort_values([group_col, "SCORE_TOTAL"], ascending=[True, False]).reset_index(drop=True)
        p(f"Score total pronto | colunas de score: {len(score_cols)}", "ok")
        logger.info("%s SCORE_TOTAL calculado | #score_cols=%s", E["ok"], len(score_cols))

    p("Cálculo de SCORE concluído 🎯", "ok")
    return df, score_cols
