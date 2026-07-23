"""
pricesite/api_client.py

pricehub REST API를 호출하는 얇은 클라이언트. pricesite는 이제 pricehub의
모델을 직접 import하지 않고(=DB를 공유하지 않고) 전부 이 모듈을 통해서만
데이터를 받아온다 — 나중에 pricesite가 별도 프로젝트/도메인으로 분리돼도
PRICEHUB_API_BASE_URL만 실제 도메인으로 바꾸면 그대로 동작한다.

인증: 서버 간 통신이라 Api-Key를 서버(pricesite 백엔드)에서만 보관하고
쓴다 — 브라우저(공개 사용자)에는 절대 노출되지 않는다.
"""
import requests
from django.conf import settings
from django.core.cache import cache

_GAME_API_PATH = {
    'pokemon_kr': 'pokemon/kr',
    'pokemon_jp': 'pokemon/jp',
    'onepiece_kr': 'onepiece/kr',
    'digimon_kr': 'digimon/kr',
}

# 가격은 하루 1번만 갱신되므로, 같은 카드를 짧은 시간 안에 여러 번 조회해도
# (트래픽 몰림·봇 등) pricehub API/DB를 매번 다시 두드리지 않도록 짧게
# 캐시한다. DB에 영구 저장하는 게 아니라 TTL이 지나면 자동으로 다시
# pricehub를 호출하므로 "가격은 캐시하지 않고 실시간으로" 원칙과 어긋나지
# 않는다 — 부하 방지용 완충일 뿐, 하루 단위로 보면 항상 최신 값을 반영함.
_PRICE_CACHE_TTL = 600  # 10분


class PricehubAPIError(Exception):
    """pricehub API 호출 실패 (네트워크 오류, 5xx, 타임아웃 등)"""


def _get(path, params=None, timeout=5):
    url = f'{settings.PRICEHUB_API_BASE_URL}{path}'
    headers = {'Authorization': f'Api-Key {settings.PRICEHUB_API_KEY}'}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        raise PricehubAPIError(f'pricehub API 호출 실패: {url} ({e})') from e


def fetch_expansions(game_key):
    """확장팩 목록 (카탈로그 동기화용)"""
    path = _GAME_API_PATH[game_key]
    return _get(f'/api/{path}/expansions/', timeout=30)


def fetch_cards(game_key, expansion_code):
    """
    확장팩별 카드 목록 (카탈로그 동기화용). 사용자 요청이 아니라 백그라운드
    동기화라 응답 속도보다 완주가 중요함 — 카드 수가 많은 확장팩은 카드당
    가격 인덱스 조회가 누적돼 수십 초 걸릴 수 있어 타임아웃을 넉넉히 잡는다.
    """
    path = _GAME_API_PATH[game_key]
    return _get(f'/api/{path}/expansions/{expansion_code}/cards/', timeout=60)


def fetch_price_snapshot(game_key, source_id):
    """
    카드 최신 가격 스냅샷 — 한글판은 market_items(판매처별 분포),
    일본판은 latest_prices(출처×등급별 최신가). 카드 상세 페이지 방문마다
    호출되므로 짧게 캐시해서(_PRICE_CACHE_TTL) 부하를 줄인다.
    """
    cache_key = f'pricesite:price-snapshot:{game_key}:{source_id}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    path = _GAME_API_PATH[game_key]
    data = _get(f'/api/{path}/cards/{source_id}/price-snapshot/')
    cache.set(cache_key, data, _PRICE_CACHE_TTL)
    return data


def fetch_price_history(game_key, source_id, range_key='week'):
    """가격 변화 그래프용 기간별(1주/1개월/1년) 이력 — 짧게 캐시(_PRICE_CACHE_TTL)."""
    cache_key = f'pricesite:price-history:{game_key}:{source_id}:{range_key}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    path = _GAME_API_PATH[game_key]
    data = _get(f'/api/{path}/cards/{source_id}/price-history/', params={'range': range_key})
    cache.set(cache_key, data, _PRICE_CACHE_TTL)
    return data
