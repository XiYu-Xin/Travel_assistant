"""配置模块"""

import os
from pathlib import Path

def get_root_path() -> Path:
    """获取项目根目录（向上查找含 config.yaml 的目录）"""
    current = Path(__file__).resolve().parent
    for parent in [current, *current.parents]:
        if (parent / "config.yaml").exists() or (parent / ".gitignore").exists():
            return parent
    raise RuntimeError("未找到项目根目录")