"""
在携程旅行中爬取海口市的第一页中所有景点的url
景点的详情页url的位置：
    <div class="cardListBox_box__lMuWz">
        <div class="sightItemCard_box__2FUEj ">
            <a href="https://you.ctrip.com/sight/haikou37/3175.html?poiType=3&amp;scene=online">雷琼海口火山群世界地质公园</a>
"""

import requests
from bs4 import BeautifulSoup

# 设置请求头（User-Agent），避免被拒绝访问
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36 Edg/152.0.0.0"
}


def get_sight_page(page_num, headers = headers):
    # 构造当前页的URL（第1页是 s0-p1.html，第1页有时也可以直接不带参数，这里统一格式）
    url = f"https://you.ctrip.com/sight/haikou37/s0-p{page_num}.html"

    # 请求页面
    response = requests.get(url, headers=headers)
    response.encoding = 'utf-8'  # 设置编码，避免乱码

    # 解析HTML
    soup = BeautifulSoup(response.text, 'html.parser')

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


# 测试：抓取第1页的链接
if __name__ == '__main__':
    all_url_list = get_sight_page(1)
    for link in all_url_list:
        print(link)
