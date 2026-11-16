"""携程景点爬虫 - 两阶段：Selenium 发现 URL + requests 抓详情

阶段一（发现）：城市列表页由 JS 渲染，必须用 Selenium；
              复用同一个 driver 跨页跨城市，避免反复启停浏览器。
阶段二（详情）：景点详情页是服务端渲染，用 requests + TokenBucket 限速；
              可多线程并发，由 detail_workers 控制。

保留自 test03_2：driver 复用、失败清单、随机停顿。
保留自 test04：parse_sight_url、extract_modules、{cls}.{district_id}.{sight_id}.html 命名。
"""

import re
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from loguru import logger

try:
    from base_scraper import BaseScraper, RawDocument
except ImportError:
    from src.scraper.base_scraper import BaseScraper, RawDocument

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    _SELENIUM_OK = True
except ImportError:  # 只爬取详情页
    _SELENIUM_OK = False

DEFAULT_CITY_CONFIG: Dict[str, Dict[str, object]] = {
    "海口": {"district_id": "haikou37",     "pages": 4},
    "三亚": {"district_id": "sanya61",      "pages": 5},
    "陵水": {"district_id": "lingshui1509", "pages": 3},
    "万宁": {"district_id": "wanning846",   "pages": 2},
    "琼海": {"district_id": "qionghai843",  "pages": 2},
    "文昌": {"district_id": "wenchang1007", "pages": 2},
}

@dataclass
class SightLink:
    city: str
    cls: str            # 路径第一段，景点为 "sight"
    district_id: str
    sight_id: str
    url: str

# URL解析工具
def parse_sight_url(url: str) -> Tuple[str, str, str]:
    """从URL解析出 (cls, district_id, sight_id)

    例：https://you.ctrip.com/sight/haikou37/3175.html?poiType=3
        -> ("sight", "haikou37", "3175")
    """
    path = urlparse(url).path
    m = re.match(r"^/([^/]+)/([^/]+)/(\d+)\.html$", path)
    if not m:
        raise ValueError(f"URL 结构不符合预期：{url}")
    return m.group(1), m.group(2), m.group(3)

# base_info、detail、comment提取工具
def extract_modules(html: str):
    """
    从原始 HTML 中提取 baseInfoMain、detailModuleRef 和 commentModuleRef
    """
    soup = BeautifulSoup(html, "html.parser")

    base_info = soup.select_one('div[class*="baseInfoMain"]')
    if base_info is None:
        print("[INFO]:baseInfoMain not found")

    main = soup.select_one('div[class*="mainModule"]')
    if main is None:
        raise ValueError("[INFO]:mainModule not found")
    detail = main.select_one('div[class*="detailModuleRef"]')
    comment = main.select_one('div[class*="commentModuleRef"]')
    return base_info, detail, comment

# 数据封装工具
def wrap_modules(base_info, detail, comment, source_url: str = "") -> str:
    """包装成最小 HTML 骨架，并把来源元数据写进 <head>"""
    from datetime import datetime, timezone
    crawled_at = datetime.now(timezone.utc).isoformat()
    chunks = [
        "<!DOCTYPE html>",
        '<html><head><meta charset="utf-8">',
        f'<meta name="source-url" content="{source_url}">',
        f'<meta name="crawled-at" content="{crawled_at}">',
        '<meta name="comment-page" content="1">',
        "</head><body>",
        '<div class="mainModule">',
    ]

    if base_info is not None:
        chunks.append(str(base_info))
    if detail is not None:
        chunks.append(str(detail))
    if comment is not None:
        chunks.append(str(comment))
    chunks.append("</div></body></html>")
    return "\n".join(chunks)

# 主程序
class CtripScraper(BaseScraper):
    name = "ctrip"
    base_domain = "you.ctrip.com"

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.base_url = self.config.get("base_url", "https://you.ctrip.com")
        self.city_config = self.config.get("cities", DEFAULT_CITY_CONFIG)
        self.detail_workers = self.config.get("detail_workers", 1)
        self.page_delay = tuple(self.config.get("page_delay", (1.0, 3.0)))

        self._driver = None
        self._driver_lock = threading.Lock()
        self._fail_lock = threading.Lock()
        self.failed_discoveries: List[Tuple[str, int]] = []
        self.failed_details: List[str] = []

    # 阶段一：Selenium 发现
    def _get_driver(self):
        if not _SELENIUM_OK:
            raise RuntimeError("未安装 selenium，无法执行发现阶段")
        with self._driver_lock:
            if self._driver is None:
                options = webdriver.ChromeOptions()
                options.add_argument("--disable-gpu")
                options.add_argument("--blink-settings=imagesEnabled=false")
                options.add_argument(f"--user-agent={self._ua}")
                self._driver = webdriver.Chrome(options=options)
                logger.info("[ctrip] 启动 Chrome driver（复用模式）")
            return self._driver

    def close(self) -> None:
        with self._driver_lock:
            if self._driver is not None:
                self._driver.quit()
                self._driver = None
                logger.info("[ctrip] 关闭 Chrome driver")

    def _discover_page(self, district_id: str, page_num: int) -> List[str]:
        driver = self._get_driver()
        url = f"{self.base_url}/sight/{district_id}/s0-p{page_num}.html"
        driver.get(url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'div[class*="sightItemCard_box"]')
            )
        )
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards = soup.select('div[class*="sightItemCard_box"]')

        links: List[str] = []
        for card in cards:
            a_tag = card.find("a", href=True)
            if not a_tag:
                continue
            href = a_tag["href"]
            if f"/sight/{district_id}/" in href and ".html" in href and "s0-p" not in href:
                full = self.base_url + href if href.startswith("/") else href
                links.append(full)
        return list(dict.fromkeys(links))  # 保序去重

    def discover_sights(self) -> List[SightLink]:
        all_links: List[SightLink] = []
        for city, conf in self.city_config.items():
            district_id = str(conf["district_id"])
            logger.info(f"[ctrip] 发现城市 {city} ({district_id})")
            for page in range(1, int(conf["pages"]) + 1):
                try:
                    urls = self._discover_page(district_id, page)
                    for u in urls:
                        try:
                            cls, did, sid = parse_sight_url(u)
                        except ValueError as e:
                            logger.warning(f"[ctrip] 跳过非法 URL {u}: {e}")
                            continue
                        all_links.append(SightLink(city, cls, did, sid, u))
                    logger.info(f"  p{page}: +{len(urls)}")
                except Exception as e:
                    logger.error(f"  p{page} 失败: {e}")
                    with self._fail_lock:
                        self.failed_discoveries.append((city, page))
                time.sleep(random.uniform(*self.page_delay))

        seen, unique = set(), []
        for link in all_links:
            if link.url not in seen:
                seen.add(link.url)
                unique.append(link)
        logger.info(f"[ctrip] 去重后共 {len(unique)} 个景点")
        return unique

    # 阶段二：requests 抓详情
    def fetch_sight_detail(self, link: SightLink) -> Optional[Path]:
        # 断点续爬
        out_path = self.raw_dir / f"{link.cls}.{link.district_id}.{link.sight_id}.html"
        if out_path.exists() and out_path.stat().st_size > 0:
            logger.debug(f"[ctrip] 跳过已存在 {out_path.name}")  # 跳过已经爬过的景点
            return out_path

        try:
            resp = self._request(link.url)
        except Exception as e:
            logger.error(f"[ctrip] 详情请求失败 {link.url}: {e}")
            with self._fail_lock:
                self.failed_details.append(link.url)
            return None

        try:
            base_info, detail, comment = extract_modules(resp.text)
        except ValueError as e:
            logger.error(f"[ctrip] 模块提取失败 {link.url}: {e}")
            with self._fail_lock:
                self.failed_details.append(link.url)
            return None

        if detail is None and comment is None:
            logger.error(f"[ctrip] base_info/detail/comment 均为空 {link.url}")
            with self._fail_lock:
                self.failed_details.append(link.url)
            return None

        html = wrap_modules(base_info, detail, comment, source_url=link.url)
        filename = f"{link.cls}.{link.district_id}.{link.sight_id}.html"
        doc = RawDocument(
            source=self.name,
            url=link.url,
            fetched_at=self._now_iso(),
            content_type="html",
            raw_content=html,
            meta={
                "city": link.city,
                "district_id": link.district_id,
                "sight_id": link.sight_id,
                "comment_page": 1,   # 显式标注：评论只存了第 1 页
            },
        )
        return self._save_raw(doc, filename)

    # 主流程
    def scrape(self) -> Dict[str, List]:
        logger.info("[ctrip] ===== 阶段一：发现景点 URL =====")
        links = self.discover_sights()

        logger.info(f"[ctrip] ===== 阶段二：抓取详情（workers={self.detail_workers}）=====")
        saved: List[Path] = []
        try:
            if self.detail_workers <= 1:
                for i, link in enumerate(links, 1):
                    path = self.fetch_sight_detail(link)
                    if path:
                        saved.append(path)
                    if i % 10 == 0:
                        logger.info(f"  进度 {i}/{len(links)}")
            else:
                with ThreadPoolExecutor(max_workers=self.detail_workers) as pool:
                    futures = {pool.submit(self.fetch_sight_detail, l): l for l in links}
                    for i, fut in enumerate(as_completed(futures), 1):
                        try:
                            path = fut.result()
                        except Exception as e:
                            logger.error(f"[ctrip] worker 异常: {e}")
                            path = None

                        if path:
                            saved.append(path)
                        if i % 10 == 0:
                            logger.info(f"  进度 {i}/{len(links)}")
        finally:
            self.close()

        logger.info(f"[ctrip] 完成：成功 {len(saved)}，"
                    f"发现失败 {len(self.failed_discoveries)}，详情失败 {len(self.failed_details)}")
        return {
            "saved": saved,
            "failed_discoveries": self.failed_discoveries,
            "failed_details": self.failed_details,
        }

if __name__ == "__main__":
    from src.utils.logger import setup_logger
    setup_logger()

    scraper = CtripScraper({
        "rate": 2.0,            # 全局每秒最多 2 个请求
        "capacity": 5.0,        # 允许突发 5 个
        "detail_workers": 3,    # 详情阶段 3 线程
        "page_delay": (1.0, 2.0),
    })
    result = scraper.scrape()
    print(f"成功 {len(result['saved'])} 个")
    if result["failed_details"]:
        print("失败详情：", result["failed_details"])
