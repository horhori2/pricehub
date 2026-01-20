"""
포켓몬카드 단일 검색 디버깅 도구
API 응답과 필터링 과정을 상세히 출력합니다.
"""

import os
import django
import urllib.request
import urllib.parse
import json
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from pricehub.models import Card

# 네이버 API 정보
NAVER_CLIENT_ID = "S_iul25XJKSybg_fiSAc"
NAVER_CLIENT_SECRET = "_73PsEM4om"


def search_naver_api(search_query):
    """네이버 쇼핑 API 검색"""
    try:
        enc_text = urllib.parse.quote(search_query)
        url = f"https://openapi.naver.com/v1/search/shop?query={enc_text}&sort=sim&exclude=used:rental:cbshop&display=20"
        
        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id", NAVER_CLIENT_ID)
        request.add_header("X-Naver-Client-Secret", NAVER_CLIENT_SECRET)
        
        response = urllib.request.urlopen(request)
        if response.getcode() == 200:
            result = json.loads(response.read())
            return result.get('items', [])
        return []
    except Exception as e:
        print(f"❌ API 예외: {e}")
        return []


def extract_pokemon_info(product_name):
    """포켓몬카드 정보 추출"""
    if not product_name.startswith("포켓몬"):
        return None, None, None
    
    promo_match = re.search(r'P-\d{3}', product_name)
    if promo_match:
        return f"포켓몬 {promo_match.group()}", None, None
    
    words = product_name.split()
    search_text = " ".join(words[:-1]) if len(words) > 1 else product_name
    
    # 레어도 패턴 (긴 것부터 매칭)
    rarity_pattern = r'\b(로켓단 미러|타입 미러|볼 미러|마스터볼|몬스터볼|UR|SSR|SR|RR|RRR|CHR|CSR|BWR|AR|SAR|HR|MA|R|U|C|이로치|미러)\b'
    rarity_match = re.search(rarity_pattern, search_text)
    rarity = rarity_match.group(1) if rarity_match else None
    
    temp_name = search_text
    if rarity:
        rarity_index = temp_name.find(rarity)
        if rarity_index != -1:
            temp_name = temp_name[:rarity_index].strip()
    
    patterns = {
        'ace': r'\b[가-힣A-Za-z\s]+(?:ACE|Ace|ace)\b',
        'vmax': r'\b[가-힣A-Za-z\s]+(?:VMAX|Vmax|vmax)\b',
        'vstar': r'\b[가-힣A-Za-z\s]+(?:VStar|vstar|VSTAR)\b',
        'ex': r'\b[가-힣A-Za-z\s]+ex\b',
        'v': r'\b[가-힣A-Za-z\s]+V\b(?!\s*(?:MAX|max|Star|star))'
    }
    
    detected_patterns = {name: bool(re.search(pattern, temp_name, re.IGNORECASE)) 
                        for name, pattern in patterns.items()}
    
    pokemon_name = None
    extraction_rules = [
        ('ace', r'포켓몬카드\s+(.+?)\s*(?:ACE|Ace|ace)'),
        ('vmax', r'포켓몬카드\s+(.+?)\s*(?:VMAX|Vmax|vmax)'),
        ('vstar', r'포켓몬카드\s+(.+?)\s*(?:VStar|vstar|VSTAR)'),
        ('ex', r'포켓몬카드\s+(.+?ex)'),
        ('v', r'포켓몬카드\s+(.+?)\s*V\b(?!\s*(?:MAX|max|Star|star))'),
        (None, r'포켓몬카드\s+(.+)')
    ]
    
    for pattern_name, regex in extraction_rules:
        if pattern_name is None or detected_patterns.get(pattern_name, False):
            name_match = re.search(regex, temp_name, re.IGNORECASE)
            if name_match:
                pokemon_name = name_match.group(1).strip()
                break
    
    return product_name, rarity, pokemon_name


def check_item_filters(title, mall_name, required_rarity, required_pokemon_name):
    """포켓몬카드 필터링 체크"""
    
    # 제외 판매처
    if mall_name in ["화성스토어-TCG-", "네이버", "쿠팡"]:
        return False, f"제외: 판매처 {mall_name}"
    
    # 일본판 제외
    if any(keyword in title for keyword in ['일본', '일본판', 'JP', 'JPN', '일판']):
        return False, "제외: 일본판"
    
    # 포켓몬 이름 매칭
    if required_pokemon_name:
        clean_title = re.sub(r'<[^>]+>', '', title)
        
        # 띄어쓰기 제거 매칭
        required_name_no_space = re.sub(r'\s+', '', required_pokemon_name)
        title_no_space = re.sub(r'\s+', '', clean_title)
        
        if required_name_no_space.lower() in title_no_space.lower():
            pass  # 매칭 성공
        else:
            # 개별 단어 매칭
            required_words = [word for word in required_pokemon_name.split() 
                            if word.lower() not in ['ex', 'v', 'vmax', 'vstar', 'ace']]
            
            word_matches = sum(1 for word in required_words if word.lower() in clean_title.lower())
            
            if word_matches != len(required_words) or len(required_words) == 0:
                return False, f"제외: 포켓몬명 불일치 (매칭: {word_matches}/{len(required_words)})"
    
    # 레어도 매칭
    if required_rarity:
        clean_title = re.sub(r'<[^>]+>', '', title)
        
        if required_rarity not in clean_title:
            return False, f"제외: 레어도 '{required_rarity}' 미포함"
    
    return True, "✅ 통과"


def test_single_search(search_query):
    """단일 검색어 테스트"""
    
    print("\n" + "=" * 80)
    print(f"🔍 검색어: {search_query}")
    print("=" * 80)
    
    # 1. 정보 추출
    product_name, rarity, pokemon_name = extract_pokemon_info(search_query)
    
    print(f"\n📊 추출된 정보:")
    print(f"  - 전체 검색어: {product_name}")
    print(f"  - 레어도: {rarity or '없음'}")
    print(f"  - 포켓몬명: {pokemon_name or '없음'}")
    
    # 2. API 검색
    print(f"\n🌐 네이버 쇼핑 API 호출...")
    items = search_naver_api(search_query)
    
    print(f"  ✅ 검색 결과: {len(items)}개\n")
    
    if not items:
        print("❌ 검색 결과가 없습니다.")
        return
    
    # 3. 각 상품 상세 출력
    print("=" * 80)
    print("📦 검색된 상품 목록 (상위 20개)")
    print("=" * 80)
    
    valid_count = 0
    min_price = None
    min_price_item = None
    
    for idx, item in enumerate(items, 1):
        title = item['title']
        clean_title = re.sub(r'<[^>]+>', '', title)
        price = float(item['lprice'])
        mall_name = item.get('mallName', '알 수 없음')
        
        print(f"\n[{idx}] {clean_title}")
        print(f"    가격: {int(price):,}원")
        print(f"    판매처: {mall_name}")
        
        # 필터링 체크
        passed, reason = check_item_filters(title, mall_name, rarity, pokemon_name)
        
        if passed:
            print(f"    상태: {reason}")
            valid_count += 1
            if min_price is None or price < min_price:
                min_price = price
                min_price_item = clean_title
        else:
            print(f"    상태: ❌ {reason}")
    
    # 4. 결과 요약
    print("\n" + "=" * 80)
    print("📊 검색 결과 요약")
    print("=" * 80)
    print(f"총 검색 결과: {len(items)}개")
    print(f"필터 통과: {valid_count}개")
    
    if min_price is not None:
        print(f"\n💰 최저가 정보:")
        print(f"  가격: {int(min_price):,}원")
        print(f"  상품: {min_price_item}")
    else:
        print(f"\n❌ 필터를 통과한 상품이 없습니다.")
        print(f"\n🔍 필터링 조건:")
        print(f"  - 레어도: {rarity or '필터 없음'}")
        print(f"  - 포켓몬명: {pokemon_name or '필터 없음'}")
        print(f"\n💡 문제 해결 방법:")
        print(f"  1. 검색어에 레어도가 정확한지 확인")
        print(f"  2. 검색어에 포켓몬 이름이 정확한지 확인")
        print(f"  3. 확장팩명이 맞는지 확인")


def test_card_by_id(card_id):
    """카드 ID로 테스트"""
    try:
        card = Card.objects.select_related('expansion').get(id=card_id)
        
        print("\n" + "=" * 80)
        print(f"🎴 카드 정보 (ID: {card_id})")
        print("=" * 80)
        print(f"카드명: {card.name}")
        print(f"레어도: {card.rarity}")
        print(f"확장팩: {card.expansion.name}")
        print(f"카드번호: {card.card_number}")
        
        # 검색어 생성
        search_query = f"포켓몬카드 {card.name}"
        
        # 레어도가 검색 제외 목록에 없으면 추가
        excluded_rarities = ['RR', 'RRR', 'R', 'U', 'C']
        if card.rarity and card.rarity not in excluded_rarities:
            search_query += f" {card.rarity}"
        
        search_query += f" {card.expansion.name}"
        
        test_single_search(search_query)
        
    except Card.DoesNotExist:
        print(f"❌ ID {card_id}인 카드를 찾을 수 없습니다")


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("🧪 포켓몬카드 검색 디버깅 도구")
    print("=" * 80)
    print("\n선택하세요:")
    print("  1. 직접 검색어 입력")
    print("  2. 카드 ID로 검색")
    print("  3. 종료")
    
    choice = input("\n선택 (1/2/3): ").strip()
    
    if choice == '1':
        search_query = input("\n검색어를 입력하세요: ").strip()
        if search_query:
            test_single_search(search_query)
        else:
            print("❌ 검색어를 입력해주세요.")
    
    elif choice == '2':
        try:
            card_id = int(input("\n카드 ID를 입력하세요: ").strip())
            test_card_by_id(card_id)
        except ValueError:
            print("❌ 올바른 카드 ID를 입력해주세요.")
    
    elif choice == '3':
        print("종료합니다.")
    
    else:
        print("❌ 잘못된 선택입니다.")