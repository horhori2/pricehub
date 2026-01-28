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
SPECIAL_RARITIES = ['UR', 'SSR', 'SR', 'CHR', 'CSR', 'BWR', 'AR', 'SAR', 'HR', 'MA', '몬스터볼', '마스터볼', '볼 미러', '타입 미러', '로켓단 미러', '이로치', '미러']


def generate_pokemon_search_query(card_name: str, rarity: str, expansion_name: str) -> str:
    """
    포켓몬카드 검색어 생성
    
    Args:
        card_name: 카드명 (예: "팽도리")
        rarity: 레어도 (예: "AR", "C")
        expansion_name: 확장팩명 (예: "인페르노X")
    
    Returns:
        검색어 (예: "포켓몬카드 팽도리 AR 인페르노X" 또는 "포켓몬카드 팽도리 인페르노X")
    """
    # 기본 형식: 포켓몬카드 {카드명}
    search_query = f"포켓몬카드 {card_name}"
    
    # 레어도 추가 (제외 목록에 없는 경우만)
    if rarity and rarity not in EXCLUDED_RARITIES:
        search_query += f" {rarity}"
    
    # 확장팩명 추가
    if expansion_name:
        search_query += f" {expansion_name}"
    
    return search_query.strip()


def search_naver_shopping(search_query: str) -> List[dict]:
    """
    네이버 쇼핑 API 검색
    
    Args:
        search_query: 검색어
    
    Returns:
        검색 결과 리스트
    """
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


def filter_pokemon_items(items: List[dict], card_name: str, rarity: Optional[str]) -> Tuple[Optional[float], int, Optional[str]]:
    """
    포켓몬카드 검색 결과 필터링
    
    Args:
        items: API 검색 결과
        card_name: 카드명
        rarity: 레어도
    
    Returns:
        (최저가, 유효 상품 수, 최저가 판매처)
    """
    min_price = None
    valid_count = 0
    min_price_mall = None
    
    # 제외할 판매처
    excluded_malls = ["화성스토어-TCG-", "카드 베이스", "네이버", "쿠팡"]
    
    # 제외 키워드
    excluded_keywords = ['일본', '일본판', 'JP', 'JPN', '일판']
    
    for item in items:
        title = item['title']
        price = float(item['lprice'])
        mall_name = item.get('mallName', '알 수 없음')
        
        # 제외 판매처 체크
        if mall_name in excluded_malls:
            continue
        
        # 일본판 제외
        if any(keyword in title for keyword in excluded_keywords):
            continue
        
        # HTML 태그 제거
        clean_title = re.sub(r'<[^>]+>', '', title)
        
        # 카드명 매칭 (띄어쓰기 제거하고 비교)
        card_name_no_space = re.sub(r'\s+', '', card_name)
        title_no_space = re.sub(r'\s+', '', clean_title)
        
        if card_name_no_space.lower() not in title_no_space.lower():
            continue
        
        # 레어도 매칭 (일반 레어도는 필터링 안함)
        if rarity and rarity not in EXCLUDED_RARITIES:
            if rarity not in clean_title:
                continue
        
        # 유효한 상품
        valid_count += 1
        
        # 최저가 업데이트
        if min_price is None or price < min_price:
            min_price = price
            min_price_mall = mall_name
    
    return min_price, valid_count, min_price_mall


def get_lowest_price_for_card(card_name: str, rarity: str, expansion_name: str) -> Tuple[Optional[float], int, str, Optional[str]]:
    """
    포켓몬카드 최저가 검색
    
    Args:
        card_name: 카드명
        rarity: 레어도
        expansion_name: 확장팩명
    
    Returns:
        (최저가, 유효 상품 수, 검색어, 최저가 판매처)
    """
    # 검색어 생성
    search_query = generate_pokemon_search_query(card_name, rarity, expansion_name)
    
    print(f"🔍 검색어: {search_query}")
    if rarity in EXCLUDED_RARITIES:
        print(f"ℹ️  레어도 '{rarity}'는 검색어에서 제외됨")
    
    # 네이버 쇼핑 검색
    items = search_naver_shopping(search_query)
    
    if not items:
        print(f"❌ 검색 결과 없음")
        return None, 0, search_query, None
    
    print(f"✅ 검색 결과: {len(items)}개")
    
    # 필터링
    min_price, valid_count, min_price_mall = filter_pokemon_items(items, card_name, rarity)
    
    if min_price:
        print(f"💰 최저가: {int(min_price)}원 (유효 상품: {valid_count}개)")
        print(f"🏪 판매처: {min_price_mall}")
    else:
        print(f"❌ 필터링 후 유효 상품 없음")
    
    return min_price, valid_count, search_query, min_price_mall

def filter_tcg999_items(items: List[dict], card_name: str, rarity: Optional[str]) -> Tuple[Optional[float], Optional[str]]:
    """
    TCG999 판매처 전용 필터링
    
    Args:
        items: API 검색 결과
        card_name: 카드명
        rarity: 레어도
    
    Returns:
        (TCG999 가격, 판매처명)
    """
    # 제외 키워드
    excluded_keywords = ['일본', '일본판', 'JP', 'JPN', '일판']
    
    for item in items:
        title = item['title']
        price = float(item['lprice'])
        mall_name = item.get('mallName', '')
        
        # TCG999만 필터링
        if mall_name != 'TCG999':
            continue
        
        # 일본판 제외
        if any(keyword in title for keyword in excluded_keywords):
            continue
        
        # HTML 태그 제거
        clean_title = re.sub(r'<[^>]+>', '', title)
        
        # 카드명 매칭 (띄어쓰기 제거하고 비교)
        card_name_no_space = re.sub(r'\s+', '', card_name)
        title_no_space = re.sub(r'\s+', '', clean_title)
        
        if card_name_no_space.lower() not in title_no_space.lower():
            continue
        
        # 레어도 매칭 (일반 레어도는 필터링 안함)
        if rarity and rarity not in EXCLUDED_RARITIES:
            if rarity not in clean_title:
                continue
        
        # 레어도가 검색어에 없는데 상품명에 특수 레어도가 있으면 제외
        if not rarity or rarity in EXCLUDED_RARITIES:
            # 특수 레어도 패턴 생성 (긴 것부터 매칭)
            rarity_pattern = r'\b(' + '|'.join([
                '로켓단 미러', '타입 미러', '볼 미러',
                '마스터볼', '몬스터볼',
                'UR', 'SSR', 'SR', 'CHR', 'CSR', 'BWR', 'AR', 'SAR', 'HR', 'MA',
                '이로치', '미러'
            ]) + r')\b'
            
            unwanted_rarity = re.search(rarity_pattern, clean_title)
            if unwanted_rarity:
                continue
        
        # 첫 번째 매칭된 TCG999 상품 반환
        return price, mall_name
    
    return None, None


def get_tcg999_price_for_card(card_name: str, rarity: str, expansion_name: str) -> Tuple[Optional[float], str, Optional[str]]:
    """
    포켓몬카드 TCG999 가격 검색
    
    Args:
        card_name: 카드명
        rarity: 레어도
        expansion_name: 확장팩명
    
    Returns:
        (TCG999 가격, 검색어, 판매처명)
    """
    # 검색어 생성
    search_query = generate_pokemon_search_query(card_name, rarity, expansion_name)
    
    print(f"🔍 [TCG999] 검색어: {search_query}")
    
    # 네이버 쇼핑 검색
    items = search_naver_shopping(search_query)
    
    if not items:
        print(f"❌ 검색 결과 없음")
        return None, search_query, None
    
    print(f"✅ 검색 결과: {len(items)}개")
    
    # TCG999 필터링
    tcg999_price, mall_name = filter_tcg999_items(items, card_name, rarity)
    
    if tcg999_price:
        print(f"💰 [TCG999] 가격: {int(tcg999_price)}원")
    else:
        print(f"⚠️ TCG999 판매처 없음")
    
    return tcg999_price, search_query, mall_name

def get_all_prices_for_card(card_name: str, rarity: str, expansion_name: str) -> dict:
    """
    포켓몬카드 가격 통합 검색 (한 번의 API 호출로 일반 최저가 + TCG999 가격)
    
    Args:
        card_name: 카드명
        rarity: 레어도
        expansion_name: 확장팩명
    
    Returns:
        {
            'general_price': (최저가, 유효상품수, 판매처),
            'tcg999_price': (TCG999가격, 판매처),
            'search_query': 검색어
        }
    """
    # 검색어 생성
    search_query = generate_pokemon_search_query(card_name, rarity, expansion_name)
    
    print(f"🔍 [통합검색] 검색어: {search_query}")
    
    # 네이버 쇼핑 검색 (한 번만!)
    items = search_naver_shopping(search_query)
    
    if not items:
        print(f"❌ 검색 결과 없음")
        return {
            'general_price': (None, 0, None),
            'tcg999_price': (None, None),
            'search_query': search_query
        }
    
    print(f"✅ 검색 결과: {len(items)}개")
    
    # 1. 일반 최저가 필터링
    min_price, valid_count, min_price_mall = filter_pokemon_items(items, card_name, rarity)
    
    # 2. TCG999 필터링
    tcg999_price, tcg999_mall = filter_tcg999_items(items, card_name, rarity)
    
    # 결과 출력
    if min_price:
        print(f"💰 일반 최저가: {int(min_price)}원 ({min_price_mall}) - 유효: {valid_count}개")
    else:
        print(f"⚠️ 일반 최저가 없음")
    
    if tcg999_price:
        print(f"🎯 TCG999: {int(tcg999_price)}원")
    else:
        print(f"⚠️ TCG999 없음")
    
    return {
        'general_price': (min_price, valid_count, min_price_mall),
        'tcg999_price': (tcg999_price, tcg999_mall),
        'search_query': search_query
    }