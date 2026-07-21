# pricehub/utils.py
import os
import re
import urllib.request
import urllib.parse
import json
import logging
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)

# ── 네이버 API (.env에서 로드) ───────────────────────────────────
NAVER_CLIENT_ID     = os.environ.get('NAVER_CLIENT_ID', '')
NAVER_CLIENT_SECRET = os.environ.get('NAVER_CLIENT_SECRET', '')

# ── 공통 필터 ─────────────────────────────────────────────────────
EXCLUDED_MALLS    = {'네이버', '쿠팡'}
EXCLUDED_KEYWORDS = ['일본', '일본판', 'JP', 'JPN', '일판']

# 우리 자신의 매장 — 시장 최저가(경쟁사 최저가) 계산에서 반드시 제외해야
# "판매가가 시장 최저가보다 낮다"는 비교가 의미를 가진다.
OUR_SHOPS = ['화성스토어-TCG-', '카드 베이스']


# ── 템플릿에 안전하게 심을 JSON 직렬화 ──────────────────────────────
_JSON_SCRIPT_ESCAPES = {
    ord('>'): '\\u003E',
    ord('<'): '\\u003C',
    ord('&'): '\\u0026',
}


def safe_json_dumps(obj, **kwargs) -> str:
    """<script> 태그 안에 심어도 안전한 JSON 문자열을 만든다.

    표준 json.dumps는 '<' '>' '&'를 이스케이프하지 않는다. 그래서 값 안에
    '</script>'가 섞여 들어오면(네이버 쇼핑 판매자명·상품명, URL 쿼리스트링 등
    외부/사용자 입력) HTML 파서가 그 지점에서 스크립트 태그를 조기 종료시켜
    뒤에 이어지는 내용이 그대로 실행되는 XSS로 이어진다.
    Django의 json_script 필터와 동일한 방식으로 <, >, & 를 유니코드
    이스케이프해 이 문제를 막는다. 반환값은 |safe 로 <script> 안에 그대로
    출력해도 안전하다.
    """
    return json.dumps(obj, **kwargs).translate(_JSON_SCRIPT_ESCAPES)

# ════════════════════════════════════════════════════════════════
# 포켓몬 한글판 — 레어도 상수
# ════════════════════════════════════════════════════════════════

EXCLUDED_RARITIES = ['RR', 'RRR', 'R', 'U', 'C']
GENERAL_RARITIES  = {'RR', 'RRR', 'R', 'U', 'C'}

HIGH_RARITY_KEYWORDS = [
    'UR', 'SSR', 'SR', 'CHR', 'CSR', 'BWR', 'AR', 'SAR', 'HR', 'MA',
    '몬스터볼', '마스터볼', '이로치', '미러',
]

HIGHER_RARITIES = {
    'C':   ['UR', 'SSR', 'SR', 'CHR', 'CSR', 'BWR', 'AR', 'SAR', 'HR', 'MA',
            'RR', 'RRR', 'R', 'U', 'MUR'],
    'U':   ['UR', 'SSR', 'SR', 'CHR', 'CSR', 'BWR', 'AR', 'SAR', 'HR', 'MA',
            'RR', 'RRR', 'MUR'],
    'R':   ['RR', 'RRR', 'SR', 'SAR', 'CSR', 'HR', 'UR', 'MUR', 'SSR', 'AR', 'CHR', 'BWR'],
    'RR':  ['RRR', 'SAR', 'CSR', 'HR', 'UR', 'MUR', 'SSR'],
    'RRR': ['SAR', 'CSR', 'HR', 'UR', 'MUR', 'SSR'],
}

SPECIAL_RARITIES = [
    'UR', 'MUR', 'SSR', 'SR', 'CHR', 'CSR', 'BWR', 'AR', 'SAR', 'HR', 'MA',
    '몬스터볼', '마스터볼', '볼 미러', '타입 미러', '로켓단 미러', '이로치', '미러',
]

MIRROR_RARITIES = {'미러', '몬스터볼', '마스터볼', '볼 미러', '타입 미러', '로켓단 미러'}

MIRROR_KEYWORDS = {
    '미러':        None,
    '몬스터볼':    '몬스터볼',
    '마스터볼':    '마스터볼',
    '볼 미러':     '볼',
    '타입 미러':   ['타입', '에너지'],
    '로켓단 미러': '로켓단 미러',
}

IROCHI_KEYWORDS   = ['이로치', '색이 다른', '색다른']
_IROCHI_SHINY_S_RE = re.compile(r'(?<![A-Za-z0-9])s(?![A-Za-z0-9])', re.IGNORECASE)

# ════════════════════════════════════════════════════════════════
# 원피스 한글판 — 레어도/키워드 상수
# ════════════════════════════════════════════════════════════════

_BASE_CARD_NUMBER_RE       = re.compile(r'_[Pp]\d+$', re.IGNORECASE)
_SUPER_PARALLEL_KEYWORDS  = ['슈퍼 패러렐', '슈퍼패러렐', '슈퍼파라렐', '슈퍼 파라렐']
_MANGA_KEYWORDS           = ['망가', 'MANGA', 'manga']
_PARALLEL_KEYWORDS        = ['패러렐', '다른', '패레', 'P시크릿레어', '페러럴', '패러럴', '페러렐', '페레', 'P-']
_ONEPIECE_GENERAL_RARITIES = {'C', 'R', 'UC', 'SR', 'SEC'}


# ════════════════════════════════════════════════════════════════
# 공통 유틸
# ════════════════════════════════════════════════════════════════

FilterResult = Tuple[Optional[float], int, Optional[str], List[dict]]


def search_naver_shopping(search_query: str) -> List[dict]:
    """네이버 쇼핑 API 검색"""
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        logger.error("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수가 설정되지 않았습니다.")
        return []
    try:
        enc_text = urllib.parse.quote(search_query)
        url = (
            f"https://openapi.naver.com/v1/search/shop"
            f"?query={enc_text}&sort=sim&exclude=used:rental:cbshop&display=50"
        )
        req = urllib.request.Request(url)
        req.add_header("X-Naver-Client-Id", NAVER_CLIENT_ID)
        req.add_header("X-Naver-Client-Secret", NAVER_CLIENT_SECRET)
        response = urllib.request.urlopen(req, timeout=15)
        if response.getcode() == 200:
            return json.loads(response.read()).get('items', [])
        logger.error("네이버 API 요청 실패: %s", response.getcode())
        return []
    except Exception as e:
        logger.exception("네이버 API 예외: %s", e)
        return []


def _word_boundary_match(keyword: str, text: str) -> bool:
    """영문 키워드는 단어 경계, 한글은 단순 포함으로 검사"""
    if keyword.isascii():
        return bool(re.search(
            r'(?<![A-Za-z0-9])' + re.escape(keyword) + r'(?![A-Za-z0-9])',
            text,
        ))
    return keyword in text


def _clean_title(raw_title: str) -> str:
    return re.sub(r'<[^>]+>', '', raw_title)


def _is_excluded(item: dict) -> bool:
    """공통 제외 조건 (판매처·일본판 키워드).

    주의: 우리 자신의 매장(OUR_SHOPS)은 여기서 걸러내지 않는다.
    raw_data(valid_items)에는 우리 매장 항목도 남겨둬야 카드 상세의
    판매처 목록에서 "우리 매장가"를 함께 보여줄 수 있다.
    시장 최저가 계산에서 우리 매장을 제외하는 로직은 _build_price_result()에 있다.
    """
    if item.get('mallName', '') in EXCLUDED_MALLS:
        return True
    return any(kw in item.get('title', '') for kw in EXCLUDED_KEYWORDS)


def _build_price_result(valid_items: List[dict]) -> FilterResult:
    """유효 상품 리스트에서 최저가·최저가 판매처를 추출해 반환.

    "시장 최저가"는 경쟁사 기준으로 계산한다 — 우리 매장(OUR_SHOPS) 항목은
    최저가 후보에서 제외한다 (우리가 제일 싸게 걸어도 그게 "시장 최저가"로
    잡히면 안 됨). 단, 매칭된 판매처가 우리 매장뿐이라면 비교할 경쟁사가
    없다는 뜻이므로 예외적으로 우리 매장가를 그대로 사용한다.
    raw_data로 저장되는 valid_items 자체는 우리 매장 항목을 포함해 그대로 반환
    (카드 상세 판매처 목록에서 우리 매장가를 함께 보여주기 위함).
    """
    if not valid_items:
        return None, 0, None, []
    competitor_items = [i for i in valid_items if i.get('mallName') not in OUR_SHOPS]
    price_pool = competitor_items or valid_items
    min_item = min(price_pool, key=lambda x: float(x['lprice']))
    return (
        float(min_item['lprice']),
        len(valid_items),
        min_item.get('mallName'),
        valid_items,
    )


# ════════════════════════════════════════════════════════════════
# 포켓몬 한글판
# ════════════════════════════════════════════════════════════════

def generate_pokemon_search_query(card_name: str, rarity: str, expansion_name: str) -> str:
    """포켓몬카드 검색어 생성"""
    query = f"포켓몬카드 {card_name}"
    if rarity and rarity not in EXCLUDED_RARITIES:
        query += f" {rarity}"
    if expansion_name:
        query += f" {expansion_name}"
    return query.strip()


def _has_high_rarity_keyword(clean_title: str) -> bool:
    return any(_word_boundary_match(kw, clean_title) for kw in HIGH_RARITY_KEYWORDS)


def filter_pokemon_items(items: List[dict], card_name: str, rarity: Optional[str],
                          is_teukil: bool = False) -> FilterResult:
    """포켓몬카드 검색 결과 필터링"""
    is_mirror_rarity  = rarity in MIRROR_RARITIES
    is_general_rarity = rarity in GENERAL_RARITIES
    is_irochi         = rarity == '이로치'
    card_name_no_space = re.sub(r'\s+', '', card_name).lower()
    valid_items = []

    for item in items:
        if _is_excluded(item):
            continue
        title = _clean_title(item['title'])
        if re.sub(r'\s+', '', title).lower().find(card_name_no_space) == -1:
            continue
        if is_teukil:
            if '특일' not in title and '특별' not in title:
                continue
        else:
            if '특일' in title or '특별' in title:
                continue

        if is_general_rarity:
            if _has_high_rarity_keyword(title):
                continue
            if any(_word_boundary_match(h, title) for h in HIGHER_RARITIES.get(rarity, [])):
                continue

        elif is_irochi:
            # 이로치/색이 다른/색다른 키워드 또는 단독 s/S 중 하나 이상 포함
            has_irochi_kw = any(kw in title for kw in IROCHI_KEYWORDS)
            has_shiny_s   = bool(_IROCHI_SHINY_S_RE.search(title))
            if not (has_irochi_kw or has_shiny_s):
                continue

        elif rarity and rarity not in EXCLUDED_RARITIES:
            if is_mirror_rarity:
                required_kw = MIRROR_KEYWORDS.get(rarity)
                if required_kw:
                    kws = required_kw if isinstance(required_kw, list) else [required_kw]
                    if not any(kw in title for kw in kws):
                        continue
            elif rarity == 'MUR':
                if 'MUR' not in title.upper():
                    continue
            else:
                if not _word_boundary_match(rarity, title):
                    continue

        valid_items.append(item)

    return _build_price_result(valid_items)


def get_all_prices_for_card(card_name: str, rarity: str, expansion_name: str,
                             is_teukil: bool = False) -> dict:
    """포켓몬카드 가격 통합 검색"""
    search_query = generate_pokemon_search_query(card_name, rarity, expansion_name)
    logger.debug("[포켓몬] 검색어: %s", search_query)

    items = search_naver_shopping(search_query)
    if not items:
        logger.debug("[포켓몬] 검색 결과 없음")
        return {'general_price': (None, 0, None), 'search_query': search_query, 'valid_items': []}

    logger.debug("[포켓몬] 검색 결과: %d개", len(items))
    min_price, valid_count, min_price_mall, valid_items = filter_pokemon_items(
        items, card_name, rarity, is_teukil,
    )

    if min_price:
        logger.debug("[포켓몬] 최저가: %d원 (%s) — 유효 %d개",
                     int(min_price), min_price_mall, valid_count)
    else:
        logger.debug("[포켓몬] 최저가 없음")

    return {
        'general_price': (min_price, valid_count, min_price_mall),
        'search_query': search_query,
        'valid_items': valid_items,
    }


# ════════════════════════════════════════════════════════════════
# 원피스 한글판 — 공통 필터 내부 헬퍼
# ════════════════════════════════════════════════════════════════

def _onepiece_rarity_flags(rarity: str):
    """레어도 문자열에서 is_manga, is_special, is_parallel 플래그 반환"""
    is_manga    = rarity == 'MANGA'
    is_special  = rarity == 'SP'
    is_parallel = rarity.startswith('P-')
    return is_manga, is_special, is_parallel


def _onepiece_title_matches(title: str, base_number: str,
                             is_manga: bool, is_special: bool, is_parallel: bool,
                             price: float, rarity: str = '') -> bool:
    """
    원피스 카드번호·레어도 필터를 적용해 상품이 유효한지 반환.
    공통 제외(판매처·일본판)는 호출 전에 처리되어 있어야 함.
    """
    if base_number not in title:
        return False

    has_parallel_kw = any(kw in title for kw in _PARALLEL_KEYWORDS)

    if is_manga:
        has_kw = (
            any(kw in title for kw in _SUPER_PARALLEL_KEYWORDS)
            or any(kw in title for kw in _MANGA_KEYWORDS)
        )
        if not has_kw or price < 200000:
            return False

    elif is_special:
        if not any(kw in title for kw in ['스페셜', 'SP']):
            return False

    elif is_parallel:
        # P-* 레어도: 패러렐 키워드 반드시 포함
        if not has_parallel_kw:
            return False

    elif rarity in _ONEPIECE_GENERAL_RARITIES:
        # 일반 레어도(C, R, UC, SR, SEC): 패러렐/스페셜 키워드 있으면 제외
        if has_parallel_kw:
            return False
        if '스페셜' in title or _word_boundary_match('SP', title):
            return False

    else:
        # 그 외 레어도(L, SL, SEC 등): 패러렐 키워드만 제외
        if has_parallel_kw:
            return False

    return True


# ════════════════════════════════════════════════════════════════
# 원피스 한글판 — 공개 함수
# ════════════════════════════════════════════════════════════════

def generate_onepiece_search_query(
    card_name: str,
    rarity: str,
    expansion_name: str,
    card_number: str,
) -> str:
    """
    원피스 카드 검색어 생성.

    MANGA          → '망가 {base}'
    SP             → '스페셜 {base}'
    P-*            → '패러렐 {base}'
    ST* / P-프로모  → '원피스 {base}'
    그 외           → '{base}'
    """
    base = _BASE_CARD_NUMBER_RE.sub('', card_number)

    if rarity == 'MANGA':
        return f"망가 {base}"
    if rarity == 'SP':
        return f"스페셜 {base}"
    if rarity.startswith('P-') and not base.startswith('P-'):
        return f"패러렐 {base}"
    if base.startswith(('ST', 'P-')):
        return f"원피스 {base}"
    return base


def filter_onepiece_items(
    items: List[dict],
    card_name: str,
    rarity: str,
    expansion_name: str,
    card_number: str,
) -> FilterResult:
    """원피스 카드 일반 필터링 (최저가 반환)"""
    base_number = _BASE_CARD_NUMBER_RE.sub('', card_number)
    is_manga, is_special, is_parallel = _onepiece_rarity_flags(rarity)
    valid_items = []

    for item in items:
        if _is_excluded(item):
            continue
        title = _clean_title(item['title'])
        price = float(item['lprice'])
        if _onepiece_title_matches(title, base_number, is_manga, is_special, is_parallel, price, rarity):
            valid_items.append(item)

    return _build_price_result(valid_items)



# ════════════════════════════════════════════════════════════════
# 디지몬 한글판
# ════════════════════════════════════════════════════════════════

_DIGIMON_PARALLEL_KEYWORDS = [
    '패러렐', '다른', '패레', 'P시크릿레어', '페러럴', '패러럴', '페러렐', '페레',
]

def generate_digimon_search_query(
    card_name: str,
    card_number: str,
    is_parallel: bool = False,
    is_scarce: bool = False,
    is_special: bool = False,
) -> str:
    """
    디지몬카드 검색어 생성.

    희소/패러렐/스페셜 접두사 → 카드번호 앞에 추가 (희소 > 패러렐 > 스페셜 우선순위)
    ST* / P-* 카드            → '디지몬 {card_number}'
    일반 카드                  → '{card_number}'
    """
    if is_scarce:
        prefix = "희소 "
    elif is_parallel:
        prefix = "패러렐 "
    elif is_special:
        prefix = "스페셜 "
    else:
        prefix = ""

    if card_number.startswith(('ST', 'P-')):
        return f"{prefix}디지몬 {card_number}".strip()
    return f"{prefix}{card_number}".strip()


def filter_digimon_items(
    items: List[dict],
    card_number: str,
    is_parallel: bool = False,
    is_scarce: bool = False,
    is_special: bool = False,
) -> FilterResult:
    """디지몬카드 검색 결과 필터링"""
    valid_items = []

    for item in items:
        if _is_excluded(item):
            continue
        title = _clean_title(item['title'])

        if card_number not in title:
            continue

        has_scarce_kw = "희소" in title
        if is_scarce and not has_scarce_kw:
            continue
        if not is_scarce and has_scarce_kw:
            continue

        has_parallel_kw = any(kw in title for kw in _DIGIMON_PARALLEL_KEYWORDS)
        if is_parallel and not has_parallel_kw:
            continue
        if not is_parallel and has_parallel_kw:
            continue

        has_special_kw = "스페셜" in title or _word_boundary_match('SP', title.upper())
        if is_special and not has_special_kw:
            continue
        if not is_special and has_special_kw:
            continue

        valid_items.append(item)

    return _build_price_result(valid_items)


def get_digimon_all_prices(
    card_name: str,
    card_number: str,
    is_parallel: bool = False,
    is_scarce: bool = False,
    is_special: bool = False,
) -> dict:
    """
    디지몬카드 가격 통합 검색 (API 1회 호출).

    Returns:
        {
            'general_price': (최저가, 유효상품수, 판매처),
            'search_query':  검색어,
            'valid_items':   유효 상품 전체 리스트,
        }
    """
    search_query = generate_digimon_search_query(card_name, card_number, is_parallel, is_scarce, is_special)
    logger.debug("[디지몬] 검색어: %s", search_query)

    items = search_naver_shopping(search_query)
    if not items:
        logger.debug("[디지몬] 검색 결과 없음")
        return {
            'general_price': (None, 0, None),
            'search_query':  search_query,
            'valid_items':   [],
        }

    logger.debug("[디지몬] 검색 결과: %d개", len(items))

    min_price, valid_count, min_price_mall, valid_items = filter_digimon_items(
        items, card_number, is_parallel, is_scarce, is_special,
    )

    if min_price:
        logger.debug("[디지몬] 최저가: %d원 (%s) — 유효 %d개",
                     int(min_price), min_price_mall, valid_count)

    return {
        'general_price': (min_price, valid_count, min_price_mall),
        'search_query':  search_query,
        'valid_items':   valid_items,
    }


def get_onepiece_all_prices(
    card_name: str,
    rarity: str,
    expansion_name: str,
    card_number: str,
) -> dict:
    """
    원피스 카드 가격 통합 검색 (API 1회 호출).

    Returns:
        {
            'general_price': (최저가, 유효상품수, 판매처),
            'search_query':  검색어,
            'valid_items':   유효 상품 전체 리스트,
        }
    """
    search_query = generate_onepiece_search_query(card_name, rarity, expansion_name, card_number)
    logger.debug("[원피스] 검색어: %s", search_query)

    items = search_naver_shopping(search_query)
    if not items:
        logger.debug("[원피스] 검색 결과 없음")
        return {
            'general_price': (None, 0, None),
            'search_query':  search_query,
            'valid_items':   [],
        }

    logger.debug("[원피스] 검색 결과: %d개", len(items))

    min_price, valid_count, min_price_mall, valid_items = filter_onepiece_items(
        items, card_name, rarity, expansion_name, card_number,
    )

    if min_price:
        logger.debug("[원피스] 최저가: %d원 (%s) — 유효 %d개",
                     int(min_price), min_price_mall, valid_count)

    return {
        'general_price': (min_price, valid_count, min_price_mall),
        'search_query':  search_query,
        'valid_items':   valid_items,
    }