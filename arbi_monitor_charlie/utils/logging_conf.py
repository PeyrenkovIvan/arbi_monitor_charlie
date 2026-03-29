# arbi_monitor/utils/logging_conf.py
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

def setup_logging():
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    app_log = LOG_DIR / "app.log"
    alerts_log = LOG_DIR / "alerts.log"

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Console
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    root.addHandler(ch)

    # App log
    fh1 = RotatingFileHandler(app_log, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    fh1.setFormatter(fmt)
    fh1.setLevel(logging.INFO)
    root.addHandler(fh1)

    # Alerts log (будем писать сюда при достижении цели)
    fh2 = RotatingFileHandler(alerts_log, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    fh2.setFormatter(fmt)
    fh2.setLevel(logging.INFO)
    logging.getLogger("alerts").addHandler(fh2)
    logging.getLogger("alerts").setLevel(logging.INFO)
