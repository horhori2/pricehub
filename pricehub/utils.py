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
EXCLUDED_MALLS    = {'네이버', '쿠팡', 'KREAM'}
EXCLUDED_KEYWORDS = ['일본', '일본판', 'JP', 'JPN', '일판', '일어판', '영문', '영문판', '미국', '미국판', '영어']

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
_REDMANGA_KEYWORDS        = ['적망가', '레드망가', '레드', '적']
_PARALLEL_KEYWORDS        = ['패러렐', '다른', '패레', 'P시크릿레어', '페러럴', '패러럴', '페러렐', '페레']
_ONEPIECE_GENERAL_RARITIES = {'C', 'R', 'UC', 'SR', 'SEC'}

# 판매자가 "패러렐"을 한글 대신 레어도 코드/영문 약어로만 표기하는 경우
# (예: "사보 P리더 OP13-004", "사보 L-P", "사보 리더 L PR OP13-004").
# "P-L"/"P-SR" 같은 레어도 코드 표기는 이 게임 자체 레어도 체계(P-SEC/P-SR/
# P-L 등, RARITY_CHOICES 참고)와 동일해서 판매자가 그대로 씀. 예전엔 그냥
# 'P-' 문자열 포함 여부로 봤었는데, 그러면 프로모 카드번호 자체가 전부
# "P-001"처럼 'P-'를 포함해서 프로모 카드는 항상 "패러렐 키워드 있음"으로
# 오판정되어 가격 수집이 전혀 안 되는 버그가 있었음(37장 중 raw_data가
# 제대로 채워진 카드 0장으로 확인됨) — 레어도 코드 전체가 정확히 매치될
# 때만 인정하도록 수정.
_ONEPIECE_PARALLEL_RARITY_CODE_RE = re.compile(
    r'(?<![A-Za-z0-9])P-(?:SEC|SR|SL|UC|L|R|C|D)(?![A-Za-z0-9])'
)
_ONEPIECE_PARALLEL_ABBREV_RE = re.compile(r'(?<![A-Za-z0-9])PR(?![A-Za-z0-9])', re.IGNORECASE)
_ONEPIECE_PARALLEL_ABBREV_SUBSTR = ['P리더', 'L-P']


def _has_onepiece_parallel_kw(title: str, base_number: str = '') -> bool:
    if any(kw in title for kw in _PARALLEL_KEYWORDS):
        return True
    if _ONEPIECE_PARALLEL_RARITY_CODE_RE.search(title):
        return True
    if any(s in title for s in _ONEPIECE_PARALLEL_ABBREV_SUBSTR):
        return True
    if base_number.startswith('P-'):
        # 프로모 카드번호(P-001 등) 자체와 혼동 방지 — 예: "PROMO"의 "PR"
        return False
    return bool(_ONEPIECE_PARALLEL_ABBREV_RE.search(title))

# "두웅" — 덱 동봉 아크릴 스탠드 굿즈(EB03/OP13 등). 카드번호가 D1~D5 같은
# 자체 부여 번호라 검색어로 못 써서(예: 'D4' 검색은 노이즈만 나옴) 완전히
# 별도의 검색어·필터 로직을 쓴다.
_DOONG_RARITIES = {'D', 'P-D'}


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


def _pokemon_item_is_valid(title: str, card_name_no_space: str, rarity: Optional[str], is_teukil: bool,
                            is_mirror_rarity: bool, is_general_rarity: bool, is_irochi: bool) -> bool:
    """
    포켓몬 상품 1건(제목)이 카드(이름·레어도·특일여부)에 유효한 매칭인지 판정.
    _is_excluded()(판매처·일본판 공통 제외)는 호출 전에 처리되어 있어야 함.
    filter_pokemon_items()의 매칭 로직 본체 — 오염 데이터 재검사 스크립트에서도
    그대로 재사용하기 위해 분리.
    """
    if re.sub(r'\s+', '', title).lower().find(card_name_no_space) == -1:
        return False
    if is_teukil:
        if '특일' not in title and '특별' not in title:
            return False
    else:
        if '특일' in title or '특별' in title:
            return False

    if is_general_rarity:
        if _has_high_rarity_keyword(title):
            return False
        if any(_word_boundary_match(h, title) for h in HIGHER_RARITIES.get(rarity, [])):
            return False

    elif is_irochi:
        # 이로치/색이 다른/색다른 키워드 또는 단독 s/S 중 하나 이상 포함
        has_irochi_kw = any(kw in title for kw in IROCHI_KEYWORDS)
        has_shiny_s   = bool(_IROCHI_SHINY_S_RE.search(title))
        if not (has_irochi_kw or has_shiny_s):
            return False

    elif rarity and rarity not in EXCLUDED_RARITIES:
        if is_mirror_rarity:
            required_kw = MIRROR_KEYWORDS.get(rarity)
            if required_kw:
                kws = required_kw if isinstance(required_kw, list) else [required_kw]
                if not any(kw in title for kw in kws):
                    return False
        elif rarity == 'MUR':
            if 'MUR' not in title.upper():
                return False
        else:
            if not _word_boundary_match(rarity, title):
                return False

    return True


def filter_pokemon_items(items: List[dict], card_name: str, rarity: Optional[str],
                          is_teukil: bool = False) -> FilterResult:
    """포켓몬카드 검색 결과 필터링"""
    is_mirror_rarity  = rarity in MIRROR_RARITIES
    is_general_rarity = rarity in GENERAL_RARITIES
    is_irochi         = rarity == '이로치'
    card_name_no_space = re.sub(r'\s+', '', card_name).lower()

    valid_items = [
        item for item in items
        if not _is_excluded(item)
        and _pokemon_item_is_valid(
            _clean_title(item['title']), card_name_no_space, rarity, is_teukil,
            is_mirror_rarity, is_general_rarity, is_irochi,
        )
    ]

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
    """레어도 문자열에서 is_manga, is_special, is_parallel, is_redmanga 플래그 반환"""
    is_manga    = rarity == 'MANGA'
    is_special  = rarity == 'SP'
    is_parallel = rarity.startswith('P-')
    is_redmanga = rarity == 'REDMANGA'
    return is_manga, is_special, is_parallel, is_redmanga


def _doong_search_query(shop_product_code: str, card_name: str) -> str:
    """
    "두웅" 전용 검색어. 카드번호(D1~D5 등) 대신 상품코드의 확장팩 접두사
    (예: 'OPC-EB03-D4-K' → 'EB03')와 카드명을 그대로 붙여서 검색한다.

    예: shop_product_code='OPC-EB03-D4-K', card_name='금 두웅 (나미)'
        → 'EB03 금 두웅 나미'
    """
    parts = shop_product_code.upper().split('-')
    expansion_code = parts[1] if len(parts) > 1 else ''
    flat_name = re.sub(r'\s+', ' ', card_name.replace('(', ' ').replace(')', ' ')).strip()
    return f"{expansion_code} {flat_name}".strip()


def _doong_item_is_valid(title: str, card_name: str, is_parallel: bool) -> bool:
    """
    "두웅" 상품 1건이 유효한지 판정.

    실제 판매 상품명 표기가 "금"/"패러렐"/캐릭터명만 등 제각각이라, 패러렐
    (금) 등급이면 이 중 하나라도 맞으면 유효로 본다(OR). 일반 등급이면
    카드명 괄호 안 캐릭터명(있는 경우)만 확인한다.
    예: '두웅 (나미)' → 괄호 안 '나미', '금 두웅' → 괄호 없음(캐릭터명 없음).
    """
    if '두웅' not in title:
        return False

    m = re.search(r'\(([^)]+)\)', card_name)
    char_name = m.group(1).strip() if m else ''

    if is_parallel:
        if '금' in title:
            return True
        if any(kw in title for kw in _PARALLEL_KEYWORDS):
            return True
        return bool(char_name) and char_name in title

    if char_name:
        return char_name in title
    return True


def _onepiece_title_matches(title: str, base_number: str,
                             is_manga: bool, is_special: bool, is_parallel: bool,
                             price: float, rarity: str = '', card_name: str = '',
                             is_redmanga: bool = False) -> bool:
    """
    원피스 카드번호·레어도 필터를 적용해 상품이 유효한지 반환.
    공통 제외(판매처·일본판)는 호출 전에 처리되어 있어야 함.
    """
    if rarity in _DOONG_RARITIES:
        return _doong_item_is_valid(title, card_name, is_parallel)

    if base_number not in title:
        return False

    has_parallel_kw = _has_onepiece_parallel_kw(title, base_number)

    if is_manga:
        has_kw = (
            any(kw in title for kw in _SUPER_PARALLEL_KEYWORDS)
            or any(kw in title for kw in _MANGA_KEYWORDS)
        )
        if not has_kw or price < 200000:
            return False

    elif is_redmanga:
        # 적망가(레드망가) — 일반 망가 검색어("망가 {base}")로 찾되, 제목에
        # 적망가/레드망가/레드/적 키워드가 있는 것만 유효로 본다.
        if not any(kw in title for kw in _REDMANGA_KEYWORDS):
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
    shop_product_code: str = '',
) -> str:
    """
    원피스 카드 검색어 생성.

    D / P-D(두웅)  → '{확장팩코드} {카드명}' (_doong_search_query 참고)
    MANGA          → '망가 {base}'
    REDMANGA       → '망가 {base}' (검색어는 MANGA와 동일, 결과 필터링에서 구분)
    SP             → '스페셜 {base}'
    P-*            → '패러렐 {base}'
    ST* / P-프로모  → '원피스 {base}'
    그 외           → '{base}'
    """
    if rarity in _DOONG_RARITIES:
        return _doong_search_query(shop_product_code, card_name)

    base = _BASE_CARD_NUMBER_RE.sub('', card_number)

    if rarity in ('MANGA', 'REDMANGA'):
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
    is_manga, is_special, is_parallel, is_redmanga = _onepiece_rarity_flags(rarity)
    valid_items = []

    for item in items:
        if _is_excluded(item):
            continue
        title = _clean_title(item['title'])
        price = float(item['lprice'])
        if _onepiece_title_matches(title, base_number, is_manga, is_special, is_parallel, price, rarity, card_name, is_redmanga):
            valid_items.append(item)

    return _build_price_result(valid_items)



# ════════════════════════════════════════════════════════════════
# 디지몬 한글판
# ════════════════════════════════════════════════════════════════

_DIGIMON_PARALLEL_KEYWORDS = [
    '패러렐', '다른', '패레', 'P시크릿레어', '페러럴', '패러럴', '페러렐', '페레',
]

# 일부 판매자(예: 카드슬래쉬)는 "★"(별 1개)로 패러렐을, "★★"(별 2개)로
# 희소를 표기함 — 그냥 문자 포함 검사만 하면 '★'가 '★★'의 부분집합이라
# 겹쳐버리므로, 별 두 개(희소)부터 떼어내고 남은 단독 별만 패러렐로 본다.
_DIGIMON_SCARCE_STAR   = '★★'
_DIGIMON_PARALLEL_STAR = '★'


def _has_digimon_scarce_star(title: str) -> bool:
    return _DIGIMON_SCARCE_STAR in title


def _has_digimon_parallel_star(title: str) -> bool:
    return _DIGIMON_PARALLEL_STAR in title.replace(_DIGIMON_SCARCE_STAR, '')

# 판매자가 "패러렐"을 한글 대신 영문 약어로만 표기하는 경우 — 위 키워드로는
# 못 잡아서 일반 카드 raw_data에 패러렐 상품이 그대로 섞여 들어갔었음
# (예: "...BT9-081)PSR", "...데크스도루고라몬 [P]", "...데크스도루고라몬 P").
_DIGIMON_PARALLEL_ABBREV_RE = [
    re.compile(r'(?<![A-Za-z0-9])PSR(?![A-Za-z0-9])', re.IGNORECASE),
    re.compile(r'\[P\]', re.IGNORECASE),
    re.compile(r'\(P\)', re.IGNORECASE),
]
# 제목 맨 끝에 단독으로 붙은 "P"
_DIGIMON_TRAILING_P_RE = re.compile(r'(?<![A-Za-z0-9])P$')


def _has_digimon_parallel_abbrev(title: str, card_number: str = '') -> bool:
    # 프로모 계열 카드번호('P-', 'LM-' — 둘 다 PROMO 확장팩 소속)는
    # "(P)"/"[P]"/단독 "P"가 패러렐이 아니라 "프로모"를 뜻하는 표기라
    # 약어 판정 자체를 적용하지 않는다.
    if card_number.startswith(('P-', 'LM-')):
        return False
    stripped = title.strip()
    if any(p.search(stripped) for p in _DIGIMON_PARALLEL_ABBREV_RE):
        return True
    return bool(_DIGIMON_TRAILING_P_RE.search(stripped))

# RBK-01(라이징 윈드) — 재록 확장팩. 기존 다른 확장팩 카드를 그대로
# 재수록하면서 거의 대부분 패러렐로 분류해서 넣는 바람에, 원본 확장팩의
# 패러렐 카드와 카드번호가 그대로 겹친다(예: BT1-060이 원본 BT1에도,
# RBK-01에도 둘 다 패러렐로 존재). 판매자들은 제목에 재록판이라는 표시
# (RB1/라이징윈드/리부트부스트 등)를 남기므로 이걸로 구분한다.
_DIGIMON_RBK01_MARKERS = ['RB1', '라이징윈드', '라이징 윈드', '리부트부스트', 'RBK-01', 'RBK']


def _has_digimon_rbk01_marker(title: str) -> bool:
    return any(kw in title for kw in _DIGIMON_RBK01_MARKERS)


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


def _digimon_item_is_valid(title: str, card_number: str,
                            is_parallel: bool = False, is_scarce: bool = False,
                            is_special: bool = False,
                            rbk01_marker_required: Optional[bool] = None) -> bool:
    """
    디지몬 상품 1건(제목)이 카드(카드번호·희소/패러렐/스페셜 여부)에 유효한
    매칭인지 판정. _is_excluded()는 호출 전에 처리되어 있어야 함.
    filter_digimon_items()의 매칭 로직 본체 — 오염 데이터 재검사 스크립트에서도
    그대로 재사용하기 위해 분리.

    rbk01_marker_required: RBK-01(라이징 윈드) 재록과 카드번호가 겹치는
    카드에서만 의미 있음.
        True  -> 이 카드 자체가 RBK-01 쪽 — 제목에 재록 표시가 있어야 유효.
        False -> 이 카드번호가 RBK-01에도 있어서 겹침 — 재록 표시가 있으면
                 그건 RBK-01 상품이니 이 카드(원본)에서는 제외.
        None  -> RBK-01과 무관한 카드 — 검사 안 함.
    """
    if card_number not in title:
        return False

    if rbk01_marker_required is True and not _has_digimon_rbk01_marker(title):
        return False
    if rbk01_marker_required is False and _has_digimon_rbk01_marker(title):
        return False

    has_scarce_kw = "희소" in title or _has_digimon_scarce_star(title)
    if is_scarce and not has_scarce_kw:
        return False
    if not is_scarce and has_scarce_kw:
        return False

    has_parallel_kw = (
        any(kw in title for kw in _DIGIMON_PARALLEL_KEYWORDS)
        or _has_digimon_parallel_abbrev(title, card_number)
        or _has_digimon_parallel_star(title)
    )
    if is_parallel and not has_parallel_kw:
        return False
    if not is_parallel and has_parallel_kw:
        return False

    has_special_kw = "스페셜" in title or _word_boundary_match('SP', title.upper())
    if is_special and not has_special_kw:
        return False
    if not is_special and has_special_kw:
        return False

    return True


def filter_digimon_items(
    items: List[dict],
    card_number: str,
    is_parallel: bool = False,
    is_scarce: bool = False,
    is_special: bool = False,
    rbk01_marker_required: Optional[bool] = None,
) -> FilterResult:
    """디지몬카드 검색 결과 필터링"""
    valid_items = [
        item for item in items
        if not _is_excluded(item)
        and _digimon_item_is_valid(
            _clean_title(item['title']), card_number, is_parallel, is_scarce, is_special,
            rbk01_marker_required,
        )
    ]

    return _build_price_result(valid_items)


def get_digimon_all_prices(
    card_name: str,
    card_number: str,
    is_parallel: bool = False,
    is_scarce: bool = False,
    is_special: bool = False,
    rbk01_marker_required: Optional[bool] = None,
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
        items, card_number, is_parallel, is_scarce, is_special, rbk01_marker_required,
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
    shop_product_code: str = '',
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
    search_query = generate_onepiece_search_query(card_name, rarity, expansion_name, card_number, shop_product_code)
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