"""日志模块"""
"""
program
    ├─ data
        └─raw
    ├─ src
        ├─scraper
            ├─base_scraper.py
            └─ctrip_scraper.py
        └─utils
            ├─logger.py
            └─config.py
    ├─.gitignore
    └─config.yaml
"""
import sys
from pathlib import Path
from loguru import logger
from src.utils.config import get_root_path

def setup_logger(level: str = "INFO") -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    )
    log_dir = get_root_path() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_dir / "scraper_{time:YYYY-MM-DD}.log",
        level=level,
        rotation="00:00",
        retention="7 days",
        encoding="utf-8",
        enqueue=True,          # 多线程安全
        backtrace=True,
        diagnose=False,        # 避免日志泄露敏感变量
    )

