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

def setup_logger() -> None:
    """配置 loguru 日志"""
    pass

