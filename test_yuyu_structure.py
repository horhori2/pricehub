# test_yuyu_structure.py
import requests
from bs4 import BeautifulSoup

url = "https://yuyu-tei.jp/sell/poc/s/m03"
headers = {'User-Agent': 'Mozilla/5.0'}

response = requests.get(url, headers=headers, timeout=30)
response.encoding = 'utf-8'
soup = BeautifulSoup(response.text, 'html.parser')

print("=== 확장팩명 관련 요소 찾기 ===\n")

# 1. line1 클래스 찾기
line1 = soup.select('.line1')
print(f"line1 클래스: {len(line1)}개")
if line1:
    print(f"  내용: {line1[0].get_text(strip=True)}")
    print()

# 2. 모든 h1, h2, h3 태그 찾기
for tag in ['h1', 'h2', 'h3', 'h4']:
    elements = soup.find_all(tag)
    print(f"{tag} 태그: {len(elements)}개")
    for elem in elements[:3]:  # 처음 3개만
        print(f"  - {elem.get_text(strip=True)}")
    print()

# 3. title 태그
title = soup.find('title')
if title:
    print(f"title: {title.get_text(strip=True)}\n")

# 4. breadcrumb (빵 부스러기) 찾기
breadcrumb = soup.select('.breadcrumb')
if breadcrumb:
    print("breadcrumb 발견:")
    print(f"  {breadcrumb[0].get_text(strip=True)}\n")

# 5. 페이지 타이틀 관련 클래스 찾기
possible_title_classes = [
    '.page-title',
    '.title',
    '.heading',
    '.series-name',
    '.product-name',
    '.category-name',
]

for cls in possible_title_classes:
    elements = soup.select(cls)
    if elements:
        print(f"{cls}: {len(elements)}개")
        for elem in elements[:2]:
            print(f"  - {elem.get_text(strip=True)}")
        print()

# 6. HTML 샘플 (처음 3000자)
print("\n=== HTML 샘플 ===")
print(soup.prettify()[:3000])