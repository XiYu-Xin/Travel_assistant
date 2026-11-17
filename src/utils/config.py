"""配置模块"""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml

def get_root_path() -> Path:
    """获取项目根目录（向上查找含 config.yaml 的目录）"""
    current = Path(__file__).resolve().parent
    for parent in [current, *current.parents]:
        if (parent / "config.yaml").exists() or (parent / ".gitignore").exists():
            return parent
    raise RuntimeError("未找到项目根目录")

def load_config(filename: str = "config.yaml") -> Dict[str, Any]:
    """加载项目根目录下的YAML配置文件，返回dict（文件为空时返回 {}）"""
    path = get_root_path() / filename
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}

def load_sight_config(
    filename: str = "config.yaml",
    section: str = "sight",
    override: Optional[Dict[str, Dict[str, Any]]] = None,
    default: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Dict[str, Any]]:
    """按优先级加载景点城市配置。

    优先级：
        1. override  —— 显式传入（用于测试 / 临时覆盖）
        2. config.yaml 中的 scraper.<section> 节点
        3. default  —— 兜底（保证 YAML 缺失时爬虫仍能跑）

    Args:
        filename: 配置文件名，默认 config.yaml
        section: scraper 下的子节点名，默认 "sight"
        override: 显式覆盖
        default: 兜底配置

    Raises:
        RuntimeError: 三个来源都为空时抛出
    """
    if override is not None:
        return override

    try:
        data = load_config(filename)
        cities = (data.get("scraper") or {}).get(section)
        if cities is not None:
            return cities
    except (FileNotFoundError, yaml.YAMLError, RuntimeError):
        # 配置文件缺失或 YAML 语法错误 或 get_root_path 失败时，落到 default 兜底
        pass

    if default is not None:
        return default
    raise RuntimeError(
        f"未能从 {filename} 的 scraper.{section} 加载城市配置，"
        f"且未提供 override 或 default"
    )