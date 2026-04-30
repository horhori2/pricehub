# test_cardrush_crawl.py
import requests
from bs4 import BeautifulSoup
import re
import time

# 카드러쉬 확장팩 매핑 (테스트용 - 몇 개만)
TEST_EXPANSIONS = {
    'M1L': {'name': 'メガシンフォニア', 'url': 'https://www.cardrush-pokemon.jp/product-group/488'},
    'SV11B': {'name': 'ブラックボルト', 'url': 'https://www.cardrush-pokemon.jp/product-group/476'},
    'SV2a': {'name': 'ポケモンカード151', 'url': 'https://www.cardrush-pokemon.jp/product-group/284'},
}

def extract_card_info(card_name_text):
    """
    카드명에서 정보 추출
    예: ☆SALE☆ハリテヤマ【R】{025/063} → (ハリテヤマ, R, 025/063)
    """
    # SALE 제거
    card_name_text = card_name_text.replace('☆SALE☆', '').strip()
    
    # 레어도 추출 【R】, 【RR】, 【SR】 등
    rarity_match = re.search(r'【(.+?)】', card_name_text)
    rarity = rarity_match.group(1) if rarity_match else None
    
    # 카드번호 추출 {025/063}
    card_number_match = re.search(r'\{(.+?)\}', card_name_text)
    card_number = card_number_match.group(1) if card_number_match else None
    
    # 카드명 추출 (레어도와 카드번호 제거)
    card_name = re.sub(r'【.+?】', '', card_name_text)
    card_name = re.sub(r'\{.+?\}', '', card_name).strip()
    
    return card_name, rarity, card_number


def parse_price(price_text):
    """가격 텍스트에서 숫자만 추출 (220円 → 220)"""
    price_match = re.search(r'(\d+)', price_text.replace(',', ''))
    return int(price_match.group(1)) if price_match else None


def test_crawl_page(url, expansion_code):
    """카드러쉬 페이지 크롤링 테스트"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ja-JP,ja;q=0.9',
    }
    
    try:
        print(f"  🔍 요청 중...")
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        
        print(f"  📡 HTTP {response.status_code}")
        
        if response.status_code != 200:
            print(f"  ❌ 요청 실패")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 카드 아이템 찾기
        card_items = soup.find_all('li', class_='list_item_cell')
        
        print(f"  📦 {len(card_items)}개 카드 아이템 발견")
        
        if not card_items:
            print(f"  ⚠️  카드를 찾을 수 없습니다")
            # HTML 구조 확인
            print(f"\n  🔍 HTML 일부 확인:")
            print(response.text[:500])
            return []
        
        cards = []
        
        # 처음 5개만 상세 출력
        for i, item in enumerate(card_items[:5]):
            print(f"\n  --- 카드 #{i+1} ---")
            
            try:
                # 카드명 추출
                goods_name = item.find('span', class_='goods_name')
                if goods_name:
                    card_name_full = goods_name.get_text(strip=True)
                    print(f"  📝 원본 카드명: {card_name_full}")
                    
                    card_name, rarity, card_number = extract_card_info(card_name_full)
                    print(f"  🎴 파싱 결과:")
                    print(f"     - 카드명: {card_name}")
                    print(f"     - 레어도: {rarity}")
                    print(f"     - 카드번호: {card_number}")
                else:
                    print(f"  ❌ goods_name을 찾을 수 없음")
                    continue
                
                # 확장팩 코드 확인
                model_number = item.find('span', class_='model_number_value')
                if model_number:
                    page_expansion_code = model_number.get_text(strip=True)
                    print(f"  📁 확장팩 코드: {page_expansion_code}")
                else:
                    page_expansion_code = expansion_code
                    print(f"  📁 확장팩 코드 (기본값): {page_expansion_code}")
                
                # 가격 추출
                price_elem = item.find('span', class_='figure')
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    price = parse_price(price_text)
                    print(f"  💰 가격: {price_text} → {price}원")
                else:
                    print(f"  ❌ 가격을 찾을 수 없음")
                    price = None
                
                # 재고 추출
                stock_elem = item.find('p', class_='stock')
                if stock_elem:
                    stock_text = stock_elem.get_text(strip=True)
                    stock_match = re.search(r'(\d+)', stock_text.replace(',', ''))
                    stock = int(stock_match.group(1)) if stock_match else 0
                    print(f"  📊 재고: {stock_text} → {stock}개")
                else:
                    stock = 0
                    print(f"  📊 재고: 정보 없음")
                
                # shop_product_code 생성
                if card_number:
                    shop_product_code = f"{page_expansion_code}-{card_number}"
                else:
                    shop_product_code = f"{page_expansion_code}-{card_name}"
                print(f"  🔑 shop_product_code: {shop_product_code}")
                
                if price:
                    cards.append({
                        'expansion_code': page_expansion_code,
                        'card_name': card_name,
                        'rarity': rarity,
                        'card_number': card_number,
                        'price': price,
                        'stock': stock,
                        'shop_product_code': shop_product_code
                    })
                
            except Exception as e:
                print(f"  ⚠️  카드 파싱 오류: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # 전체 통계
        total_cards = len(card_items)
        valid_cards = len([item for item in card_items if item.find('span', class_='goods_name') and item.find('span', class_='figure')])
        
        print(f"\n  📊 통계:")
        print(f"     - 전체 아이템: {total_cards}개")
        print(f"     - 유효한 카드: {valid_cards}개")
        print(f"     - 파싱 성공: {len(cards)}개 (처음 5개만 파싱)")
        
        return cards
        
    except Exception as e:
        print(f"  ❌ 크롤링 오류: {e}")
        import traceback
        traceback.print_exc()
        return []


def main():
    print("=" * 80)
    print("카드러쉬 크롤링 테스트")
    print("=" * 80)
    print("⚠️  DB 저장 없이 크롤링만 테스트합니다")
    print("=" * 80)
    
    all_cards = []
    
    for expansion_code, info in TEST_EXPANSIONS.items():
        print(f"\n{'='*80}")
        print(f"📁 {expansion_code} - {info['name']}")
        print(f"🔗 {info['url']}")
        print(f"{'='*80}")
        
        cards = test_crawl_page(info['url'], expansion_code)
        
        if cards:
            all_cards.extend(cards)
            print(f"\n  ✅ 성공적으로 {len(cards)}개 카드 파싱")
        else:
            print(f"\n  ❌ 카드 파싱 실패")
        
        # 다음 확장팩 전 대기
        print(f"\n  ⏳ 2초 대기...")
        time.sleep(2)
    
    # 최종 결과
    print("\n" + "=" * 80)
    print("테스트 완료")
    print("=" * 80)
    print(f"총 수집된 카드: {len(all_cards)}개")
    
    if all_cards:
        print(f"\n샘플 데이터 (처음 3개):")
        for i, card in enumerate(all_cards[:3], 1):
            print(f"\n  카드 #{i}:")
            print(f"    - 확장팩: {card['expansion_code']}")
            print(f"    - 카드명: {card['card_name']}")
            print(f"    - 레어도: {card['rarity']}")
            print(f"    - 카드번호: {card['card_number']}")
            print(f"    - 가격: {card['price']}원")
            print(f"    - 재고: {card['stock']}개")
            print(f"    - shop_product_code: {card['shop_product_code']}")
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()