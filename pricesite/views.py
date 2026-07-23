"""
pricesite/views.py

일반 사용자용 가격 검색 사이트 — 완전 공개(로그인 불필요), 읽기 전용.
pricehub의 DB를 직접 참조하지 않는다 — 대신:

  - 확장팩/카드 카탈로그(이름·레어도·이미지 등 정적 메타데이터)는 로컬 DB
    캐시(`pricesite.models`)를 읽는다. 이 캐시는 `sync_catalog` 커맨드가
    pricehub API를 통해 주기적으로 채운다. 검색/필터/페이지네이션을 빠르게
    처리하기 위함이지, DB를 공유하기 위함이 아니다 — 값은 전부 API를 거쳐
    들어온다.
  - 가격 정보(판매처별 분포, 가격 이력)는 매일 갱신되는 핵심 데이터라 로컬에
    저장하지 않고, 카드 상세 페이지에서 매 요청마다 pricehub API를 실시간
    호출해서 보여준다(`pricesite.api_client`).

추후 별도 프로젝트/도메인으로 분리할 것을 염두에 두고 있어서, pricehub와의
결합은 REST API 하나로 최소화한다 — 이 파일은 pricehub.models나
pricehub.views를 import하지 않는다.
"""
import json

from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from .api_client import PricehubAPIError, fetch_price_history, fetch_price_snapshot
from .models import Card, Expansion

GAME_CONFIG = {
    'pokemon_kr': {'label': '포켓몬 한글판', 'is_japan': False},
    'pokemon_jp': {'label': '포켓몬 일본판', 'is_japan': True},
    'onepiece_kr': {'label': '원피스 한글판', 'is_japan': False},
    'digimon_kr': {'label': '디지몬 한글판', 'is_japan': False},
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
    expansions = Expansion.objects.filter(game_type=game_key).order_by('-release_date')
    return render(request, 'pricesite/expansion_list.html', {
        'game_key': game_key,
        'label': cfg['label'],
        'expansions': expansions,
    })


@require_GET
def card_list(request, game_key, code):
    cfg = _cfg(game_key)
    expansion = get_object_or_404(Expansion, game_type=game_key, code=code)

    cards_qs = Card.objects.filter(expansion=expansion).order_by('card_number')

    q = (request.GET.get('q') or '').strip()
    if q:
        cards_qs = cards_qs.filter(Q(name__icontains=q) | Q(card_number__icontains=q))

    all_rarities = list(
        Card.objects.filter(expansion=expansion)
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
    card = get_object_or_404(
        Card.objects.select_related('expansion'), game_type=game_key, pk=pk
    )

    try:
        snapshot = fetch_price_snapshot(game_key, card.source_id)
        history = fetch_price_history(game_key, card.source_id, 'week')
        api_error = None
    except PricehubAPIError:
        snapshot = None
        history = {'history': []}
        api_error = '가격 정보를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.'

    ctx = {
        'game_key': game_key,
        'label': cfg['label'],
        'card': card,
        'is_japan': cfg['is_japan'],
        'api_error': api_error,
        'price_history_week_json': json_dumps(history.get('history', [])),
    }

    if cfg['is_japan']:
        ctx.update({
            'latest_prices': snapshot['latest_prices'] if snapshot else [],
            'stats': snapshot['stats'] if snapshot else {},
        })
    else:
        market_items = snapshot['market_items'] if snapshot else []
        ctx.update({
            'market_items': market_items,
            'market_items_json': json_dumps(market_items),
            'stats': snapshot['stats'] if snapshot else {},
        })

    return render(request, 'pricesite/card_detail.html', ctx)


@require_GET
def price_history(request, game_key, pk):
    """가격 변화 그래프 기간(1주/1개월/1년) 전환용 AJAX 엔드포인트 — pricehub API 실시간 프록시."""
    _cfg(game_key)  # 알 수 없는 게임이면 404
    card = get_object_or_404(Card, game_type=game_key, pk=pk)
    range_key = request.GET.get('range', 'month')

    try:
        data = fetch_price_history(game_key, card.source_id, range_key)
    except PricehubAPIError:
        return JsonResponse({'range': range_key, 'history': []})

    return JsonResponse(data)


def json_dumps(value):
    return json.dumps(value, ensure_ascii=False)
