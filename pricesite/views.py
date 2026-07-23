"""
pricesite/views.py

일반 사용자용 가격 검색 사이트 — 완전 공개(로그인 불필요), 읽기 전용.
관리자 대시보드(pricehub 앱)와 같은 DB의 카드/가격 데이터를 보여주기만
하고, 판매가 설정 등 쓰기 기능은 전혀 없다(그래서 공개해도 안전함).

추후 별도 프로젝트/도메인으로 분리할 것을 염두에 두고 있어서, pricehub와의
결합은 최소화한다 — 모델과 순수 조회용 헬퍼(차트 데이터 계산 등)만
재사용하고, 쓰기 로직이 있는 뷰/폼은 참조하지 않는다.
"""
from django.db.models import Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from pricehub.models import (
    Card, CardPrice, Expansion,
    DigimonCard, DigimonCardPrice, DigimonExpansion,
    JapanCard, JapanCardPrice, JapanExpansion,
    OnePieceCard, OnePieceCardPrice, OnePieceExpansion,
)
from pricehub.utils import safe_json_dumps
from pricehub.views import (
    _PRICE_HISTORY_RANGE_DAYS,
    _calc_stats,
    _jp_price_history_data,
    _parse_market_items,
    _price_history_data,
)

GAME_CONFIG = {
    'pokemon_kr': {
        'label': '포켓몬 한글판',
        'expansion_model': Expansion,
        'card_model': Card,
        'price_model': CardPrice,
        'is_japan': False,
    },
    'pokemon_jp': {
        'label': '포켓몬 일본판',
        'expansion_model': JapanExpansion,
        'card_model': JapanCard,
        'price_model': JapanCardPrice,
        'is_japan': True,
    },
    'onepiece_kr': {
        'label': '원피스 한글판',
        'expansion_model': OnePieceExpansion,
        'card_model': OnePieceCard,
        'price_model': OnePieceCardPrice,
        'is_japan': False,
    },
    'digimon_kr': {
        'label': '디지몬 한글판',
        'expansion_model': DigimonExpansion,
        'card_model': DigimonCard,
        'price_model': DigimonCardPrice,
        'is_japan': False,
    },
}


def _cfg(game_key):
    cfg = GAME_CONFIG.get(game_key)
    if cfg is None:
        raise Http404('알 수 없는 게임입니다.')
    return cfg


@require_GET
def home(request):
    return render(request, 'pricesite/home.html', {'games': GAME_CONFIG})


@require_GET
def expansion_list(request, game_key):
    cfg = _cfg(game_key)
    expansions = (
        cfg['expansion_model'].objects
        .annotate(card_count=Count('cards', distinct=True))
        .order_by('-release_date', '-created_at')
    )
    return render(request, 'pricesite/expansion_list.html', {
        'game_key': game_key,
        'label': cfg['label'],
        'expansions': expansions,
    })


@require_GET
def card_list(request, game_key, code):
    cfg = _cfg(game_key)
    expansion = get_object_or_404(cfg['expansion_model'], code=code)
    card_model = cfg['card_model']

    cards_qs = card_model.objects.filter(expansion=expansion).order_by('card_number')

    q = (request.GET.get('q') or '').strip()
    if q:
        cards_qs = cards_qs.filter(Q(name__icontains=q) | Q(card_number__icontains=q))

    all_rarities = list(
        card_model.objects.filter(expansion=expansion)
        .exclude(rarity='').values_list('rarity', flat=True)
        .distinct().order_by('rarity')
    )
    selected_rarities = request.GET.getlist('rarities')
    if selected_rarities:
        cards_qs = cards_qs.filter(rarity__in=selected_rarities)

    per_page = 100
    total_count = cards_qs.count()
    page = max(1, int(request.GET.get('page', 1) or 1))
    total_pages = max(1, -(-total_count // per_page))
    page = min(page, total_pages)
    offset = (page - 1) * per_page
    cards = list(cards_qs[offset:offset + per_page])

    _half = 3
    _start = max(1, page - _half)
    _end = min(total_pages, page + _half)
    if _end - _start < 6:
        if _start == 1:
            _end = min(total_pages, _start + 6)
        else:
            _start = max(1, _end - 6)
    page_range = list(range(_start, _end + 1))

    return render(request, 'pricesite/card_list.html', {
        'game_key': game_key,
        'label': cfg['label'],
        'is_japan': cfg['is_japan'],
        'expansion': expansion,
        'cards': cards,
        'q': q,
        'all_rarities': all_rarities,
        'selected_rarities': selected_rarities,
        'total_count': total_count,
        'page': page,
        'total_pages': total_pages,
        'page_range': page_range,
    })


@require_GET
def card_detail(request, game_key, pk):
    cfg = _cfg(game_key)
    card = get_object_or_404(cfg['card_model'].objects.select_related('expansion'), pk=pk)

    ctx = {
        'game_key': game_key,
        'label': cfg['label'],
        'card': card,
        'is_japan': cfg['is_japan'],
    }

    if cfg['is_japan']:
        latest_prices = {}
        for price in card.prices.order_by('-collected_at'):
            key = f'{price.source}_{price.condition}'
            if key not in latest_prices:
                latest_prices[key] = price
        price_values = [int(p.price) for p in latest_prices.values()]
        ctx.update({
            'latest_prices': latest_prices,
            'stats': _calc_stats(price_values),
            'price_history_week_json': safe_json_dumps(
                _jp_price_history_data(card, days=7), ensure_ascii=False
            ),
        })
    else:
        latest_price_obj = card.prices.order_by('-collected_at').first()
        market_items, stats = _parse_market_items(latest_price_obj)
        ctx.update({
            'market_items': market_items,
            'market_items_json': safe_json_dumps(market_items, ensure_ascii=False),
            'stats': stats,
            'price_history_week_json': safe_json_dumps(
                _price_history_data(card, card.prices, days=7), ensure_ascii=False
            ),
        })

    return render(request, 'pricesite/card_detail.html', ctx)


@require_GET
def price_history(request, game_key, pk):
    """가격 변화 그래프 기간(1주/1개월/1년) 전환용 AJAX 엔드포인트."""
    cfg = _cfg(game_key)
    card = get_object_or_404(cfg['card_model'], pk=pk)
    range_key = request.GET.get('range', 'month')
    days = _PRICE_HISTORY_RANGE_DAYS.get(range_key, 30)

    if cfg['is_japan']:
        history = _jp_price_history_data(card, days=days)
    else:
        history = _price_history_data(card, card.prices, days=days)

    return JsonResponse({'range': range_key, 'history': history})
