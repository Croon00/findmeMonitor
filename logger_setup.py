import logging
from logging.handlers import RotatingFileHandler
from config import LOG_FILE, ERROR_LOG_FILE

def setup_logger():
    logger = logging.getLogger("findme")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(fmt)
        logger.addHandler(ch)

        fh = RotatingFileHandler(LOG_FILE, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

        eh = RotatingFileHandler(ERROR_LOG_FILE, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
        eh.setLevel(logging.WARNING)
        eh.setFormatter(fmt)
        logger.addHandler(eh)

    return logger