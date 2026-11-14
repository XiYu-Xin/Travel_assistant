"""
在携程旅行中爬取海口市前五页的所有景点的详情页url
fake-useragent:内置了真实的全球浏览器数据库，在需要使用大量 User-Agent的轮换需求下很好用。
selenium:模拟一个真实的浏览器内核去加载页面、执行JavaScript、触发翻页，然后从最终渲染出的 DOM 里提取数据

控制页面页数的标签为：<a href="/sight/haikou37/s0-p1.html"></a> 中的sp-p{number}中
"""
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent
import random

def get_sight_page(page_num, headers):
    driver = webdriver.Chrome()  # 需要有 ChromeDriver
    driver.get(f"https://you.ctrip.com/sight/haikou37/s0-p{page_num}.html")
    # 显式等待，直到景点卡片容器出现（最多等10秒）
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'div[class*="sightItemCard_box"]'))
    )
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    # 2. 找到所有景点卡片容器
    # 每个景点都有着相同的标签类名：<div class="sightItemCard_box__2FUEj ">
    # 类名可能带随机后缀，使用模糊匹配
    cards = soup.select('div[class*="sightItemCard_box"]')

    detail_links = []
    for card in cards:
        # 在每个卡片里找景点详情页的 <a> 标签（标题里的跳转链接）
        # 规律：href 包含 "/sight/haikou37/" 并且后面跟着数字ID
        a_tag = card.find('a', href=True)
        if a_tag:
            href = a_tag['href']
            # 过滤掉分页链接、垃圾广告链接，只保留详情页（特征：含数字ID，比如 /3175.html）
            if '/sight/haikou37/' in href and '.html' in href and 's0-p' not in href:
                # 如果是相对路径，补全域名
                if href.startswith('/'):
                    full_url = 'https://you.ctrip.com' + href
                else:
                    full_url = href
                detail_links.append(full_url)

    # 3. 保序去重
    return list(dict.fromkeys(detail_links))


if __name__ == '__main__':
    all_url_list = []
    ua = UserAgent()

    for page_num in range(1, 6):
        headers = {'User-Agent': ua.random}       # 每页换一个 UA
        urls = get_sight_page(page_num, headers=headers)
        all_url_list.extend(urls)
        print(f"第 {page_num} 页拿到 {len(urls)} 个链接")
        time.sleep(random.uniform(1, 3))     # 每个页面之间的访问相隔1至3秒

    # 保序去重
    seen, unique_urls = set(), []
    for u in all_url_list:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)

    print(f"共 {len(unique_urls)} 个景点")
    for link in unique_urls:
        print(link)