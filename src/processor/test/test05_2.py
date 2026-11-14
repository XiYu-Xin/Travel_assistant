"""
将HTML文本解析成结构化JSON数据
"""

import json
import requests
from bs4 import BeautifulSoup, Comment
from fake_useragent import UserAgent


def extract_row(row):
    # 解析一个 moduleContentRow：<b>小标题</b>：内容...
    b = row.find('b')
    if not b:
        return None, row.get_text(separator='\n', strip=True)

    sub_title = b.get_text(strip=True)

    parts = []
    for sib in b.next_siblings:          # 包含 NavigableString、Comment、Tag
        if isinstance(sib, Comment):     # 跳过 <!-- -->
            continue
        if hasattr(sib, 'get_text'):
            parts.append(sib.get_text(separator='\n', strip=True))
        else:
            parts.append(str(sib).strip())

    content = '\n'.join(p for p in parts if p).strip()
    content = content.lstrip('：:').strip()   # 去掉紧跟的冒号
    return sub_title, content


def parse_detail_modules(ref_div):
    """把 detailModuleRef 中的 moduleTitle / moduleContent 配对成 dict
    特殊处理：
      - moduleContent 下有 moduleContentRow 时，拆成嵌套 dict（服务设施）
      - moduleContent 带额外 class（如 modulePhone）时，仍按 moduleContent 处理
    """
    data = {}

    modules = ref_div.select('div.detailModule') or [ref_div]

    def is_title_or_content(tag):
        if tag.name != 'div':
            return False
        cls = set(tag.get('class') or [])
        # 注意：用“包含”判断，兼容 moduleContent modulePhone 这种多 class
        return bool(cls & {'moduleTitle', 'moduleContent'})

    for module in modules:
        children = module.find_all(recursive=False)
        nodes = [c for c in children if is_title_or_content(c)]
        if not nodes:
            nodes = module.find_all(is_title_or_content)

        current_title = None
        for node in nodes:
            cls = set(node.get('class') or [])

            if 'moduleTitle' in cls:
                current_title = node.get_text(strip=True)

            elif 'moduleContent' in cls:      # moduleContent modulePhone 也会进这里
                if not current_title:
                    continue

                # 服务设施：内部有多个 moduleContentRow，拆成子 dict
                rows = node.find_all('div', class_='moduleContentRow')
                if rows:
                    sub_data = {}
                    for row in rows:
                        sub_title, sub_content = extract_row(row)
                        if not sub_title:
                            continue
                        # 子标题去重
                        k, i = sub_title, 2
                        while k in sub_data:
                            k = f'{sub_title}_{i}'
                            i += 1
                        sub_data[k] = sub_content
                    value = sub_data
                else:
                    # 普通 moduleContent（含官方电话 modulePhone）
                    value = node.get_text(separator='\n', strip=True)

                # 顶层 key 去重
                key, i = current_title, 2
                while key in data:
                    key = f'{current_title}_{i}'
                    i += 1
                data[key] = value
                current_title = None

    return data


if __name__ == '__main__':
    base_url = "https://you.ctrip.com/sight/haikou37/3175.html?poiType=3&scene=online"
    headers = {'User-Agent': UserAgent().random}

    page = requests.get(base_url, headers=headers)
    page.encoding = page.apparent_encoding
    soup = BeautifulSoup(page.text, 'html.parser')

    ref_div = soup.select_one('div.detailModuleRef')
    detail_info = parse_detail_modules(ref_div) if ref_div else {}

    print(json.dumps(detail_info, ensure_ascii=False, indent=2))

    comments = soup.find_all('div', class_='commentItem')
    comments_data = []
    for i, item in enumerate(comments, 1):
        detail_div = item.select_one('.contentInfo .commentDetail')
        if detail_div is None:
            continue
        comments_data.append({
            'index': i,
            'content': detail_div.get_text(separator='\n', strip=True),
        })

    print(json.dumps(comments_data, ensure_ascii=False, indent=2))