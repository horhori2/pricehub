# pricehub/utils.py
import re
import urllib.request
import urllib.parse
import json
from typing import Optional, Tuple, List

# 네이버 API 정보
NAVER_CLIENT_ID = "S_iul25XJKSybg_fiSAc"
NAVER_CLIENT_SECRET = "_73PsEM4om"

# 검색어에서 제외할 레어도 (일반 레어도)
EXCLUDED_RARITIES = ['RR', 'RRR', 'R', 'U', 'C']

# 모든 특수 레어도 목록 (필터링용)
SPECIAL_RARITIES = ['UR', 'MUR', 'SSR', 'SR', 'CHR', 'CSR', 'BWR', 'AR', 'SAR', 'HR', 'MA', '몬스터볼', '마스터볼', '볼 미러', '타입 미러', '로켓단 미러', '이로치', '미러']


# ==================== 공통 ====================

def search_naver_shopping(search_query: str) -> List[dict]:
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
        else:
            print(f"❌ API 요청 실패: {response.getcode()}")
            return []
    except Exception as e:
        print(f"❌ 예외 발생: {e}")
        return []


# ==================== 포켓몬 한글판 ====================

def generate_pokemon_search_query(card_name: str, rarity: str, expansion_name: str) -> str:
    """포켓몬카드 검색어 생성"""
    search_query = f"포켓몬카드 {card_name}"
    if rarity and rarity not in EXCLUDED_RARITIES:
        search_query += f" {rarity}"
    if expansion_name:
        search_query += f" {expansion_name}"
    return search_query.strip()


def filter_pokemon_items(items: List[dict], card_name: str, rarity: Optional[str]) -> Tuple[Optional[float], int, Optional[str], List[dict]]:
    """포켓몬카드 검색 결과 필터링"""
    min_price = None
    valid_count = 0
    min_price_mall = None
    valid_items = []

    excluded_malls = ["화성스토어-TCG-", "카드 베이스", "네이버", "쿠팡"]
    excluded_keywords = ['일본', '일본판', 'JP', 'JPN', '일판']

    print(f"\n📋 필터링 상세 로그 (총 {len(items)}개):")

    for idx, item in enumerate(items, 1):
        title = item['title']
        price = float(item['lprice'])
        mall_name = item.get('mallName', '알 수 없음')

        print(f"\n[{idx}] 가격: {int(price)}원 / 판매처: {mall_name}")

        clean_title = re.sub(r'<[^>]+>', '', title)
        print(f"    제목: {clean_title}")

        if mall_name in excluded_malls:
            print(f"    ❌ 제외 판매처")
            continue

        if any(keyword in title for keyword in excluded_keywords):
            print(f"    ❌ 일본판 키워드 포함")
            continue

        card_name_no_space = re.sub(r'\s+', '', card_name)
        title_no_space = re.sub(r'\s+', '', clean_title)

        if card_name_no_space.lower() not in title_no_space.lower():
            print(f"    ❌ 카드명 불일치")
            print(f"       찾는 카드명: {card_name_no_space}")
            print(f"       상품 제목: {title_no_space}")
            continue

        print(f"    ✅ 카드명 일치")

        if rarity and rarity not in EXCLUDED_RARITIES:
            if rarity == 'MUR':
                if 'MUR' not in clean_title.upper():
                    print(f"    ❌ MUR 레어도 불일치")
                    continue
                print(f"    ✅ MUR 레어도 일치")
            elif rarity not in clean_title:
                print(f"    ❌ 레어도 '{rarity}' 불일치")
                continue

        valid_count += 1
        valid_items.append(item)
        print(f"    ✅ 유효한 상품!")

        if min_price is None or price < min_price:
            min_price = price
            min_price_mall = mall_name
            print(f"    💰 최저가 업데이트: {int(min_price)}원")

    print(f"\n📊 필터링 결과: 유효 상품 {valid_count}개")
    return min_price, valid_count, min_price_mall, valid_items


def get_all_prices_for_card(card_name: str, rarity: str, expansion_name: str) -> dict:
    """
    포켓몬카드 가격 통합 검색

    Returns:
        {
            'general_price': (최저가, 유효상품수, 판매처),
            'search_query': 검색어,
            'valid_items': 유효한 상품 전체 결과
        }
    """
    search_query = generate_pokemon_search_query(card_name, rarity, expansion_name)
    print(f"🔍 [통합검색] 검색어: {search_query}")

    items = search_naver_shopping(search_query)

    if not items:
        print(f"❌ 검색 결과 없음")
        return {
            'general_price': (None, 0, None),
            'search_query': search_query,
            'valid_items': [],
        }

    print(f"✅ 검색 결과: {len(items)}개")

    min_price, valid_count, min_price_mall, valid_items = filter_pokemon_items(items, card_name, rarity)

    if min_price:
        print(f"💰 일반 최저가: {int(min_price)}원 ({min_price_mall}) - 유효: {valid_count}개")
    else:
        print(f"⚠️ 일반 최저가 없음")

    return {
        'general_price': (min_price, valid_count, min_price_mall),
        'search_query': search_query,
        'valid_items': valid_items,
    }


# ==================== 원피스 한글판 ====================

def generate_onepiece_search_query(card_name: str, rarity: str, expansion_name: str, card_number: str, is_manga: bool = False) -> str:
    """원피스 카드 검색어 생성"""
    base_card_number = re.sub(r"_[Pp]\d+$", "", card_number)

    if card_number != base_card_number:
        print(f"  카드번호 변환: {card_number} → {base_card_number}")

    if is_manga:
        search_query = f"망가 {base_card_number}"
        print(f"  슈퍼 패러렐(망가) 검색어: {search_query}")
        return search_query

    if rarity and rarity.startswith('SP-'):
        search_query = f"SP {base_card_number}"
        print(f"  SP 카드 검색어 ({rarity}): {search_query}")
        return search_query

    if rarity and rarity.startswith('P-') and not base_card_number.startswith('P-'):
        search_query = f"패러렐 {base_card_number}"
        print(f"  패러렐 카드 검색어: {search_query}")
        return search_query

    if base_card_number.startswith('ST') or base_card_number.startswith('P-'):
        search_query = f"원피스 {base_card_number}"
        print(f"  일반 카드 검색어: {search_query}")
        return search_query

    print(f"  기본 검색어: {base_card_number}")
    return base_card_number


def filter_onepiece_items(items: List[dict], card_number: str, rarity: str, is_manga: bool = False) -> Tuple[Optional[float], int, Optional[str], List[dict]]:
    """원피스 카드 검색 결과 필터링"""
    min_price = None
    valid_count = 0
    min_price_mall = None
    valid_items = []

    excluded_malls = ["화성스토어-TCG-", "카드 베이스", "네이버", "쿠팡"]
    excluded_keywords = ['일본', '일본판', 'JP', 'JPN', '일판']

    base_card_number = re.sub(r"_[Pp]\d+", "", card_number, flags=re.IGNORECASE)
    is_special = rarity == 'SP-SP'
    is_parallel = rarity.startswith('P-')

    for item in items:
        title = item['title']
        price = float(item['lprice'])
        mall_name = item.get('mallName', '알 수 없음')

        if mall_name in excluded_malls:
            continue
        if any(keyword in title for keyword in excluded_keywords):
            continue

        clean_title = re.sub(r'<[^>]+>', '', title)

        if base_card_number not in clean_title:
            continue

        if is_manga:
            super_parallel_keywords = ['슈퍼 패러렐', '슈퍼패러렐', '슈퍼파라렐', '슈퍼 파라렐']
            manga_keywords = ['망가', 'MANGA', 'manga']
            if not (any(kw in clean_title for kw in super_parallel_keywords) or
                    any(kw in clean_title for kw in manga_keywords)):
                continue
            if price < 200000:
                continue
        elif is_special:
            if not any(kw in clean_title for kw in ['스페셜', 'SP']):
                continue
        elif is_parallel:
            parallel_keywords = ['패러렐', '다른', '패레', 'P시크릿레어', '페러럴', '패러럴', '페러렐', '페레']
            if not any(kw in clean_title for kw in parallel_keywords):
                continue

        valid_count += 1
        valid_items.append(item)

        if min_price is None or price < min_price:
            min_price = price
            min_price_mall = mall_name

    return min_price, valid_count, min_price_mall, valid_items


def get_onepiece_all_prices(card_name: str, rarity: str, expansion_name: str, card_number: str, is_manga: bool = False) -> dict:
    """
    원피스 카드 가격 통합 검색

    Returns:
        {
            'general_price': (최저가, 유효상품수, 판매처),
            'search_query': 검색어,
            'valid_items': 유효한 상품 전체 결과
        }
    """
    search_query = generate_onepiece_search_query(card_name, rarity, expansion_name, card_number, is_manga)
    print(f"🔍 [원피스 통합검색] 검색어: {search_query}")

    items = search_naver_shopping(search_query)

    if not items:
        print(f"❌ 검색 결과 없음")
        return {
            'general_price': (None, 0, None),
            'search_query': search_query,
            'valid_items': [],
        }

    print(f"✅ 검색 결과: {len(items)}개")

    min_price, valid_count, min_price_mall, valid_items = filter_onepiece_items(items, card_number, rarity, is_manga)

    if min_price:
        print(f"💰 일반 최저가: {int(min_price)}원 ({min_price_mall}) - 유효: {valid_count}개")
    else:
        print(f"⚠️ 일반 최저가 없음")

    return {
        'general_price': (min_price, valid_count, min_price_mall),
        'search_query': search_query,
        'valid_items': valid_items,
    }