"""
pricehub/dashboard_views.py

판매가 관리 대시보드.
- 홈: 게임(포켓몬/원피스/디지몬) × 언어(한글판/일본판) 선택
- 각 카테고리별: 확장팩 목록 → 카드 목록 → 카드 상세 + 판매가 설정
"""
import json
import re

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import Count, Prefetch, OuterRef, Subquery, Q
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test

from .models import (
    Expansion, Card, CardPrice,
    OnePieceExpansion, OnePieceCard, OnePieceCardPrice,
    JapanExpansion, JapanCard, JapanCardPrice,
)

from django.utils import timezone
from datetime import timedelta


OUR_SHOPS = ['화성스토어-TCG-', '카드 베이스']


# ── 권한 ──────────────────────────────────────────────────────
def is_staff(user):
    return user.is_active and user.is_staff

staff_required = user_passes_test(is_staff, login_url='/dashboard/login/')


# ── 로그인/로그아웃 ───────────────────────────────────────────
def dashboard_login(request):
    error = None
    if request.method == 'POST':
        user = authenticate(request,
                            username=request.POST.get('username'),
                            password=request.POST.get('password'))
        if user and user.is_staff:
            login(request, user)
            return redirect('/dashboard/')
        error = '아이디 또는 비밀번호가 올바르지 않습니다.'
    return render(request, 'dashboard/login.html', {'error': error})


def dashboard_logout(request):
    logout(request)
    return redirect('/dashboard/login/')


# ── 홈 (카테고리 선택) ────────────────────────────────────────
@staff_required
def home(request):
    """
    게임 × 언어 카테고리 선택 화면.
    각 카테고리의 미설정 카드 수를 보여줌.
    """
    categories = [
        {
            'game': '포켓몬',
            'game_key': 'pokemon',
            'icon': '🎴',
            'regions': [
                {
                    'label': '한글판',
                    'key': 'kr',
                    'url': '/dashboard/pokemon/kr/expansions/',
                    'total': Card.objects.count(),
                    'unpriced': Card.objects.filter(selling_price=0).count(),
                },
                {
                    'label': '일본판',
                    'key': 'jp',
                    'url': '/dashboard/pokemon/jp/expansions/',
                    'total': JapanCard.objects.count(),
                    'unpriced': JapanCard.objects.filter(selling_price=0).count(),
                },
            ],
        },
        {
            'game': '원피스',
            'game_key': 'onepiece',
            'icon': '⚓',
            'regions': [
                {
                    'label': '한글판',
                    'key': 'kr',
                    'url': '/dashboard/onepiece/kr/expansions/',
                    'total': OnePieceCard.objects.count(),
                    'unpriced': OnePieceCard.objects.filter(selling_price=0).count(),
                },
            ],
        },
        {
            'game': '디지몬',
            'game_key': 'digimon',
            'icon': '🦕',
            'regions': [],
            'coming_soon': True,
        },
    ]
    return render(request, 'dashboard/home.html', {'categories': categories})


# ════════════════════════════════════════════════════════════════
# 포켓몬 한글판
# ════════════════════════════════════════════════════════════════

@staff_required
def pokemon_kr_expansion_list(request):
    expansions = list(Expansion.objects.order_by('-release_date', '-created_at'))
    for e in expansions:
        e.card_count = e.cards.count()
        e.unpriced_count = e.cards.filter(selling_price=0).count()
    total_cards = sum(e.card_count for e in expansions)
    total_unpriced = sum(e.unpriced_count for e in expansions)
    return render(request, 'dashboard/expansion_list.html', {
        'expansions': expansions,
        'total_cards': total_cards,
        'total_unpriced': total_unpriced,
        'breadcrumb': [('홈', '/dashboard/'), ('포켓몬 한글판', None)],
        'base_url': '/dashboard/pokemon/kr',
        'title': '포켓몬 한글판',
        'bulk_price_url': '/dashboard/pokemon/kr/bulk-price/',
        'card_search_url': '/dashboard/pokemon/kr/cards/search/',
        'card_detail_base_url': '/dashboard/pokemon/kr/cards/',
        'bulk_issues_url': '/dashboard/pokemon/kr/bulk-price/issues/',
        'reset_prices_url_prefix': '/dashboard/pokemon/kr/expansions/',
        'reset_all_url': '/dashboard/pokemon/kr/reset-all-prices/',
    })


@staff_required
def pokemon_kr_card_list(request, code):
    expansion = get_object_or_404(Expansion, code=code)
    latest_price_qs = CardPrice.objects.filter(card=OuterRef('pk')).order_by('-collected_at')
    cards = (
        Card.objects.filter(expansion=expansion)
        .annotate(
            latest_market_price=Subquery(latest_price_qs.values('price')[:1]),
            latest_collected_at=Subquery(latest_price_qs.values('collected_at')[:1]),
        )
        .order_by('card_number')
    )
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'unpriced':
        cards = cards.filter(selling_price=0)
    elif filter_type == 'priced':
        cards = cards.filter(selling_price__gt=0)
    return render(request, 'dashboard/card_list.html', {
        'expansion': expansion,
        'cards': cards,
        'filter_type': filter_type,
        'breadcrumb': [('홈', '/dashboard/'), ('포켓몬 한글판', '/dashboard/pokemon/kr/expansions/'), (expansion.name, None)],
        'detail_base_url': '/dashboard/pokemon/kr/cards',
        'back_url': '/dashboard/pokemon/kr/expansions/',
        'bulk_price_url': f'/dashboard/pokemon/kr/bulk-price/?expansion={expansion.code}',
        'reset_prices_url': f'/dashboard/pokemon/kr/expansions/{expansion.code}/reset-prices/',
    })


@staff_required
def pokemon_kr_card_detail(request, pk):
    card = get_object_or_404(Card.objects.select_related('expansion'), pk=pk)
    latest_price_obj = card.prices.order_by('-collected_at').first()
    market_items, stats = _parse_market_items(latest_price_obj)
     # 최근 1주일 가격 이력
    one_week_ago = timezone.now() - timedelta(days=7)
    price_history_week = list(
        card.prices
        .filter(collected_at__gte=one_week_ago)
        .order_by('collected_at')
        .values('collected_at', 'raw_data')
    )

    return render(request, 'dashboard/card_detail.html', {
        'card': card,
        'card_type': 'pokemon_kr',
        'latest_price_obj': latest_price_obj,
        'market_items': market_items,
        'market_items_json': json.dumps(market_items, ensure_ascii=False),
        'stats': stats,
        'set_price_url': f'/dashboard/pokemon/kr/cards/{pk}/set-price/',
        'back_url': f'/dashboard/pokemon/kr/expansions/{card.expansion.code}/cards/',
        'breadcrumb': [
            ('홈', '/dashboard/'),
            ('포켓몬 한글판', '/dashboard/pokemon/kr/expansions/'),
            (card.expansion.name, f'/dashboard/pokemon/kr/expansions/{card.expansion.code}/cards/'),
            (card.name, None),
        ],
        'price_history_week_json': json.dumps(
            [
                {
                    'date': p['collected_at'].strftime('%m/%d %H:%M'),
                    'raw_data': p['raw_data'] if isinstance(p['raw_data'], list) else [],
                }
                for p in price_history_week
            ],
            ensure_ascii=False
        ),
    })


@staff_required
@require_POST
def pokemon_kr_set_price(request, pk):
    card = get_object_or_404(Card, pk=pk)
    try:
        data = json.loads(request.body)
        price = int(data.get('selling_price', 0))
        if price <= 0:
            return JsonResponse({'error': '올바른 가격을 입력해주세요.'}, status=400)
        card.selling_price = price
        card.save(update_fields=['selling_price'])
        return JsonResponse({'success': True, 'selling_price': price})
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': '잘못된 요청입니다.'}, status=400)
    
@staff_required
def pokemon_kr_card_search(request):
    q = request.GET.get('name', '').strip()
    page_size = min(int(request.GET.get('page_size', 30)), 50)

    if not q:
        return JsonResponse({'results': []})

    cards = Card.objects.filter(name__icontains=q).select_related('expansion').order_by('expansion__release_date', 'card_number')[:page_size]

    results = []
    for card in cards:
        latest = card.prices.first()
        results.append({
            'id': card.id,
            'name': card.name,
            'rarity': card.rarity,
            'card_number': card.card_number,
            'image_url': card.image_url,
            'selling_price': card.selling_price if card.selling_price != 0 else None,
            'latest_price': float(latest.price) if latest else None,
            'expansion': {
                'code': card.expansion.code,
                'name': card.expansion.name,
            }
        })

    return JsonResponse({'results': results})

@staff_required
@require_POST
def pokemon_kr_reset_prices(request, expansion_code):
    count = Card.objects.filter(expansion__code=expansion_code).update(selling_price=0)
    return JsonResponse({'success': True, 'count': count})

@staff_required
@require_POST
def pokemon_kr_reset_all_prices(request):
    count = Card.objects.all().update(selling_price=0)
    return JsonResponse({'success': True, 'count': count})


# ════════════════════════════════════════════════════════════════
# 포켓몬 일본판
# ════════════════════════════════════════════════════════════════

@staff_required
def pokemon_jp_expansion_list(request):
    expansions = list(JapanExpansion.objects.order_by('-release_date', '-created_at'))
    for e in expansions:
        e.card_count = e.cards.count()
        e.unpriced_count = e.cards.filter(selling_price=0).count()
    total_cards = sum(e.card_count for e in expansions)
    total_unpriced = sum(e.unpriced_count for e in expansions)
    return render(request, 'dashboard/expansion_list.html', {
        'expansions': expansions,
        'total_cards': total_cards,
        'total_unpriced': total_unpriced,
        'breadcrumb': [('홈', '/dashboard/'), ('포켓몬 일본판', None)],
        'base_url': '/dashboard/pokemon/jp',
        'title': '포켓몬 일본판',
        'card_search_url': '/dashboard/pokemon/jp/cards/search/',
        'card_detail_base_url': '/dashboard/pokemon/jp/cards/',
    })


@staff_required
def pokemon_jp_card_list(request, code):
    expansion = get_object_or_404(JapanExpansion, code=code)
    latest_price_qs = JapanCardPrice.objects.filter(card=OuterRef('pk')).order_by('-collected_at')
    cards = (
        JapanCard.objects.filter(expansion=expansion)
        .annotate(
            latest_market_price=Subquery(latest_price_qs.values('price')[:1]),
            latest_collected_at=Subquery(latest_price_qs.values('collected_at')[:1]),
        )
        .order_by('card_number')
    )
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'unpriced':
        cards = cards.filter(selling_price=0)
    elif filter_type == 'priced':
        cards = cards.filter(selling_price__gt=0)
    return render(request, 'dashboard/card_list.html', {
        'expansion': expansion,
        'cards': cards,
        'filter_type': filter_type,
        'breadcrumb': [('홈', '/dashboard/'), ('포켓몬 일본판', '/dashboard/pokemon/jp/expansions/'), (expansion.name, None)],
        'detail_base_url': '/dashboard/pokemon/jp/cards',
        'back_url': '/dashboard/pokemon/jp/expansions/',
    })


@staff_required
def pokemon_jp_card_detail(request, pk):
    card = get_object_or_404(JapanCard.objects.select_related('expansion'), pk=pk)

    # 일본판은 source/condition별 최신 가격
    latest_prices = {}
    for price in JapanCardPrice.objects.filter(card=card).order_by('-collected_at'):
        key = f"{price.source}_{price.condition}"
        if key not in latest_prices:
            latest_prices[key] = price

    # 통계용: 모든 최신 가격들
    price_values = [int(p.price) for p in latest_prices.values()]
    stats = _calc_stats(price_values)

    return render(request, 'dashboard/card_detail_jp.html', {
        'card': card,
        'latest_prices': latest_prices,
        'stats': stats,
        'set_price_url': f'/dashboard/pokemon/jp/cards/{pk}/set-price/',
        'back_url': f'/dashboard/pokemon/jp/expansions/{card.expansion.code}/cards/',
        'breadcrumb': [
            ('홈', '/dashboard/'),
            ('포켓몬 일본판', '/dashboard/pokemon/jp/expansions/'),
            (card.expansion.name, f'/dashboard/pokemon/jp/expansions/{card.expansion.code}/cards/'),
            (card.name, None),
        ],
    })


@staff_required
@require_POST
def pokemon_jp_set_price(request, pk):
    return _set_price(JapanCard, pk, request)


# ════════════════════════════════════════════════════════════════
# 원피스 한글판
# ════════════════════════════════════════════════════════════════

@staff_required
def onepiece_kr_expansion_list(request):
    expansions = list(OnePieceExpansion.objects.order_by('-release_date', '-created_at'))
    for e in expansions:
        e.card_count = e.cards.count()
        e.unpriced_count = e.cards.filter(selling_price=0).count()
    total_cards = sum(e.card_count for e in expansions)
    total_unpriced = sum(e.unpriced_count for e in expansions)
    return render(request, 'dashboard/expansion_list.html', {
        'expansions': expansions,
        'total_cards': total_cards,
        'total_unpriced': total_unpriced,
        'breadcrumb': [('홈', '/dashboard/'), ('원피스 한글판', None)],
        'base_url': '/dashboard/onepiece/kr',
        'title': '원피스 한글판',
        'bulk_price_url': '/dashboard/onepiece/kr/bulk-price/',
        'card_search_url': '/dashboard/onepiece/kr/cards/search/',
        'card_detail_base_url': '/dashboard/onepiece/kr/cards/',
        'bulk_issues_url': '/dashboard/onepiece/kr/bulk-price/issues/',
        'reset_prices_url_prefix': '/dashboard/onepiece/kr/expansions/',
        'reset_all_url': '/dashboard/onepiece/kr/reset-all-prices/',
    })


@staff_required
def onepiece_kr_card_list(request, code):
    expansion = get_object_or_404(OnePieceExpansion, code=code)
    latest_price_qs = OnePieceCardPrice.objects.filter(card=OuterRef('pk')).order_by('-collected_at')
    cards = (
        OnePieceCard.objects.filter(expansion=expansion)
        .annotate(
            latest_market_price=Subquery(latest_price_qs.values('price')[:1]),
            latest_collected_at=Subquery(latest_price_qs.values('collected_at')[:1]),
        )
        .order_by('card_number')
    )
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'unpriced':
        cards = cards.filter(selling_price=0)
    elif filter_type == 'priced':
        cards = cards.filter(selling_price__gt=0)
    return render(request, 'dashboard/card_list.html', {
        'expansion': expansion,
        'cards': cards,
        'filter_type': filter_type,
        'breadcrumb': [('홈', '/dashboard/'), ('원피스 한글판', '/dashboard/onepiece/kr/expansions/'), (expansion.name, None)],
        'detail_base_url': '/dashboard/onepiece/kr/cards',
        'back_url': '/dashboard/onepiece/kr/expansions/',
        'bulk_price_url': f'/dashboard/onepiece/kr/bulk-price/?expansion={expansion.code}',
        'reset_prices_url': f'/dashboard/onepiece/kr/expansions/{expansion.code}/reset-prices/',
    })


@staff_required
def onepiece_kr_card_detail(request, pk):
    card = get_object_or_404(OnePieceCard.objects.select_related('expansion'), pk=pk)
    latest_price_obj = card.prices.order_by('-collected_at').first()
    market_items, stats = _parse_market_items(latest_price_obj)

    # 최근 1주일 가격 이력
    one_week_ago = timezone.now() - timedelta(days=7)
    price_history_week = list(
        card.prices
        .filter(collected_at__gte=one_week_ago)
        .order_by('collected_at')
        .values('collected_at', 'raw_data')
    )

    return render(request, 'dashboard/card_detail.html', {
        'card': card,
        'card_type': 'onepiece_kr',
        'latest_price_obj': latest_price_obj,
        'market_items': market_items,
        'market_items_json': json.dumps(market_items, ensure_ascii=False),
        'stats': stats,
        'set_price_url': f'/dashboard/onepiece/kr/cards/{pk}/set-price/',
        'back_url': f'/dashboard/onepiece/kr/expansions/{card.expansion.code}/cards/',
        'price_history_week_json': json.dumps(
            [
                {
                    'date': p['collected_at'].strftime('%m/%d %H:%M'),
                    'raw_data': p['raw_data'] if isinstance(p['raw_data'], list) else [],
                }
                for p in price_history_week
            ],
            ensure_ascii=False
        ),
        'breadcrumb': [
            ('홈', '/dashboard/'),
            ('원피스 한글판', '/dashboard/onepiece/kr/expansions/'),
            (card.expansion.name, f'/dashboard/onepiece/kr/expansions/{card.expansion.code}/cards/'),
            (card.name, None),
        ],
    })

@staff_required
@require_POST
def onepiece_kr_set_price(request, pk):
    return _set_price(OnePieceCard, pk, request)

@staff_required
@require_POST
def onepiece_kr_reset_prices(request, expansion_code):
    count = OnePieceCard.objects.filter(expansion__code=expansion_code).update(selling_price=0)
    return JsonResponse({'success': True, 'count': count})

@staff_required
@require_POST
def onepiece_kr_reset_all_prices(request):
    count = OnePieceCard.objects.all().update(selling_price=0)
    return JsonResponse({'success': True, 'count': count})


# ════════════════════════════════════════════════════════════════
# 공통 헬퍼
# ════════════════════════════════════════════════════════════════

def _parse_market_items(latest_price_obj):
    """CardPrice.raw_data(valid_items 배열)에서 market_items + stats 반환"""
    market_items = []
    if latest_price_obj and latest_price_obj.raw_data:
        raw = latest_price_obj.raw_data
        if isinstance(raw, list):
            market_items = raw
        elif isinstance(raw, dict) and raw:
            market_items = [raw]

    for item in market_items:
        item['clean_title'] = re.sub(r'<[^>]+>', '', item.get('title', ''))
        item['price_int'] = int(float(item.get('lprice', 0)))

    # 우리 샵: OUR_SHOPS 순서 고정, 나머지: 최저가 순
    our_items = []
    for shop in OUR_SHOPS:
        for item in market_items:
            if item.get('mallName') == shop:
                our_items.append(item)
                break  # 같은 샵 중복 방지

    other_items = sorted(
        [i for i in market_items if i.get('mallName') not in OUR_SHOPS],
        key=lambda x: x['price_int']
    )

    market_items = our_items + other_items

    prices = [item['price_int'] for item in market_items if item['price_int'] > 0]
    stats = _calc_stats(prices)
    return market_items, stats


def _calc_stats(prices):
    if not prices:
        return {}
    sorted_p = sorted(prices)
    return {
        'min': sorted_p[0],
        'max': sorted_p[-1],
        'avg': round(sum(sorted_p) / len(sorted_p)),
        'median': sorted_p[len(sorted_p) // 2],
        'count': len(sorted_p),
    }


def _set_price(model_class, pk, request):
    """공통 판매가 저장 (AJAX POST)"""
    obj = get_object_or_404(model_class, pk=pk)
    try:
        data = json.loads(request.body)
        price = int(data.get('selling_price', 0))
        if price < 0:
            return JsonResponse({'success': False, 'error': '올바른 가격을 입력하세요.'})
        obj.selling_price = price if price > 0 else None
        obj.save(update_fields=['selling_price'])
        return JsonResponse({'success': True, 'selling_price': obj.selling_price})
    except (ValueError, TypeError) as e:
        return JsonResponse({'success': False, 'error': str(e)})



# ────────────────────────────────────────────────────────────────
# 1. 일괄 설정 페이지
# GET /dashboard/pokemon/kr/bulk-price/
# ────────────────────────────────────────────────────────────────

@staff_required
def pokemon_kr_bulk_price(request):
    expansion_code = request.GET.get('expansion', '')
    # ← 레어도 필터 추가 (쉼표 구분 복수 선택)
    # rarity_filter = request.GET.get('rarities', '')
    selected_rarities = request.GET.getlist('rarities')

    selected_expansion = None
    if expansion_code:
        selected_expansion = Expansion.objects.filter(code=expansion_code).first()

    mall_names = _collect_mall_names(expansion_code=expansion_code or None)
    expansions = list(Expansion.objects.order_by('-release_date'))
    needs_review = Card.objects.filter(selling_price=0).count()

    # 레어도 목록 (해당 확장팩 or 전체)
    rarity_qs = Card.objects.values_list('rarity', flat=True).distinct().order_by('rarity')
    if expansion_code:
        rarity_qs = rarity_qs.filter(expansion__code=expansion_code)
    all_rarities = list(rarity_qs)

    raw_list = _load_raw_data(
        expansion_code=expansion_code or None,
        rarities=selected_rarities or None,        # ← 추가
    )
    shop_stats, overall_avg = _calc_shop_stats(raw_list)

    return render(request, 'dashboard/bulk_price.html', {
        'mall_names': json.dumps(mall_names),
        'mall_names_display': mall_names,
        'expansions': expansions,
        'needs_review': needs_review,
        'shop_stats_json': json.dumps(shop_stats, ensure_ascii=False),
        'shop_stats': shop_stats,
        'overall_avg': overall_avg,
        'selected_expansion': selected_expansion,
        'expansion_code': expansion_code,
        'all_rarities': all_rarities,              # ← 추가
        'selected_rarities': selected_rarities,    # ← 추가
        'selected_rarities_json': json.dumps(selected_rarities),  # ← 추가
        'breadcrumb': [
            ('홈', '/dashboard/'),
            ('포켓몬 한글판', '/dashboard/pokemon/kr/expansions/'),
            ('일괄 판매가 설정', None),
        ],
        'config': {
        'label': '포켓몬 한글판',
        'expansion_list_url': '/dashboard/pokemon/kr/expansions/',
        'bulk_price_url': '/dashboard/pokemon/kr/bulk-price/',
        'bulk_run_url': '/dashboard/pokemon/kr/bulk-price/run/',
        'bulk_issues_url': '/dashboard/pokemon/kr/bulk-price/issues/',
        'high_rarity_list': "['SAR','CSR','UR','MUR','BWR']",
        },
    })

# ────────────────────────────────────────────────────────────────
# 2. 즉시 실행 API
# POST /dashboard/pokemon/kr/bulk-price/run/
# ────────────────────────────────────────────────────────────────

@staff_required
@require_POST
def pokemon_kr_bulk_run(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': '잘못된 요청입니다.'}, status=400)

    priorities = [p.strip() for p in data.get('priorities', []) if p.strip()]
    expansion_code = data.get('expansion_code', '').strip()
    skip_priced = data.get('skip_priced', False)
    rarities = data.get('rarities', [])
    min_price_floor = int(data.get('min_price', 0) or 0)
    fallback_mode = data.get('fallback_mode', '')  # 'avg', 'max', ''

    if not priorities:
        return JsonResponse({'error': '우선순위를 1개 이상 설정해주세요.'}, status=400)

    cards_qs = Card.objects.select_related('expansion').order_by('expansion__code', 'card_number')
    if expansion_code:
        cards_qs = cards_qs.filter(expansion__code=expansion_code)
    if rarities:
        cards_qs = cards_qs.filter(rarity__in=rarities)

    from django.db.models import Subquery, OuterRef
    latest_price_id_qs = (
        CardPrice.objects
        .filter(card=OuterRef('pk'))
        .exclude(raw_data={})
        .exclude(raw_data=[])
        .order_by('-collected_at')
        .values('id')[:1]
    )
    cards_list = list(cards_qs.annotate(latest_price_id=Subquery(latest_price_id_qs)))

    price_ids = [c.latest_price_id for c in cards_list if c.latest_price_id]
    price_map = {
        cp.id: cp.raw_data
        for cp in CardPrice.objects.filter(id__in=price_ids)
    }

    to_update = []
    skipped = []
    needs_review = []

    for card in cards_list:
        if skip_priced and card.selling_price != 0:
            skipped.append(card.id)
            continue

        raw = price_map.get(card.latest_price_id, [])
        if isinstance(raw, dict):
            raw = [raw]

        # ── 우선순위 매칭 ──
        matched_price = None
        for mall_name in priorities:
            for item in raw:
                if item.get('mallName', '') == mall_name:
                    try:
                        price = int(float(item.get('lprice', 0)))
                        if price > 0:
                            matched_price = price
                    except (ValueError, TypeError):
                        pass
                    break
            if matched_price:
                break

        if matched_price:
            if min_price_floor > 0 and matched_price < min_price_floor:
                matched_price = min_price_floor
            card.selling_price = matched_price
            to_update.append(card)

        else:
            # ── 미매칭 카드: fallback 처리 ──
            fallback_price = None
            if fallback_mode in ('avg', 'max'):
                prices = []
                for item in raw:
                    try:
                        p = int(float(item.get('lprice', 0)))
                        if p > 0:
                            prices.append(p)
                    except (ValueError, TypeError):
                        pass
                if prices:
                    raw_price = (sum(prices) / len(prices)) if fallback_mode == 'avg' else max(prices)
                    fallback_price = round(raw_price / 100) * 100  # 100원 단위 반올림

            if fallback_price:
                if min_price_floor > 0 and fallback_price < min_price_floor:
                    fallback_price = min_price_floor
                card.selling_price = fallback_price
                to_update.append(card)
            else:
                needs_review.append(card.id)

    if to_update:
        Card.objects.bulk_update(to_update, ['selling_price'])

    return JsonResponse({
        'success': True,
        'total': len(cards_list),
        'set_count': len(to_update),
        'skipped_count': len(skipped),
        'needs_review_count': len(needs_review),
        'needs_review_ids': needs_review[:100],
    })


# ────────────────────────────────────────────────────────────────
# 3. 점검 필요 카드 목록
# GET /dashboard/pokemon/kr/bulk-price/issues/
# ────────────────────────────────────────────────────────────────

@staff_required
def pokemon_kr_bulk_issues(request):
    expansion_code = request.GET.get('expansion', '')
    selected_rarities = request.GET.getlist('rarities')

    cards_qs = Card.objects.filter(selling_price=0).select_related('expansion')
    if expansion_code:
        cards_qs = cards_qs.filter(expansion__code=expansion_code)
    cards_qs = cards_qs.order_by('expansion__code', 'card_number')

    # 전체 카드에서 레어도 추출 (bulk_price와 동일)
    rarity_qs = Card.objects.values_list('rarity', flat=True).distinct().order_by('rarity')
    if expansion_code:
        rarity_qs = rarity_qs.filter(expansion__code=expansion_code)
    all_rarities = list(rarity_qs)

    # raw_data
    seen = {}
    for cp in CardPrice.objects.filter(card__in=cards_qs)\
                                .exclude(raw_data={}).exclude(raw_data=[])\
                                .order_by('-collected_at')\
                                .values('card_id', 'raw_data'):
        if cp['card_id'] not in seen:
            seen[cp['card_id']] = cp['raw_data']

    expansions = Expansion.objects.order_by('-release_date')

    return render(request, 'dashboard/bulk_issues.html', {
        'cards': cards_qs,
        'expansions': expansions,
        'expansion_code': expansion_code,
        'total': cards_qs.count(),
        'card_raw_json': json.dumps(seen, ensure_ascii=False),
        'all_rarities': all_rarities,
        'selected_rarities': selected_rarities,
        'selected_rarities_json': json.dumps(selected_rarities),
        'breadcrumb': [
            ('홈', '/dashboard/'),
            ('포켓몬 한글판', '/dashboard/pokemon/kr/expansions/'),
            ('일괄 판매가 설정', '/dashboard/pokemon/kr/bulk-price/'),
            ('2차 판매가 설정', None),
        ],
        'config': {
            'label': '포켓몬 한글판',
            'bulk_price_url': '/dashboard/pokemon/kr/bulk-price/',
            'bulk_issues_url': '/dashboard/pokemon/kr/bulk-price/issues/',
            'set_price_url_prefix': '/dashboard/pokemon/kr/cards/',
            'high_rarity_list': "['SAR','CSR','HR','UR','MUR','BWR']",
        },
    })


# //////////////////////////////// 원피스 한글판 ///////////////////////////////////////


# ────────────────────────────────────────────────────────────────
# 내부 헬퍼
# ────────────────────────────────────────────────────────────────

def _collect_mall_names(expansion_code=None, limit=500):
    qs = CardPrice.objects.exclude(raw_data={}).exclude(raw_data=[])
    if expansion_code:
        qs = qs.filter(card__expansion__code=expansion_code)

    # 카드별 최신 1건 id만 먼저 추출
    seen_cards = {}
    for cp in qs.order_by('-collected_at').values('card_id', 'id'):
        if cp['card_id'] not in seen_cards:
            seen_cards[cp['card_id']] = cp['id']
        if len(seen_cards) >= limit:
            break

    name_count = {}
    for raw in CardPrice.objects.filter(id__in=seen_cards.values()).values_list('raw_data', flat=True):
        if isinstance(raw, list):
            for item in raw:
                name = item.get('mallName', '').strip()
                if name:
                    name_count[name] = name_count.get(name, 0) + 1

    return sorted(name_count.items(), key=lambda x: -x[1])

def _calc_shop_stats(raw_data_list):
    """
    raw_data 리스트(각 CardPrice.raw_data)에서 샵별 통계 집계.

    Returns:
        {
            "샵이름": {
                "count": 등장 횟수(유효 상품 수),
                "prices": [가격 리스트],
                "avg": 평균가,
                "min": 최저가,
                "max": 최고가,
            },
            ...
        }
    """
    shops = {}
    total_prices = []

    for raw in raw_data_list:
        if isinstance(raw, dict):
            raw = [raw] if raw else []
        if not isinstance(raw, list):
            continue

        for item in raw:
            mall = item.get('mallName', '').strip()
            try:
                price = int(float(item.get('lprice', 0)))
            except (ValueError, TypeError):
                continue
            if not mall or price <= 0:
                continue

            if mall not in shops:
                shops[mall] = {'count': 0, 'prices': []}
            shops[mall]['count'] += 1
            shops[mall]['prices'].append(price)
            total_prices.append(price)

    # 통계 계산
    overall_avg = round(sum(total_prices) / len(total_prices)) if total_prices else 0

    result = []
    for mall, data in shops.items():
        prices = data['prices']
        avg = round(sum(prices) / len(prices))
        diff = avg - overall_avg
        diff_pct = round((diff / overall_avg) * 100, 1) if overall_avg else 0
        result.append({
            'name': mall,
            'count': data['count'],
            'avg': avg,
            'min': min(prices),
            'max': max(prices),
            'diff': diff,           # 전체 평균 대비 차이 (원)
            'diff_pct': diff_pct,   # 전체 평균 대비 차이 (%)
            'cheaper': diff < 0,    # True면 전체 평균보다 저렴
        })

    result.sort(key=lambda x: -x['count'])
    return result, overall_avg


def _load_raw_data(expansion_code=None, rarities=None):
    qs = CardPrice.objects.exclude(raw_data={}).exclude(raw_data=[])
    if expansion_code:
        qs = qs.filter(card__expansion__code=expansion_code)
    if rarities:
        qs = qs.filter(card__rarity__in=rarities)

    # 1단계: raw_data 없이 card_id + id만 추려냄 (메모리 절약)
    seen_cards = {}
    for cp in qs.order_by('-collected_at').values('card_id', 'id'):
        if cp['card_id'] not in seen_cards:
            seen_cards[cp['card_id']] = cp['id']

    # 2단계: 필요한 id만 raw_data 조회
    return list(
        CardPrice.objects.filter(id__in=seen_cards.values())
                         .values_list('raw_data', flat=True)
    )


# ────────────────────────────────────────────────────────────────
# 1. 전체 샵 랭킹
# GET /dashboard/pokemon/kr/shop-stats/
# ────────────────────────────────────────────────────────────────

@staff_required
def pokemon_kr_shop_stats(request):
    raw_list = _load_raw_data()
    shop_stats, overall_avg = _calc_shop_stats(raw_list)

    expansions = Expansion.objects.order_by('-release_date')

    return render(request, 'dashboard/shop_stats.html', {
        'shop_stats_json': json.dumps(shop_stats, ensure_ascii=False),
        'shop_stats': shop_stats,
        'overall_avg': overall_avg,
        'expansion': None,
        'expansions': expansions,
        'total_cards': Card.objects.count(),
        'title': '포켓몬 한글판 전체',
        'breadcrumb': [
            ('홈', '/dashboard/'),
            ('포켓몬 한글판', '/dashboard/pokemon/kr/expansions/'),
            ('경쟁 샵 랭킹', None),
        ],
    })


# ────────────────────────────────────────────────────────────────
# 2. 확장팩별 샵 랭킹
# GET /dashboard/pokemon/kr/shop-stats/<code>/
# ────────────────────────────────────────────────────────────────

@staff_required
def pokemon_kr_shop_stats_detail(request, code):
    expansion = get_object_or_404(Expansion, code=code)
    raw_list = _load_raw_data(expansion_code=code)
    shop_stats, overall_avg = _calc_shop_stats(raw_list)

    expansions = Expansion.objects.order_by('-release_date')

    return render(request, 'dashboard/shop_stats.html', {
        'shop_stats_json': json.dumps(shop_stats, ensure_ascii=False),
        'shop_stats': shop_stats,
        'overall_avg': overall_avg,
        'expansion': expansion,
        'expansions': expansions,
        'total_cards': Card.objects.filter(expansion=expansion).count(),
        'title': expansion.name,
        'breadcrumb': [
            ('홈', '/dashboard/'),
            ('포켓몬 한글판', '/dashboard/pokemon/kr/expansions/'),
            ('경쟁 샵 랭킹', '/dashboard/pokemon/kr/shop-stats/'),
            (expansion.name, None),
        ],
    })

# ── 내부 헬퍼 ────────────────────────────────────────────────────

def _onepiece_collect_mall_names(expansion_code=None, limit=500):
    """원피스 raw_data에서 mallName 빈도 집계"""
    qs = OnePieceCardPrice.objects.exclude(raw_data={}).exclude(raw_data=[])
    if expansion_code:
        qs = qs.filter(card__expansion__code=expansion_code)

    # 카드별 최신 1건 id만 먼저 추출
    seen_cards = {}
    for cp in qs.order_by('-collected_at').values('card_id', 'id'):
        if cp['card_id'] not in seen_cards:
            seen_cards[cp['card_id']] = cp['id']
        if len(seen_cards) >= limit:
            break

    name_count = {}
    for raw in OnePieceCardPrice.objects.filter(id__in=seen_cards.values()).values_list('raw_data', flat=True):
        if isinstance(raw, list):
            for item in raw:
                name = item.get('mallName', '').strip()
                if name:
                    name_count[name] = name_count.get(name, 0) + 1

    return sorted(name_count.items(), key=lambda x: -x[1])


def _onepiece_load_raw_data(expansion_code=None, rarities=None):
    qs = OnePieceCardPrice.objects.exclude(raw_data={}).exclude(raw_data=[])
    if expansion_code:
        qs = qs.filter(card__expansion__code=expansion_code)
    if rarities:
        qs = qs.filter(card__rarity__in=rarities)

    seen_cards = {}
    for cp in qs.order_by('-collected_at').values('card_id', 'id'):
        if cp['card_id'] not in seen_cards:
            seen_cards[cp['card_id']] = cp['id']

    return list(
        OnePieceCardPrice.objects.filter(id__in=seen_cards.values())
                                 .values_list('raw_data', flat=True)
    )


def _onepiece_calc_shop_stats(raw_data_list):
    """raw_data 리스트에서 샵별 통계 집계"""
    shops = {}
    total_prices = []

    for raw in raw_data_list:
        if isinstance(raw, dict):
            raw = [raw] if raw else []
        if not isinstance(raw, list):
            continue
        for item in raw:
            mall = item.get('mallName', '').strip()
            try:
                price = int(float(item.get('lprice', 0)))
            except (ValueError, TypeError):
                continue
            if not mall or price <= 0:
                continue
            if mall not in shops:
                shops[mall] = {'count': 0, 'prices': []}
            shops[mall]['count'] += 1
            shops[mall]['prices'].append(price)
            total_prices.append(price)

    overall_avg = round(sum(total_prices) / len(total_prices)) if total_prices else 0

    result = []
    for mall, data in shops.items():
        prices = data['prices']
        avg = round(sum(prices) / len(prices))
        diff = avg - overall_avg
        diff_pct = round((diff / overall_avg) * 100, 1) if overall_avg else 0
        result.append({
            'name': mall,
            'count': data['count'],
            'avg': avg,
            'min': min(prices),
            'max': max(prices),
            'diff': diff,
            'diff_pct': diff_pct,
            'cheaper': diff < 0,
        })
    result.sort(key=lambda x: -x['count'])
    return result, overall_avg


# ────────────────────────────────────────────────────────────────
# 1. 일괄 설정 + 샵 랭킹 페이지
# GET /dashboard/onepiece/kr/bulk-price/
# ────────────────────────────────────────────────────────────────

@staff_required
def onepiece_kr_bulk_price(request):
    expansion_code = request.GET.get('expansion', '')
    selected_rarities = request.GET.getlist('rarities')  # ← 추가

    selected_expansion = None
    if expansion_code:
        selected_expansion = OnePieceExpansion.objects.filter(code=expansion_code).first()

    mall_names = _onepiece_collect_mall_names(expansion_code=expansion_code or None)
    expansions = list(OnePieceExpansion.objects.order_by('-release_date', '-created_at'))
    needs_review = OnePieceCard.objects.filter(selling_price=0).count()

    # 레어도 목록 추가
    rarity_qs = OnePieceCard.objects.values_list('rarity', flat=True).distinct().order_by('rarity')
    if expansion_code:
        rarity_qs = rarity_qs.filter(expansion__code=expansion_code)
    all_rarities = list(rarity_qs)

    raw_list = _onepiece_load_raw_data(expansion_code=expansion_code or None)
    shop_stats, overall_avg = _onepiece_calc_shop_stats(raw_list)

    return render(request, 'dashboard/bulk_price.html', {
        'mall_names': json.dumps(mall_names),
        'expansions': expansions,
        'needs_review': needs_review,
        'shop_stats_json': json.dumps(shop_stats, ensure_ascii=False),
        'shop_stats': shop_stats,
        'overall_avg': overall_avg,
        'selected_expansion': selected_expansion,
        'expansion_code': expansion_code,
        'all_rarities': all_rarities,                          # ← 추가
        'selected_rarities': selected_rarities,                # ← 추가
        'selected_rarities_json': json.dumps(selected_rarities),  # ← 추가
        'breadcrumb': [
            ('홈', '/dashboard/'),
            ('원피스 한글판', '/dashboard/onepiece/kr/expansions/'),
            ('일괄 판매가 설정', None),
        ],
        'config': {
            'label': '원피스 한글판',
            'expansion_list_url': '/dashboard/onepiece/kr/expansions/',
            'bulk_price_url': '/dashboard/onepiece/kr/bulk-price/',
            'bulk_run_url': '/dashboard/onepiece/kr/bulk-price/run/',
            'bulk_issues_url': '/dashboard/onepiece/kr/bulk-price/issues/',
            'high_rarity_list': "['SP-SEC','SP-SR','SEC','SL']",
        },
    })


# ────────────────────────────────────────────────────────────────
# 2. 즉시 실행
# POST /dashboard/onepiece/kr/bulk-price/run/
# ────────────────────────────────────────────────────────────────

@staff_required
@require_POST
def onepiece_kr_bulk_run(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': '잘못된 요청입니다.'}, status=400)

    priorities = [p.strip() for p in data.get('priorities', []) if p.strip()]
    expansion_code = data.get('expansion_code', '').strip()
    skip_priced = data.get('skip_priced', False)

    if not priorities:
        return JsonResponse({'error': '우선순위를 1개 이상 설정해주세요.'}, status=400)

    cards_qs = OnePieceCard.objects.select_related('expansion').order_by('expansion__code', 'card_number')
    if expansion_code:
        cards_qs = cards_qs.filter(expansion__code=expansion_code)

    from django.db.models import Subquery, OuterRef
    latest_price_id_qs = (
        OnePieceCardPrice.objects
        .filter(card=OuterRef('pk'))
        .exclude(raw_data={})
        .exclude(raw_data=[])
        .order_by('-collected_at')
        .values('id')[:1]
    )
    cards_list = list(cards_qs.annotate(latest_price_id=Subquery(latest_price_id_qs)))

    price_ids = [c.latest_price_id for c in cards_list if c.latest_price_id]
    price_map = {
        cp.id: cp.raw_data
        for cp in OnePieceCardPrice.objects.filter(id__in=price_ids)
    }

    to_update = []
    skipped = []
    needs_review = []

    for card in cards_list:
        if skip_priced and card.selling_price != 0:
            skipped.append(card.id)
            continue

        raw = price_map.get(card.latest_price_id, [])
        if isinstance(raw, dict):
            raw = [raw]

        matched_price = None
        for mall_name in priorities:
            for item in raw:
                if item.get('mallName', '') == mall_name:
                    try:
                        price = int(float(item.get('lprice', 0)))
                        if price > 0:
                            matched_price = price
                    except (ValueError, TypeError):
                        pass
                    break
            if matched_price:
                break

        if matched_price:
            card.selling_price = matched_price
            to_update.append(card)
        else:
            needs_review.append(card.id)

    if to_update:
        OnePieceCard.objects.bulk_update(to_update, ['selling_price'])

    return JsonResponse({
        'success': True,
        'total': len(cards_list),
        'set_count': len(to_update),
        'skipped_count': len(skipped),
        'needs_review_count': len(needs_review),
        'needs_review_ids': needs_review[:100],
    })


# ────────────────────────────────────────────────────────────────
# 3. 점검 필요 목록
# GET /dashboard/onepiece/kr/bulk-price/issues/
# ────────────────────────────────────────────────────────────────

@staff_required
def onepiece_kr_bulk_issues(request):
    expansion_code = request.GET.get('expansion', '')
    selected_rarities = request.GET.getlist('rarities')

    cards_qs = OnePieceCard.objects.filter(selling_price=0).select_related('expansion')  # ← null→0
    if expansion_code:
        cards_qs = cards_qs.filter(expansion__code=expansion_code)
    cards_qs = cards_qs.order_by('expansion__code', 'card_number')

    # 전체 레어도 목록
    rarity_qs = OnePieceCard.objects.values_list('rarity', flat=True).distinct().order_by('rarity')
    if expansion_code:
        rarity_qs = rarity_qs.filter(expansion__code=expansion_code)

    # raw_data
    seen = {}
    for cp in OnePieceCardPrice.objects.filter(card__in=cards_qs)\
                                        .exclude(raw_data={}).exclude(raw_data=[])\
                                        .order_by('-collected_at')\
                                        .values('card_id', 'raw_data'):
        if cp['card_id'] not in seen:
            seen[cp['card_id']] = cp['raw_data']

    expansions = OnePieceExpansion.objects.order_by('-release_date')

    return render(request, 'dashboard/bulk_issues.html', {
        'cards': cards_qs,
        'expansions': expansions,
        'expansion_code': expansion_code,
        'total': cards_qs.count(),
        'card_raw_json': json.dumps(seen, ensure_ascii=False),
        'all_rarities': list(rarity_qs),
        'selected_rarities': selected_rarities,
        'selected_rarities_json': json.dumps(selected_rarities),
        'breadcrumb': [
            ('홈', '/dashboard/'),
            ('원피스 한글판', '/dashboard/onepiece/kr/expansions/'),
            ('일괄 판매가 설정', '/dashboard/onepiece/kr/bulk-price/'),
            ('2차 판매가 설정', None),
        ],
        'config': {
            'label': '원피스 한글판',
            'bulk_price_url': '/dashboard/onepiece/kr/bulk-price/',
            'bulk_issues_url': '/dashboard/onepiece/kr/bulk-price/issues/',
            'set_price_url_prefix': '/dashboard/onepiece/kr/cards/',
            'high_rarity_list': "['SP-SEC','SP-SR','SEC','SL']",
        },
    })

@staff_required
def onepiece_kr_card_search(request):
    q = request.GET.get('name', '').strip()
    page_size = min(int(request.GET.get('page_size', 30)), 50)

    if not q:
        return JsonResponse({'results': []})

    cards = OnePieceCard.objects.filter(name__icontains=q).select_related('expansion').order_by('expansion__release_date', 'card_number')[:page_size]

    results = []
    for card in cards:
        latest = card.prices.first()
        results.append({
            'id': card.id,
            'name': card.name,
            'rarity': card.rarity,
            'card_number': card.card_number,
            'image_url': card.image_url,
            'selling_price': card.selling_price if card.selling_price != 0 else None,
            'latest_price': float(latest.price) if latest else None,
            'expansion': {
                'code': card.expansion.code,
                'name': card.expansion.name,
            }
        })

    return JsonResponse({'results': results})