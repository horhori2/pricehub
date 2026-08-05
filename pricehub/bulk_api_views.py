"""
pricehub/bulk_api_views.py

외부 Electron 앱(Windows 가격 조정 보조 프로그램)용 API Key 인증 엔드포인트.

대시보드의 "일괄 판매가 설정" 로직(pricehub/views.py의 _bulk_* 함수들)은 이미
request.user에 의존하지 않는 순수 (request, cfg_key) -> JsonResponse 함수라서,
세션 로그인 대신 API Key 인증을 씌운 얇은 래퍼로 그대로 재사용한다. 판정 로직을
JS로 재구현하지 않기 위함 — 두 클라이언트(대시보드/Electron)가 동일한 함수를
호출하므로 동작이 어긋날 수 없다.

카드 1건 실시간 검색·저장(_card_collect_price_view)/검색어 조회
(_card_search_query_view)만 이 파일에 새로 작성했다.

네이버 검색 오픈 API가 종료 수순이라(봇 탐지로 직접 접속도 막힘) 자동 수집이
더 이상 불가능해졌다. 그래서 _card_collect_price_view는 이제 작업자가 네이버쇼핑
검색 결과 페이지를 직접 열어 Ctrl+A로 복사한 텍스트를 Electron 쪽에서 파싱한
{title, mallName, lprice} 리스트를 받아, 기존 filter_*_items() 함수(레어도/판매처
제외 등 판정 로직 그대로)에 그대로 넣어 매칭시킨다 — 검색 자체만 사람이 하고
판정/저장 로직은 하나도 새로 만들지 않는다. items가 없는 요청은 기존 라이브
검색 경로로 폴백(오픈 API가 살아있다면 계속 동작).
"""
from django.shortcuts import get_object_or_404
from django.urls import path
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from .authentication import APIKeyAuthentication
from .permissions import HasAPIKey
from .models import Card, CardPrice, OnePieceCard, OnePieceCardPrice, DigimonCard, DigimonCardPrice
from .utils import (
    get_all_prices_for_card, get_onepiece_all_prices, get_digimon_all_prices,
    filter_pokemon_items, filter_onepiece_items, filter_digimon_items,
    generate_pokemon_search_query, generate_onepiece_search_query, generate_digimon_search_query,
)
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


def _digimon_rbk01_marker_required(card):
    """
    RBK-01(라이징 윈드)은 재록 확장팩이라 원본 카드번호와 그대로 겹친다
    (원본/RBK-01 둘 다 패러렐로 존재하는 경우가 대부분). _digimon_item_is_valid의
    rbk01_marker_required 파라미터 참고.
    """
    if card.expansion.code == 'RBK-01':
        return True
    if DigimonCard.objects.filter(card_number=card.card_number, expansion__code='RBK-01').exclude(pk=card.pk).exists():
        return False
    return None


def _digimon_lmk_marker_required(card):
    """
    LMK-1.0/LMK-2.0(스페셜 리미티드 카드 팩)도 RBK-01과 같은 유형의 재록
    확장팩 — 원본 카드번호와 그대로 겹친다. _digimon_item_is_valid의
    lmk_marker_required 파라미터 참고.

    카드번호 자체가 'LM-'로 시작하는 카드(예: LM-020)는 카드번호 매칭만으로
    제목에 항상 "LM"이 들어가 있어 검사가 트리비얼해지므로 None(검사 안 함)
    으로 고정한다.
    """
    if card.card_number.startswith('LM-'):
        return None
    if card.expansion.code in ('LMK-1.0', 'LMK-2.0'):
        return True
    if DigimonCard.objects.filter(
        card_number=card.card_number, expansion__code__in=('LMK-1.0', 'LMK-2.0'),
    ).exclude(pk=card.pk).exists():
        return False
    return None


def _collect_digimon(card):
    return get_digimon_all_prices(
        card_name=card.name,
        card_number=card.card_number,
        is_parallel=card.is_parallel,
        is_scarce=card.is_scarce,
        is_special=card.is_special,
        rbk01_marker_required=_digimon_rbk01_marker_required(card),
        lmk_marker_required=_digimon_lmk_marker_required(card),
    )


# cfg_key -> (카드 모델, 가격 히스토리 모델, 검색 함수)
_COLLECT_CONFIG = {
    'pokemon_kr':  (Card, CardPrice, _collect_pokemon),
    'onepiece_kr': (OnePieceCard, OnePieceCardPrice, _collect_onepiece),
    'digimon_kr':  (DigimonCard, DigimonCardPrice, _collect_digimon),
}

# cfg_key -> 작업자가 붙여넣은 페이지에서 파싱한 items에 기존 필터 로직을 그대로 적용
_FILTER_CONFIG = {
    'pokemon_kr':  lambda items, card: filter_pokemon_items(items, card.name, card.rarity, card.is_teukil),
    'onepiece_kr': lambda items, card: filter_onepiece_items(items, card.name, card.rarity, card.expansion.name, card.card_number),
    'digimon_kr':  lambda items, card: filter_digimon_items(
        items, card.card_number, card.is_parallel, card.is_scarce, card.is_special,
        rbk01_marker_required=_digimon_rbk01_marker_required(card),
        lmk_marker_required=_digimon_lmk_marker_required(card),
    ),
}

# cfg_key -> 카드 검색어 생성 (기존 generate_*_search_query 재사용)
_SEARCH_QUERY_CONFIG = {
    'pokemon_kr':  lambda card: generate_pokemon_search_query(card.name, card.rarity, card.expansion.name),
    'onepiece_kr': lambda card: generate_onepiece_search_query(card.name, card.rarity, card.expansion.name, card.card_number, card.shop_product_code),
    'digimon_kr':  lambda card: generate_digimon_search_query(card.name, card.card_number, card.is_parallel, card.is_scarce, card.is_special),
}


def _clean_supplied_items(raw_items):
    """Electron이 붙여넣은 텍스트에서 파싱해 보낸 항목을 raw_data 형태로 정리."""
    cleaned = []
    for item in raw_items or []:
        mall = (item.get('mallName') or '').strip()
        title = (item.get('title') or '').strip()
        try:
            price = float(item.get('lprice') or 0)
        except (TypeError, ValueError):
            price = 0
        if mall and title and price > 0:
            cleaned.append({'title': title, 'mallName': mall, 'lprice': price})
    return cleaned


def _card_collect_price_view(request, cfg_key, pk):
    """
    카드 1건 가격 매칭 → CardPrice 저장 + latest_raw_data/latest_market_price 갱신.

    request.data['items']가 있으면(작업자가 네이버쇼핑 페이지를 직접 열어 복사한
    텍스트를 Electron이 파싱한 결과) 라이브 검색 없이 그 항목들을 기존
    filter_*_items()에 그대로 넣어 매칭한다. items가 없으면 기존 라이브 검색
    경로로 폴백한다(오픈 API가 아직 동작하는 동안은 계속 유효).
    request.data['dry_run']이 true면 매칭 결과만 계산하고 저장하지 않는다 —
    작업자가 저장 전에 미리 확인하는 용도.
    """
    card_model, price_model, search_fn = _COLLECT_CONFIG[cfg_key]
    card = get_object_or_404(card_model.objects.select_related('expansion'), pk=pk)

    supplied_items = request.data.get('items')
    dry_run = bool(request.data.get('dry_run'))

    if supplied_items is not None:
        cleaned = _clean_supplied_items(supplied_items)
        general_price, valid_count, general_mall, valid_items = _FILTER_CONFIG[cfg_key](cleaned, card)
        search_query = _SEARCH_QUERY_CONFIG[cfg_key](card)
    else:
        result = search_fn(card)
        general_price, valid_count, general_mall = result['general_price']
        valid_items = result['valid_items']
        search_query = result['search_query']

    if general_price is not None and general_mall and not dry_run:
        price_model.objects.create(
            card=card, price=int(general_price), source=general_mall, raw_data=valid_items,
        )
        card.latest_raw_data = valid_items
        card.latest_market_price = int(general_price)
        card.save(update_fields=['latest_raw_data', 'latest_market_price'])

    return Response({
        'search_query':  search_query,
        'general_price': int(general_price) if general_price else None,
        'mall':           general_mall,
        'valid_count':    valid_count,
        'valid_items':    valid_items,
        'saved':          bool(general_price and general_mall and not dry_run),
        'card': {
            'id':                  card.id,
            'selling_price':       int(card.selling_price or 0),
            'modified_price':      int(card.modified_price or 0),
            'latest_market_price': card.latest_market_price,
        },
    })


def _card_search_query_view(request, cfg_key, pk):
    """카드 1건의 네이버쇼핑 검색어만 반환 — 작업자가 직접 열어볼 링크를 만들기 위함."""
    card_model, _price_model, _search_fn = _COLLECT_CONFIG[cfg_key]
    card = get_object_or_404(card_model.objects.select_related('expansion'), pk=pk)
    return Response({'search_query': _SEARCH_QUERY_CONFIG[cfg_key](card)})


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
        path(
            'bulk-price/search-query/<int:pk>/',
            _bulk_api_view(_card_search_query_view, cfg_key, ['GET']),
            name=f'{cfg_key}-bulk-search-query',
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
