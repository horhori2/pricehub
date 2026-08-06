"""
pricehub/card_controltower_client.py

card-controltower(네이버 스마트스토어 매장 관리 백엔드)를 호출하는 얇은 클라이언트.
pricesite/api_client.py가 pricehub 자체 REST API를 부르는 것과 같은 패턴 —
서버 간 통신이라 인증 정보는 여기(서버)에서만 보관하고 브라우저에는 노출하지 않는다.

card-controltower는 pricehub 같은 API Key 발급 체계가 없고 매장별 관리자 계정
(Busan_admin/Gwangju_admin) 로그인으로 JWT를 받는 구조라, 로그인도 이 모듈이 담당한다.
"""
import requests
from django.conf import settings
from django.core.cache import cache

# JWT 만료는 24시간(card-controltower의 jwt.expiration-hours)이지만 안전 마진을 두고
# 이보다 짧게 캐시한다 — 만료 시각을 정확히 안 챙겨도 재로그인 비용이 크지 않기 때문.
_TOKEN_CACHE_TTL = 12 * 3600  # 12시간

# 카드 목록 전체(매장당 1만 건 이상)를 매 요청마다 다시 부르면 느리다. 실제 네이버 반영은
# "오늘의 작업" 흐름을 통해서만 값이 바뀌므로 몇 분 단위로 캐시해도 크게 stale해지지 않는다.
_CARDS_CACHE_TTL = 300  # 5분


class CardControltowerAPIError(Exception):
    """card-controltower API 호출 실패 (네트워크 오류, 인증 실패, 5xx, 타임아웃 등)"""


def _store_config(store):
    cfg = settings.CARD_CONTROLTOWER_STORES.get(store)
    if not cfg:
        raise CardControltowerAPIError(f'알 수 없는 매장: {store}')
    if not cfg.get('username') or not cfg.get('password'):
        raise CardControltowerAPIError(
            f'{store} 계정 정보가 설정되지 않음 (.env의 CARD_CONTROLTOWER_{store.upper()}_USER/PASSWORD 확인)'
        )
    return cfg


def _login(store):
    cfg = _store_config(store)
    url = f'{settings.CARD_CONTROLTOWER_BASE_URL}/api/auth/login'
    try:
        resp = requests.post(
            url,
            json={'id': cfg['username'], 'password': cfg['password']},
            timeout=10,
        )
        resp.raise_for_status()
        token = resp.json().get('token')
    except requests.RequestException as e:
        raise CardControltowerAPIError(f'card-controltower 로그인 실패: {store} ({e})') from e
    if not token:
        raise CardControltowerAPIError(f'card-controltower 로그인 응답에 token 없음: {store}')
    return token


def _get_token(store, force_refresh=False):
    cache_key = f'card-controltower:token:{store}'
    if not force_refresh:
        cached = cache.get(cache_key)
        if cached:
            return cached
    token = _login(store)
    cache.set(cache_key, token, _TOKEN_CACHE_TTL)
    return token


def fetch_store_cards(store, force_refresh=False):
    """
    매장(busan/gwangju)의 전체 카드 목록(GET /api/cards) — 상품명/판매자상품코드/
    현재가(Naver 실제가)/수정가(PriceHub 최근 조회값)/가격변동상태/판매상태 등 전부 포함.
    5분 캐시(force_refresh=True면 무시하고 새로 조회, 화면에 "새로고침" 버튼용).
    """
    cache_key = f'card-controltower:cards:{store}'
    if not force_refresh:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    def _call(token):
        url = f'{settings.CARD_CONTROLTOWER_BASE_URL}/api/cards'
        resp = requests.get(
            url,
            headers={'Authorization': f'Bearer {token}'},
            timeout=30,
        )
        return resp

    token = _get_token(store)
    try:
        resp = _call(token)
        if resp.status_code == 401:
            # 캐시된 토큰이 만료/무효 — 한 번만 재로그인 후 재시도.
            token = _get_token(store, force_refresh=True)
            resp = _call(token)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        raise CardControltowerAPIError(f'card-controltower 카드 목록 조회 실패: {store} ({e})') from e

    cache.set(cache_key, data, _CARDS_CACHE_TTL)
    return data


def fetch_all_store_cards(force_refresh=False):
    """설정된 전 매장(busan/gwangju)의 카드 목록을 {store: [...]} 형태로 한 번에 반환."""
    return {
        store: fetch_store_cards(store, force_refresh=force_refresh)
        for store in settings.CARD_CONTROLTOWER_STORES
    }


def sale_status_index():
    """
    sellerProductCode → {store: bool(판매중)} 인덱스. 카드 목록/상세 화면에 "부산/광주
    판매중" 배지를 다는 용도 — card-controltower 연동이 실패해도 조용히 빈 dict를 반환해
    배지만 안 뜨고 나머지 화면(PriceHub 자체 기능)은 그대로 동작하게 한다.
    """
    try:
        all_cards = fetch_all_store_cards()
    except CardControltowerAPIError:
        return {}

    index = {}
    for store, cards in all_cards.items():
        for c in cards:
            code = c.get('sellerProductCode')
            if not code:
                continue
            index.setdefault(code, {})[store] = c.get('naverSaleStatus') == 'SALE'
    return index
