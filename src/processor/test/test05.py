"""
数据获取：
在景点的详情页中获取景点的介绍，以及点评等信息
景点：雷琼海口火山群世界地质公园
url:https://you.ctrip.com/sight/haikou37/3175.html?poiType=3&scene=online
"""

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

if __name__ == '__main__':
    base_url = "https://you.ctrip.com/sight/haikou37/3175.html?poiType=3&scene=online"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36 Edg/152.0.0.0"
    }

    page = requests.get(base_url, headers=headers)
    page.encoding = 'utf-8'

    soup = BeautifulSoup(page.content, 'html.parser')

    # 1.获取景点介绍等信息
    """
    HTML结构：
    div.detailModuleRef
    └─ div.detailModule normalModule
        ├─ div.moduleTitle      <- 这个标签下是标题
        ├─ div.moduleContent    <- 这个标签下是内容
        ├─ div.moduleTitle      <- 下一个标题
        └─ div.moduleContent    <- 下一个内容
    ├─ div.askModuleRef
    └─ div.commentModuleRef
    """
    # find方法（只取第一个）
    ref_div = soup.find('div', class_='detailModuleRef')
    print("我是find：")
    if ref_div:
        print(ref_div.get_text(strip=True))

    # select方法（CSS选择器）
    print("我是Select：")
    ref_divs = soup.select('div.detailModuleRef')
    for d in ref_divs:
        print(d.get_text(strip=True))

    # 2.获取相关的点评
    """
    HTML结构：
    div.commentItem
    ├─ div.userInfo
    └─ div.contentInfo
        ├─ div.scroreInfo
        ├─ div.commentDetail    <- 这个标签下是评论
        ├─ div.commentImgList
        └─ div.commentFooter
    """
    comments = soup.find_all('div', class_='commentItem')

    for i, item in enumerate(comments, 1):
        detail_div = item.select_one('.contentInfo .commentDetail')
        if detail_div is None:
            continue
        content = detail_div.get_text(separator='\n', strip=True)
        print(f'第{i}条点评：')
        print(content)
