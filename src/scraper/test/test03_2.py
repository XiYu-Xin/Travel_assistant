"""
在携程旅行中，爬取海南省多个城市前几页的旅游景点详情页的 url
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import random

# 城市配置：城市名 -> {district_id, pages}
CITY_CONFIG = {
    "海口": {"district_id": "haikou37",      "pages": 4},
    "三亚": {"district_id": "sanya61",       "pages": 5},
    "陵水": {"district_id": "lingshui1509",  "pages": 3},
    "万宁": {"district_id": "wanning846",    "pages": 2},
    "琼海": {"district_id": "qionghai843",   "pages": 2},
    "文昌": {"district_id": "wenchang1007",  "pages": 2},
}


def get_sight_page(driver, page_num, district_id):
    """用已启动的 driver 打开某页，返回该页景点详情链接列表"""
    driver.get(f"https://you.ctrip.com/sight/{district_id}/s0-p{page_num}.html")

    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'div[class*="sightItemCard_box"]'))
    )
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    cards = soup.select('div[class*="sightItemCard_box"]')

    detail_links = []
    for card in cards:
        a_tag = card.find('a', href=True)
        if not a_tag:
            continue
        href = a_tag['href']
        if f'/sight/{district_id}/' in href and '.html' in href and 's0-p' not in href:
            full_url = 'https://you.ctrip.com' + href if href.startswith('/') else href
            detail_links.append(full_url)

    return list(dict.fromkeys(detail_links))


def create_driver():
    """
        创建并返回一个配置好的 Chrome WebDriver（真实浏览器实例）。

        虽然切换页面的标签为<a href="/sight/haikou37/s0-p1.html"></a> 中的sp-p{number}
        但是直接使用request却没法拿到除了第一页以外的原始的HTML

        与 requests 只拿到原始 HTML 不同，Selenium 驱动的是真实浏览器：
        调用 driver.get(url) 时，浏览器会自动执行页面中的 JavaScript，
        因此之后读到的 page_source / DOM 是 JS 渲染后的结果，
        用于抓取动态渲染的页面。

        :return:webdriver.Chrome 实例
    """

    options = webdriver.ChromeOptions()
    options.add_argument('--disable-gpu')
    options.add_argument('--blink-settings=imagesEnabled=false')  # 不加载图片，提速
    # 如确实需要轮换 UA，可在这里配置：
    # options.add_argument(f'--user-agent={ua.random}')
    return webdriver.Chrome(options=options)


if __name__ == '__main__':
    all_urls = []
    failed = []  # 记录 (城市, 页码) 失败任务

    driver = create_driver()
    try:
        for city, conf in CITY_CONFIG.items():
            print(f"\n正在爬取城市：{city}")
            district_id = conf["district_id"]
            for page_num in range(1, conf["pages"] + 1):
                try:
                    urls = get_sight_page(driver, page_num, district_id)
                    all_urls.extend(urls)
                    print(f"\t第 {page_num} 页拿到 {len(urls)} 个链接")
                except Exception as e:
                    print(f"\t第 {page_num} 页失败：{e}")
                    failed.append((city, page_num))

                time.sleep(random.uniform(1, 3))  # 页面之间随机停顿
    finally:
        driver.quit()

    # 保序去重
    seen, unique_urls = set(), []
    for u in all_urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)

    print(f"\n共 {len(unique_urls)} 个景点")
    for link in unique_urls:
        print(link)

    if failed:
        print(f"\n失败任务：{failed}")