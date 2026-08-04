"""
pricehub/bulk_api_views.py

외부 Electron 앱(Windows 가격 조정 보조 프로그램)용 API Key 인증 엔드포인트.

대시보드의 "일괄 판매가 설정" 로직(pricehub/views.py의 _bulk_* 함수들)은 이미
request.user에 의존하지 않는 순수 (request, cfg_key) -> JsonResponse 함수라서,
세션 로그인 대신 API Key 인증을 씌운 얇은 래퍼로 그대로 재사용한다. 판정 로직을
JS로 재구현하지 않기 위함 — 두 클라이언트(대시보드/Electron)가 동일한 함수를
호출하므로 동작이 어긋날 수 없다.

카드 1건 실시간 검색·저장(_card_collect_price_view)만 이 파일에 새로 작성했다.
scripts/collect/collect_all_prices.py가 확장팩 전체를 순회하며 하던 일을 카드
1건 단위로 쪼갠 것 — Electron 쪽에서 카드 목록을 순회하며 한 장씩 호출한다.
"""
from django.shortcuts import get_object_or_404
from django.urls import path
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from .authentication import APIKeyAuthentication
from .permissions import HasAPIKey
from .models import Card, CardPrice, OnePieceCard, OnePieceCardPrice, DigimonCard, DigimonCardPrice
from .utils import get_all_prices_for_card, get_onepiece_all_prices, get_digimon_all_prices
from .views import (
    _bulk_shop_stats_api,
    _bulk_run_view,
    _bulk_inline_cards_view,
    _bulk_approve_view,
    _bulk_edit_view,
)


# ════════════════════════════════════════════════════════════════
# 카드 1건 실시간 검색·저장
# ════════════════════════════════════════════════════════════════

def _collect_pokemon(card):
    return get_all_prices_for_card(
        card_name=card.name,
        rarity=card.rarity,
        expansion_name=card.expansion.name,
        is_teukil=card.is_teukil,
    )


def _collect_onepiece(card):
    return get_onepiece_all_prices(
        card_name=card.name,
        rarity=card.rarity,
        expansion_name=card.expansion.name,
        card_number=card.card_number,
        shop_product_code=card.shop_product_code,
    )


def _collect_digimon(card):
    return get_digimon_all_prices(
        card_name=card.name,
        card_number=card.card_number,
        is_parallel=card.is_parallel,
        is_scarce=card.is_scarce,
        is_special=card.is_special,
    )


# cfg_key -> (카드 모델, 가격 히스토리 모델, 검색 함수)
_COLLECT_CONFIG = {
    'pokemon_kr':  (Card, CardPrice, _collect_pokemon),
    'onepiece_kr': (OnePieceCard, OnePieceCardPrice, _collect_onepiece),
    'digimon_kr':  (DigimonCard, DigimonCardPrice, _collect_digimon),
}


def _card_collect_price_view(request, cfg_key, pk):
    """
    카드 1건 네이버쇼핑 검색 → CardPrice 저장 + latest_raw_data/latest_market_price 갱신.
    scripts/collect/collect_all_prices.py의 확장팩 순회 로직과 동일한 저장 방식을
    카드 1건 단위로 수행한다(gunicorn 타임아웃을 피하기 위해 Electron이 카드별로 호출).
    """
    card_model, price_model, search_fn = _COLLECT_CONFIG[cfg_key]
    card = get_object_or_404(card_model.objects.select_related('expansion'), pk=pk)

    result = search_fn(card)
    general_price, valid_count, general_mall = result['general_price']
    valid_items = result['valid_items']

    if general_price is not None and general_mall:
        price_model.objects.create(
            card=card, price=int(general_price), source=general_mall, raw_data=valid_items,
        )
        card.latest_raw_data = valid_items
        card.latest_market_price = int(general_price)
        card.save(update_fields=['latest_raw_data', 'latest_market_price'])

    return Response({
        'search_query':  result['search_query'],
        'general_price': int(general_price) if general_price else None,
        'mall':           general_mall,
        'valid_count':    valid_count,
        'card': {
            'id':                  card.id,
            'selling_price':       int(card.selling_price or 0),
            'modified_price':      int(card.modified_price or 0),
            'latest_market_price': card.latest_market_price,
        },
    })


# ════════════════════════════════════════════════════════════════
# 기존 대시보드 bulk 함수를 API Key 인증으로 감싸는 팩토리
# ════════════════════════════════════════════════════════════════

def _bulk_api_view(handler, cfg_key, methods):
    """handler(request, cfg_key, **kwargs)를 API Key 인증 DRF 뷰로 감싼다."""
    @api_view(methods)
    @authentication_classes([APIKeyAuthentication])
    @permission_classes([HasAPIKey])
    def view(request, *args, **kwargs):
        return handler(request, cfg_key, *args, **kwargs)
    return view


# 대시보드 bulk 함수 재사용 — slug: (handler, methods)
_BULK_HANDLERS = {
    'stats':        (_bulk_shop_stats_api, ['GET']),
    'run':          (_bulk_run_view, ['POST']),
    'inline-cards': (_bulk_inline_cards_view, ['POST']),
    'approve':      (_bulk_approve_view, ['POST']),
    'edit':         (_bulk_edit_view, ['POST']),
}


def bulk_price_api_urls(cfg_key):
    """
    게임 하나(cfg_key)에 대한 bulk-price API 경로 목록 생성.
    api_urls.py에서 pokemon_kr/onepiece_kr/digimon_kr 각각에 대해 호출해 붙여쓴다.
    """
    patterns = [
        path(
            'bulk-price/collect-card/<int:pk>/',
            _bulk_api_view(_card_collect_price_view, cfg_key, ['POST']),
            name=f'{cfg_key}-bulk-collect-card',
        ),
    ]
    for slug, (handler, methods) in _BULK_HANDLERS.items():
        patterns.append(
            path(
                f'bulk-price/{slug}/',
                _bulk_api_view(handler, cfg_key, methods),
                name=f'{cfg_key}-bulk-{slug}',
            )
        )
    return patterns
