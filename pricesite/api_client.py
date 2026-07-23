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

_GAME_API_PATH = {
    'pokemon_kr': 'pokemon/kr',
    'pokemon_jp': 'pokemon/jp',
    'onepiece_kr': 'onepiece/kr',
    'digimon_kr': 'digimon/kr',
}


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
    return _get(f'/api/{path}/expansions/', timeout=15)


def fetch_cards(game_key, expansion_code):
    """확장팩별 카드 목록 (카탈로그 동기화용)"""
    path = _GAME_API_PATH[game_key]
    return _get(f'/api/{path}/expansions/{expansion_code}/cards/', timeout=15)


def fetch_price_snapshot(game_key, source_id):
    """
    카드 최신 가격 스냅샷 — 한글판은 market_items(판매처별 분포),
    일본판은 latest_prices(출처×등급별 최신가). 카드 상세 페이지에서
    매 요청마다 실시간으로 호출한다(로컬에 캐시하지 않음).
    """
    path = _GAME_API_PATH[game_key]
    return _get(f'/api/{path}/cards/{source_id}/price-snapshot/')


def fetch_price_history(game_key, source_id, range_key='week'):
    """가격 변화 그래프용 기간별(1주/1개월/1년) 이력 — 실시간 호출."""
    path = _GAME_API_PATH[game_key]
    return _get(f'/api/{path}/cards/{source_id}/price-history/', params={'range': range_key})
