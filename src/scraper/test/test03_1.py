"""
在携程旅行中，爬取海南省多个城市前几页的旅游景点详情页的url
根据城市的热门程度不同，爬取不同景点数量：热门旅游城市三亚、海口爬取4、5页（40+个景点），冷门旅游城市爬取2、3页（20+景点）
携程中介绍海口景点的url：https://you.ctrip.com/sight/haikou37.html
     介绍三亚景点的url：https://you.ctrip.com/sight/sanya61.html
共同点：https://you.ctrip.com/sight/{cityId}}.html
"""

from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import random
citys = ["海口", "三亚", "陵水", "万宁", "琼海", "文昌"]

districtIds = {"海口": "haikou37", "三亚": "sanya61", "陵水": "lingshui1509", "万宁": "wanning846",
              "琼海": "qionghai843", "文昌": "wenchang1007"}

pageNum = {"海口": 4, "三亚": 5, "陵水": 3, "万宁": 2, "琼海": 2, "文昌": 2}

def get_sight_page(page_num, district_id):
    driver = webdriver.Chrome()
    driver.get(f"https://you.ctrip.com/sight/{district_id}/s0-p{page_num}.html")

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'div[class*="sightItemCard_box"]'))
    )
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    cards = soup.select('div[class*="sightItemCard_box"]')

    detail_links = []
    for card in cards:
        a_tag = card.find('a', href=True)
        if a_tag:
            href = a_tag['href']
            # 过滤掉分页链接、垃圾广告链接，只保留详情页（特征：含数字ID，比如 /3175.html）
            if f'/sight/{district_id}/' in href and '.html' in href and 's0-p' not in href:
                # 相对路径，补全域名
                if href.startswith('/'):
                    full_url = 'https://you.ctrip.com' + href
                else:
                    full_url = href
                detail_links.append(full_url)

    # 保序去重
    return list(dict.fromkeys(detail_links))


if __name__ == '__main__':
    url_list = []
    ua = UserAgent()

    for city in citys:
        print(f"正在爬取城市：{city}")
        for page_num in range(1, pageNum[city]+1):
            headers = {'User-Agent': ua.random}
            urls = get_sight_page(page_num, districtIds[city])
            url_list.extend(urls)
            print(f"\t第 {page_num} 页拿到 {len(urls)} 个链接")

    seen, unique_urls = set(), []
    for u in url_list:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)

    print(f"共 {len(unique_urls)} 个景点")
    for link in unique_urls:
        print(link)
