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

# 모든 특수 레어도 목록 (필터링용) - MUR 추가
SPECIAL_RARITIES = ['UR', 'MUR', 'SSR', 'SR', 'CHR', 'CSR', 'BWR', 'AR', 'SAR', 'HR', 'MA', '몬스터볼', '마스터볼', '볼 미러', '타입 미러', '로켓단 미러', '이로치', '미러']


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
    
    print(f"\n📋 필터링 상세 로그 (총 {len(items)}개):")
    
    for idx, item in enumerate(items, 1):
        title = item['title']
        price = float(item['lprice'])
        mall_name = item.get('mallName', '알 수 없음')
        
        print(f"\n[{idx}] 가격: {int(price)}원 / 판매처: {mall_name}")
        
        # HTML 태그 제거
        clean_title = re.sub(r'<[^>]+>', '', title)
        print(f"    제목: {clean_title}")
        
        # 제외 판매처 체크
        if mall_name in excluded_malls:
            print(f"    ❌ 제외 판매처")
            continue
        
        # 일본판 제외
        if any(keyword in title for keyword in excluded_keywords):
            print(f"    ❌ 일본판 키워드 포함")
            continue
        
        # 카드명 매칭 (띄어쓰기 제거하고 비교)
        card_name_no_space = re.sub(r'\s+', '', card_name)
        title_no_space = re.sub(r'\s+', '', clean_title)
        
        if card_name_no_space.lower() not in title_no_space.lower():
            print(f"    ❌ 카드명 불일치")
            print(f"       찾는 카드명: {card_name_no_space}")
            print(f"       상품 제목: {title_no_space}")
            continue
        
        print(f"    ✅ 카드명 일치")
        
        # 레어도 매칭 (일반 레어도는 필터링 안함)
        if rarity and rarity not in EXCLUDED_RARITIES:
            # MUR은 "MUR" 또는 "mur"만 인식
            if rarity == 'MUR':
                clean_title_upper = clean_title.upper()
                if 'MUR' not in clean_title_upper:
                    print(f"    ❌ MUR 레어도 불일치")
                    continue
                print(f"    ✅ MUR 레어도 일치")
            elif rarity not in clean_title:
                print(f"    ❌ 레어도 '{rarity}' 불일치")
                continue
        
        # 유효한 상품
        valid_count += 1
        print(f"    ✅ 유효한 상품!")
        
        # 최저가 업데이트
        if min_price is None or price < min_price:
            min_price = price
            min_price_mall = mall_name
            print(f"    💰 최저가 업데이트: {int(min_price)}원")
    
    print(f"\n📊 필터링 결과: 유효 상품 {valid_count}개")
    
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
    
    print(f"\n🎯 TCG999 필터링 상세 로그:")
    
    for idx, item in enumerate(items, 1):
        title = item['title']
        price = float(item['lprice'])
        mall_name = item.get('mallName', '')
        
        # TCG999만 필터링
        if mall_name != 'TCG999':
            continue
        
        print(f"\n[TCG999 발견] 가격: {int(price)}원")
        
        # HTML 태그 제거
        clean_title = re.sub(r'<[^>]+>', '', title)
        print(f"    제목: {clean_title}")
        
        # 일본판 제외
        if any(keyword in title for keyword in excluded_keywords):
            print(f"    ❌ 일본판 키워드 포함")
            continue
        
        # 카드명 매칭 (띄어쓰기 제거하고 비교)
        card_name_no_space = re.sub(r'\s+', '', card_name)
        title_no_space = re.sub(r'\s+', '', clean_title)
        
        if card_name_no_space.lower() not in title_no_space.lower():
            print(f"    ❌ 카드명 불일치")
            print(f"       찾는 카드명: {card_name_no_space}")
            print(f"       상품 제목: {title_no_space}")
            continue
        
        print(f"    ✅ 카드명 일치")
        
        # 레어도 매칭 (일반 레어도는 필터링 안함)
        if rarity and rarity not in EXCLUDED_RARITIES:
            # MUR은 "MUR" 또는 "mur"만 인식
            if rarity == 'MUR':
                clean_title_upper = clean_title.upper()
                if 'MUR' not in clean_title_upper:
                    print(f"    ❌ MUR 레어도 불일치")
                    continue
                print(f"    ✅ MUR 레어도 일치")
            elif rarity not in clean_title:
                print(f"    ❌ 레어도 '{rarity}' 불일치")
                continue
        
        # 레어도가 검색어에 없는데 상품명에 특수 레어도가 있으면 제외
        if not rarity or rarity in EXCLUDED_RARITIES:
            # 특수 레어도 패턴 생성 (긴 것부터 매칭)
            rarity_pattern = r'\b(' + '|'.join([
                '로켓단 미러', '타입 미러', '볼 미러',
                '마스터볼', '몬스터볼',
                'MUR', 'UR', 'SSR', 'SR', 'CHR', 'CSR', 'BWR', 'AR', 'SAR', 'HR', 'MA',
                '이로치', '미러'
            ]) + r')\b'
            
            unwanted_rarity = re.search(rarity_pattern, clean_title, re.IGNORECASE)
            if unwanted_rarity:
                print(f"    ❌ 원치 않는 레어도 발견: {unwanted_rarity.group()}")
                continue
        
        # 첫 번째 매칭된 TCG999 상품 반환
        print(f"    ✅ TCG999 유효 상품!")
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

# pricehub/utils.py 끝에 추가

# ==================== 원피스 카드 유틸리티 ====================

def generate_onepiece_search_query(card_name: str, rarity: str, expansion_name: str, card_number: str, is_manga: bool = False) -> str:
    """
    원피스 카드 검색어 생성
    
    Args:
        card_name: 카드명
        rarity: 레어도 (예: "SR", "P-SR", "SP-SR", "SP-SEC")
        expansion_name: 확장팩명
        card_number: 카드번호 (예: "OP10-046", "OP10-046_P1", "OP08-058_P2")
        is_manga: 망가(슈퍼 패러렐) 여부
    
    Returns:
        검색 쿼리 문자열
    """
    # ★ 기본 카드번호에서 _P1, _P2 등 제거 (개선)
    # OP08-058_P2 → OP08-058
    # OP10-046_p1 → OP10-046 (대소문자 구분 없이)
    base_card_number = re.sub(r"_[Pp]\d+$", "", card_number)
    
    # 디버깅: 변환 결과 확인
    if card_number != base_card_number:
        print(f"  카드번호 변환: {card_number} → {base_card_number}")
    
    # 망가(슈퍼 패러렐) 처리
    if is_manga:
        search_query = f"망가 {base_card_number}"
        print(f"  슈퍼 패러렐(망가) 검색어: {search_query}")
        return search_query
    
    # SP 레어도 처리 (SP-로 시작하는 모든 레어도)
    # SP-SEC, SP-SR, SP-SL, SP-L, SP-SP 등
    if rarity and rarity.startswith('SP-'):
        search_query = f"SP {base_card_number}"
        print(f"  SP 카드 검색어 ({rarity}): {search_query}")
        return search_query
    
    # 패러렐 카드 처리 (P-로 시작, 단 P-프로모 제외)
    if rarity and rarity.startswith('P-') and not base_card_number.startswith('P-'):
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


def get_onepiece_all_prices(card_name: str, rarity: str, expansion_name: str, card_number: str, is_manga: bool = False) -> dict:
    """
    원피스 카드 가격 통합 검색
    
    Args:
        card_name: 카드명
        rarity: 레어도
        expansion_name: 확장팩명
        card_number: 카드번호
        is_manga: 망가(슈퍼 패러렐) 여부
    
    Returns:
        {
            'general_price': (최저가, 유효상품수, 판매처),
            'cardkingdom_price': (카드킹덤가격, 판매처),
            'search_query': 검색어
        }
    """
    # 검색어 생성 (is_manga 파라미터 추가)
    search_query = generate_onepiece_search_query(card_name, rarity, expansion_name, card_number, is_manga)
    
    print(f"🔍 [원피스 통합검색] 검색어: {search_query}")
    
    # 네이버 쇼핑 검색
    items = search_naver_shopping(search_query)
    
    if not items:
        print(f"❌ 검색 결과 없음")
        return {
            'general_price': (None, 0, None),
            'cardkingdom_price': (None, None),
            'search_query': search_query
        }
    
    print(f"✅ 검색 결과: {len(items)}개")
    
    # 1. 일반 최저가 필터링 (is_manga 사용)
    min_price, valid_count, min_price_mall = filter_onepiece_items(items, card_number, rarity, is_manga)
    
    # 2. 카드킹덤 필터링 (is_manga 사용)
    cardkingdom_price, cardkingdom_mall = filter_onepiece_cardkingdom_items(items, card_number, rarity, is_manga)
    
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


def filter_onepiece_items(items: List[dict], card_number: str, rarity: str, is_manga: bool = False) -> Tuple[Optional[float], int, Optional[str]]:
    """
    원피스 카드 검색 결과 필터링 (일반 최저가)
    
    Args:
        items: API 검색 결과
        card_number: 카드번호
        rarity: 레어도
        is_manga: 망가 여부
    """
    min_price = None
    valid_count = 0
    min_price_mall = None
    
    excluded_malls = ["화성스토어-TCG-", "카드 베이스", "네이버", "쿠팡"]
    excluded_keywords = ['일본', '일본판', 'JP', 'JPN', '일판']
    
    base_card_number = re.sub(r"_[Pp]\d+", "", card_number, flags=re.IGNORECASE)
    
    # 스페셜 여부 (SP-SP)
    is_special = rarity == 'SP-SP'
    # 패러렐 여부
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
        
        # 망가(슈퍼 패러렐) 키워드 확인
        if is_manga:
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
        
        valid_count += 1
        
        if min_price is None or price < min_price:
            min_price = price
            min_price_mall = mall_name
    
    return min_price, valid_count, min_price_mall


def filter_onepiece_cardkingdom_items(items: List[dict], card_number: str, rarity: str, is_manga: bool = False) -> Tuple[Optional[float], Optional[str]]:
    """
    원피스 카드 카드킹덤 전용 필터링
    
    Args:
        items: API 검색 결과
        card_number: 카드번호
        rarity: 레어도
        is_manga: 망가 여부
    """
    excluded_keywords = ['일본', '일본판', 'JP', 'JPN', '일판']
    base_card_number = re.sub(r"_[Pp]\d+", "", card_number, flags=re.IGNORECASE)
    
    # 스페셜/패러렐 여부
    is_special = rarity == 'SP-SP'
    is_parallel = rarity.startswith('P-')
    
    cardkingdom_keywords = ['카드킹덤', 'CARDKINGDOM', 'cardkingdom', '카드 킹덤']
    
    for item in items:
        title = item['title']
        price = float(item['lprice'])
        mall_name = item.get('mallName', '')
        
        has_cardkingdom = any(keyword in mall_name or keyword in title for keyword in cardkingdom_keywords)
        if not has_cardkingdom:
            continue
        
        if any(keyword in title for keyword in excluded_keywords):
            continue
        
        clean_title = re.sub(r'<[^>]+>', '', title)
        
        if base_card_number not in clean_title:
            continue
        
        # 망가 키워드 확인
        if is_manga:
            super_parallel_keywords = ['슈퍼 패러렐', '슈퍼패러렐', '슈퍼파라렐', '슈퍼 파라렐']
            manga_keywords = ['망가', 'MANGA', 'manga']
            
            has_super_parallel = any(kw in clean_title for kw in super_parallel_keywords)
            has_manga_kw = any(kw in clean_title for kw in manga_keywords)
            
            if not (has_super_parallel or has_manga_kw):
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
        
        return price, mall_name if mall_name else '카드킹덤'
    
    return None, None