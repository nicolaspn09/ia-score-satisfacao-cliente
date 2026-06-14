# utils/logging_utils.py
import logging
import time
from contextlib import contextmanager
from typing import Optional

# Emojis centralizados
E = {
    "start": "🚀",
    "ok": "✅",
    "warn": "⚠️",
    "err": "❌",
    "info": "ℹ️",
    "spark": "✨",
    "calc": "🧮",
    "clock": "⏱️",
    "filter": "🧹",
    "group": "🧩",
    "merge": "🔗",
    "save": "💾",
    "sql": "🗃️",
    "conf": "⚙️",
}

# Controle global simples para prints com emoji
ENABLE_PRINTS = False
WITH_EMOJI = True

def setup_logging(level: str = "INFO", log_file: Optional[str] = None, with_emoji: bool = True, enable_prints: bool = True):
    """
    Configura logging e comportamento dos prints com emoji.
    """
    global ENABLE_PRINTS, WITH_EMOJI
    ENABLE_PRINTS = bool(enable_prints)
    WITH_EMOJI = bool(with_emoji)

    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=handlers,
        force=True,
    )
    logging.getLogger(__name__).info("%s Logging pronto | level=%s | file=%s",
                                     f'{E["spark"] if WITH_EMOJI else ""}', level, log_file)

def _e(emoji_key: str) -> str:
    return E.get(emoji_key, "•") if WITH_EMOJI else ""

def p(msg: str, emoji: str = "info"):
    """
    Print amigável com emoji (controlado por ENABLE_PRINTS).
    """
    if ENABLE_PRINTS:
        print(f"{_e(emoji)} {msg}")

@contextmanager
def step(label: str, emoji: str = "start"):
    """
    Context manager para medir tempo de etapas: 
    with step('Agregando pedidos', 'group'): ...
    """
    t0 = time.time()
    p(f"Iniciando: {label}", emoji)
    logger = logging.getLogger("step")
    logger.info("%s %s", _e(emoji), label)
    try:
        yield
        dt = time.time() - t0
        p(f"Concluído: {label} ({dt:.2f}s)", "ok")
        logger.info("%s Concluído em %.2fs: %s", _e("ok"), dt, label)
    except Exception as e:
        dt = time.time() - t0
        p(f"Falhou: {label} ({dt:.2f}s) -> {e}", "err")
        logger.exception("%s Falhou em %.2fs: %s", _e("err"), dt, label)
        raise
