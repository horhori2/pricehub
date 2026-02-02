# onepiece_utils.py
import re
import urllib.request
import urllib.parse
import json
from typing import Optional, Tuple, List

# 네이버 API 정보
NAVER_CLIENT_ID = "S_iul25XJKSybg_fiSAc"
NAVER_CLIENT_SECRET = "_73PsEM4om"


def generate_onepiece_search_query(card_name: str, rarity: str, expansion_name: str, card_number: str) -> str:
    """
    원피스 카드 검색어 생성
    
    Args:
        card_name: 카드명
        rarity: 레어도 (예: "SR", "P-SR", "SP-SR")
        expansion_name: 확장팩명
        card_number: 카드번호 (예: "OP10-046", "OP10-046_P1")
    
    Returns:
        검색 쿼리 문자열
    """
    # 기본 카드번호에서 _P 제거
    base_card_number = re.sub(r"_P\d+", "", card_number)
    
    # 슈퍼 패러렐 (망가) 처리
    if rarity.startswith('SP-') and rarity not in ['SP-SP']:
        # 망가로 검색
        search_query = f"망가 {base_card_number}"
        print(f"  슈퍼 패러렐(망가) 검색어: {search_query}")
        return search_query
    
    # 스페셜 카드 처리 (SP-SP)
    if rarity == 'SP-SP':
        search_query = f"SP {base_card_number}"
        print(f"  스페셜 카드 검색어: {search_query}")
        return search_query
    
    # 패러렐 카드 처리
    if rarity.startswith('P-'):
        search_query = f"패러렐 {base_card_number}"
        print(f"  패러렐 카드 검색어: {search_query}")
        return search_query
    
    # 일반 카드 (ST, P-프로모 등)
    if base_card_number.startswith('ST') or base_card_number.startswith('P-'):
        search_query = f"원피스 {base_card_number}"
        print(f"  일반 카드 검색어: {search_query}")
        return search_query
    
    # 기본 카드번호만
    print(f"  기본 검색어: {base_card_number}")
    return base_card_number


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


def filter_onepiece_items(items: List[dict], card_number: str, rarity: str) -> Tuple[Optional[float], int, Optional[str]]:
    """
    원피스 카드 검색 결과 필터링 (일반 최저가)
    
    Args:
        items: API 검색 결과
        card_number: 카드번호 (OP10-046_P1 형태)
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
    
    # 기본 카드번호 (OP10-046_P1 → OP10-046)
    base_card_number = re.sub(r"_P\d+", "", card_number)
    
    # 슈퍼 패러렐 여부
    is_super_parallel = rarity.startswith('SP-') and rarity not in ['SP-SP']
    # 스페셜 여부
    is_special = rarity == 'SP-SP'
    # 패러렐 여부
    is_parallel = rarity.startswith('P-')
    
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
        
        # 카드번호 매칭
        if base_card_number not in clean_title:
            continue
        
        # 슈퍼 패러렐 (망가) 키워드 확인
        if is_super_parallel:
            super_parallel_keywords = ['슈퍼 패러렐', '슈퍼패러렐', '슈퍼파라렐', '슈퍼 파라렐']
            manga_keywords = ['망가', 'MANGA', 'manga']
            
            has_super_parallel = any(kw in clean_title for kw in super_parallel_keywords)
            has_manga = any(kw in clean_title for kw in manga_keywords)
            
            if not (has_super_parallel or has_manga):
                continue
            
            # 가격 체크: 200,000원 미만 제외
            if price < 200000:
                continue
        
        # 스페셜 카드 키워드 확인
        elif is_special:
            special_keywords = ['스페셜', 'SP']
            if not any(kw in clean_title for kw in special_keywords):
                continue
        
        # 패러렐 키워드 확인
        elif is_parallel:
            parallel_keywords = ['패러렐', '다른', '패레', 'P시크릿레어', '페러럴', '패러럴', '페러렐', '페레']
            if not any(kw in clean_title for kw in parallel_keywords):
                continue
        
        # 유효한 상품
        valid_count += 1
        
        # 최저가 업데이트
        if min_price is None or price < min_price:
            min_price = price
            min_price_mall = mall_name
    
    return min_price, valid_count, min_price_mall


def filter_onepiece_tcg999_items(items: List[dict], card_number: str, rarity: str) -> Tuple[Optional[float], Optional[str]]:
    """
    원피스 카드 TCG999 전용 필터링
    
    Args:
        items: API 검색 결과
        card_number: 카드번호
        rarity: 레어도
    
    Returns:
        (TCG999 가격, 판매처명)
    """
    # 제외 키워드
    excluded_keywords = ['일본', '일본판', 'JP', 'JPN', '일판']
    
    # 기본 카드번호
    base_card_number = re.sub(r"_P\d+", "", card_number)
    
    # 슈퍼 패러렐/스페셜/패러렐 여부
    is_super_parallel = rarity.startswith('SP-') and rarity not in ['SP-SP']
    is_special = rarity == 'SP-SP'
    is_parallel = rarity.startswith('P-')
    
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
        
        # 카드번호 매칭
        if base_card_number not in clean_title:
            continue
        
        # 슈퍼 패러렐 키워드 확인
        if is_super_parallel:
            super_parallel_keywords = ['슈퍼 패러렐', '슈퍼패러렐', '슈퍼파라렐', '슈퍼 파라렐']
            manga_keywords = ['망가', 'MANGA', 'manga']
            
            has_super_parallel = any(kw in clean_title for kw in super_parallel_keywords)
            has_manga = any(kw in clean_title for kw in manga_keywords)
            
            if not (has_super_parallel or has_manga):
                continue
            
            if price < 200000:
                continue
        
        # 스페셜 키워드 확인
        elif is_special:
            if not any(kw in clean_title for kw in ['스페셜', 'SP']):
                continue
        
        # 패러렐 키워드 확인
        elif is_parallel:
            parallel_keywords = ['패러렐', '다른', '패레', 'P시크릿레어', '페러럴', '패러럴', '페러렐', '페레']
            if not any(kw in clean_title for kw in parallel_keywords):
                continue
        
        # 첫 번째 매칭된 TCG999 상품 반환
        return price, mall_name
    
    return None, None


def filter_onepiece_cardkingdom_items(items: List[dict], card_number: str, rarity: str) -> Tuple[Optional[float], Optional[str]]:
    """
    원피스 카드 카드킹덤 전용 필터링
    
    Args:
        items: API 검색 결과
        card_number: 카드번호
        rarity: 레어도
    
    Returns:
        (카드킹덤 가격, 판매처명)
    """
    # 제외 키워드
    excluded_keywords = ['일본', '일본판', 'JP', 'JPN', '일판']
    
    # 기본 카드번호
    base_card_number = re.sub(r"_P\d+", "", card_number)
    
    # 슈퍼 패러렐/스페셜/패러렐 여부
    is_super_parallel = rarity.startswith('SP-') and rarity not in ['SP-SP']
    is_special = rarity == 'SP-SP'
    is_parallel = rarity.startswith('P-')
    
    # 카드킹덤 키워드
    cardkingdom_keywords = ['카드킹덤', 'CARDKINGDOM', 'cardkingdom', '카드 킹덤']
    
    for item in items:
        title = item['title']
        price = float(item['lprice'])
        mall_name = item.get('mallName', '')
        
        # 카드킹덤 체크
        has_cardkingdom = any(keyword in mall_name or keyword in title for keyword in cardkingdom_keywords)
        if not has_cardkingdom:
            continue
        
        # 일본판 제외
        if any(keyword in title for keyword in excluded_keywords):
            continue
        
        # HTML 태그 제거
        clean_title = re.sub(r'<[^>]+>', '', title)
        
        # 카드번호 매칭
        if base_card_number not in clean_title:
            continue
        
        # 슈퍼 패러렐 키워드 확인
        if is_super_parallel:
            super_parallel_keywords = ['슈퍼 패러렐', '슈퍼패러렐', '슈퍼파라렐', '슈퍼 파라렐']
            manga_keywords = ['망가', 'MANGA', 'manga']
            
            has_super_parallel = any(kw in clean_title for kw in super_parallel_keywords)
            has_manga = any(kw in clean_title for kw in manga_keywords)
            
            if not (has_super_parallel or has_manga):
                continue
            
            if price < 200000:
                continue
        
        # 스페셜 키워드 확인
        elif is_special:
            if not any(kw in clean_title for kw in ['스페셜', 'SP']):
                continue
        
        # 패러렐 키워드 확인
        elif is_parallel:
            parallel_keywords = ['패러렐', '다른', '패레', 'P시크릿레어', '페러럴', '패러럴', '페러렐', '페레']
            if not any(kw in clean_title for kw in parallel_keywords):
                continue
        
        # 첫 번째 매칭된 카드킹덤 상품 반환
        return price, mall_name if mall_name else '카드킹덤'
    
    return None, None


def get_onepiece_all_prices(card_name: str, rarity: str, expansion_name: str, card_number: str) -> dict:
    """
    원피스 카드 가격 통합 검색
    
    Args:
        card_name: 카드명
        rarity: 레어도
        expansion_name: 확장팩명
        card_number: 카드번호
    
    Returns:
        {
            'general_price': (최저가, 유효상품수, 판매처),
            'cardkingdom_price': (카드킹덤가격, 판매처),
            'search_query': 검색어
        }
    """
    # 검색어 생성
    search_query = generate_onepiece_search_query(card_name, rarity, expansion_name, card_number)
    
    print(f"🔍 [원피스 통합검색] 검색어: {search_query}")
    
    # 네이버 쇼핑 검색 (한 번만!)
    items = search_naver_shopping(search_query)
    
    if not items:
        print(f"❌ 검색 결과 없음")
        return {
            'general_price': (None, 0, None),
            'cardkingdom_price': (None, None),
            'search_query': search_query
        }
    
    print(f"✅ 검색 결과: {len(items)}개")
    
    # 1. 일반 최저가 필터링
    min_price, valid_count, min_price_mall = filter_onepiece_items(items, card_number, rarity)
    
    # 2. 카드킹덤 필터링
    cardkingdom_price, cardkingdom_mall = filter_onepiece_cardkingdom_items(items, card_number, rarity)
    
    # 결과 출력
    if min_price:
        print(f"💰 일반 최저가: {int(min_price)}원 ({min_price_mall}) - 유효: {valid_count}개")
    else:
        print(f"⚠️ 일반 최저가 없음")
    
    if cardkingdom_price:
        print(f"👑 카드킹덤: {int(cardkingdom_price)}원")
    else:
        print(f"⚠️ 카드킹덤 없음")
    
    return {
        'general_price': (min_price, valid_count, min_price_mall),
        'cardkingdom_price': (cardkingdom_price, cardkingdom_mall),
        'search_query': search_query
    }