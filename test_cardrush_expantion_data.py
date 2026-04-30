# test_cardrush_card_page.py
import requests
from bs4 import BeautifulSoup

# M2a 확장팩 테스트
url = "https://www.cardrush-pokemon.jp/product-group/509"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7',
}

print("🔍 카드러쉬 카드 목록 페이지 분석 중...\n")

try:
    response = requests.get(url, headers=headers, timeout=30)
    print(f"📡 HTTP 상태: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ 접근 실패")
        exit()
    
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # HTML 저장
    with open('cardrush_cards_sample.html', 'w', encoding='utf-8') as f:
        f.write(soup.prettify())
    
    print("✅ cardrush_cards_sample.html 저장 완료")
    print("\n주요 요소 분석:")
    
    # 1. 상품 아이템 찾기
    print("\n1. 상품 관련 클래스:")
    for keyword in ['item', 'product', 'goods', 'card']:
        elements = soup.find_all(class_=lambda x: x and keyword in x.lower())
        if elements:
            print(f"   '{keyword}' 포함: {len(elements)}개")
            if len(elements) > 0:
                print(f"      첫 번째: {elements[0].get('class')}")
    
    # 2. 가격 관련
    print("\n2. 가격 관련 클래스:")
    for keyword in ['price', 'yen', '円']:
        elements = soup.find_all(class_=lambda x: x and keyword in str(x).lower())
        if elements:
            print(f"   '{keyword}' 포함: {len(elements)}개")
            if len(elements) > 0:
                sample = elements[0].get_text(strip=True)[:50]
                print(f"      샘플: {sample}")
    
    # 3. 이미지
    print("\n3. 상품 이미지:")
    images = soup.find_all('img', alt=True)[:10]
    for idx, img in enumerate(images, 1):
        alt = img.get('alt', '')
        src = img.get('src', '')
        if alt and 'pokemon' in src.lower():
            print(f"   [{idx}] {alt[:50]}")
            print(f"        {src[:80]}")
    
    # 4. 링크 구조
    print("\n4. 상품 상세 링크:")
    links = soup.find_all('a', href=True)
    product_links = [a for a in links if 'product' in a.get('href', '')][:10]
    for idx, link in enumerate(product_links, 1):
        href = link.get('href')
        text = link.get_text(strip=True)[:30]
        print(f"   [{idx}] {href}")
        if text:
            print(f"        {text}")

except Exception as e:
    print(f"❌ 오류: {e}")
    import traceback
    traceback.print_exc()