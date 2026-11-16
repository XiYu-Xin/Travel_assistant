"""爬虫基类 - 统一限速、重试、会话管理与落盘"""

import os
import sys
import time
import threading
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from src.utils.config import get_root_path

import requests
from loguru import logger

class TokenBucket:
    """线程安全的令牌桶限速器

    acquire() 在锁内计算并 sleep，保证所有线程共享同一个全局速率。
    rate  = 每秒补充的令牌数（即每秒最多请求数）
    capacity = 桶容量，允许的突发请求数
    """

    def __init__(self, rate: float = 2.0, capacity: float = 5.0):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self, tokens: float = 1.0) -> None:
        if self.rate <= 0:
            raise ValueError("rate 必须 > 0")
        while True:
            with self.lock:
                now = time.monotonic()
                self.tokens = min(self.capacity,
                                  self.tokens + (now - self.last) * self.rate)
                self.last = now
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return
                wait = (tokens - self.tokens) / self.rate
            time.sleep(wait)

@dataclass
class RawDocument:
    source: str
    url: str
    fetched_at: str
    content_type: str  # "html" | "json"
    raw_content: str
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class BaseScraper(ABC):
    """爬虫抽象基类
    子类需要自行定义 name / base_domain，并实现 scrape()。
    基类负责：线程安全会话、全局限速、重试、统一落盘、来源元数据。
    """

    name: str = "base"
    base_domain: str = ""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        configured_raw_dir = self.config.get("raw_dir")
        if configured_raw_dir:
            base_raw = Path(configured_raw_dir)
            if not base_raw.is_absolute():
                base_raw = get_root_path() / base_raw
        else:
            base_raw = get_root_path() / "data" / "raw"

        self.raw_dir = base_raw / self.name
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"[{self.name}] 原始文件保存目录：{self.raw_dir}")

        # 每个线程独立 session，既保障线程安全又能复用连接池
        self._local = threading.local()
        self._ua = self.config.get(
            "user_agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36 Edg/157.0.0.0",
        )

        self.bucket = TokenBucket(
            rate=self.config.get("rate", 2.0),
            capacity=self.config.get("capacity", 5.0),
        )
        self.max_retries = self.config.get("max_retries", 3)
        self.timeout = self.config.get("timeout", 15)
        self.encoding = self.config.get("encoding", "utf-8")

    # session
    @property
    def session(self) -> requests.Session:
        if not hasattr(self._local, "session"):
            s = requests.Session()
            s.headers.update({
                "User-Agent": self._ua,
                "Accept-Language": "zh-CN,zh;q=0.9",
            })
            self._local.session = s
        return self._local.session

    # rate limiting & retries
    def _request(self, url: str, **kwargs) -> requests.Response:
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            self.bucket.acquire()
            try:
                resp = self.session.get(url, timeout=self.timeout, **kwargs)
                resp.raise_for_status()
                resp.encoding = self.encoding
                return resp
            except requests.HTTPError as e:
                code = e.response.status_code if e.response is not None else None
                if code and 400 <= code < 500 and code != 429:
                    raise  # 4xx 直接失败
                last_exc = e
            except requests.RequestException as e:
                last_exc = e
                logger.warning(f"[{self.name}] 第 {attempt}/{self.max_retries} 次失败 {url}: {e}")
                time.sleep(min(2**attempt, 10) * (0.5 + random.random()))
        raise last_exc  # type: ignore

    # save
    def _save_raw(self, doc: RawDocument, filename: str) -> Path:
        path = self.raw_dir / filename
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(doc.raw_content, encoding="utf-8")
        os.replace(tmp, path)
        return path

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @abstractmethod
    def scrape(self, **kwargs) -> Any:
        """子类实现具体爬取流程"""
        ...