"""
将景点详细页的原始HTML保存下来，为后续的数据解析做准备
部分景点详情页的url如下：
雷琼海口火山群世界地质公园：https://you.ctrip.com/sight/haikou37/3175.html?poiType=3&scene=online
海南热带野生动植物园：https://you.ctrip.com/sight/haikou37/3180.html?poiType=3&scene=online
可以观察到url的形式为：https://you.ctrip.com/{class}/{districtId}/{sightID}.html?poiType=3&scene=online
故：
1、将原始HTML保存到/data/raw中，命名为Class.districtId.sightId.html的形式。
2、只保存包含主要信息的HTML文本，包括细节模块标签（div.class=detailModuleRef）和社区评论标签（div.class=commentModuleRef)。
3、将爬取到的HTML文本保存在项目目录中的“/data/raw”下。
"""

"""
HTML结构：
    div.mainModule
    ├─ div.detailModuleRef      <-景点详细介绍模块
    ├─ div.askModuleRef
    └─ div.commentModuleRef     <-游客游玩点评模块
"""

import requests
from bs4 import BeautifulSoup
import os
import re
import time
import random
from urllib.parse import urlparse

# 路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # program/src/scraper/test
PROGRAM_DIR = os.path.dirname(os.path.dirname(os.path.dirname(BASE_DIR)))   # 回溯3级 -> program
RAW_DIR = os.path.join(PROGRAM_DIR, "data", "raw")  # program/data/raw
os.makedirs(RAW_DIR, exist_ok=True)
print(f"[INFO] RAW_DIR = {RAW_DIR}")

# 设置请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36 Edg/157.0.0.0",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# 测试用的url
BASE_URL = "https://you.ctrip.com/sight/haikou37/3175.html?poiType=3&scene=online"


# 从url中获取命名所需的Class,districtId和sightId
def parse_sight_url(url: str):
    """
    从url中解析出Class,districtId和sightId
    :param url: https://you.ctrip.com/sight/haikou37/3175.html?poiType=3
    :return:(sight,haikou37,3175)
    """
    path = urlparse(url).path  # /sight/haikou37/3175.html
    m = re.match(r"^/([^/]+)/([^/]+)/(\d+)\.html$", path)   # [sight, haikou37, 3175]
    if not m:
        raise ValueError(f"URL结构不符合预期：{url}")
    return m.group(1), m.group(2), m.group(3)


# 在HTML中提取目标模块
def extract_modules(html: str):
    """
    :return:detail, comment
    """
    soup = BeautifulSoup(html, "html.parser")

    main = soup.select_one('div[class*="mainModule"]')
    if main is None:
        raise ValueError("HTML中没找到 mainModule，可能被风控或结构不符合预期")

    detail = main.select_one('div[class*="detailModuleRef"]')
    comment = main.select_one('div[class*="commentModuleRef"]')
    return detail, comment

def save_modules(detail, comment, save_path: str):
    """
    将提取到的目标模块包装进一个最小可用的HTML骨架后写出
    """
    chunks = [
        "<!DOCTYPE html>",
        '<html><head><meta charset="utf-8"></head><body>',
        '<div class="mainModule">',
    ]

    if detail is not None:
        chunks.append(str(detail))
    if comment is not None:
        chunks.append(str(comment))
    chunks.append("</div></body></html>")

    with open(save_path, "w", encoding="utf-8") as f:
        f.write("\n".join(chunks))

# 主程序
def crawl_one(session: requests.Session, url: str):
    cls, district_id, sight_id = parse_sight_url(url)
    out_path = os.path.join(RAW_DIR, f"{cls}.{district_id}.{sight_id}.html")

    resp = session.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    resp.encoding = "utf-8"          # 防止乱码

    detail, comment = extract_modules(resp.text)
    if detail is None and comment is None:
        raise ValueError("两个模块都没抓到，可能页面是异步渲染的")

    save_modules(detail, comment, out_path)

    return (
        out_path,
        detail is not None,
        comment is not None,
        len(resp.text),
    )

if __name__ == "__main__":
    session = requests.Session()

    try:
        path, ok_d, ok_c, size = crawl_one(session, BASE_URL)
        print(f"[OK] {path}  detail={ok_d} comment={ok_c} (Original_HTML {size} bits)")
    except Exception as e:
        print(f"[FAIL] {BASE_URL} -> {e}")
