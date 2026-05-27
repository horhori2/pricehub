# pricehub/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import (
    Prefetch, Count, OuterRef, Subquery, Q, 
    Case, When, Value, IntegerField, Avg, Min, Max
)
from django.utils import timezone

from datetime import datetime, timedelta
import json

from .models import (
    # 포켓몬 한글판
    Expansion, Card, CardPrice,
    # 원피스
    OnePieceExpansion, OnePieceCard, OnePieceCardPrice,
    # 포켓몬 일본판
    JapanExpansion, JapanCard, JapanCardPrice
)


# ==================== 포켓몬 카드 뷰 ====================

def expansion_list(request):
    expansions = Expansion.objects.annotate(
        card_count=Count('cards')
    ).order_by('-release_date', '-created_at')
    return render(request, 'pricehub/expansion_list.html', {'expansions': expansions})


def card_search(request):
    query = request.GET.get('q', '').strip()

    if not query:
        return render(request, 'pricehub/search_results.html', {'query': query, 'cards': [], 'count': 0})

    latest_general_subquery = CardPrice.objects.filter(
        card=OuterRef('pk')
    ).order_by('-collected_at')

    cards = Card.objects.filter(
        Q(name__icontains=query) | Q(card_number__icontains=query)
    ).select_related('expansion').annotate(
        latest_general_price=Subquery(latest_general_subquery.values('price')[:1]),
        latest_general_source=Subquery(latest_general_subquery.values('source')[:1]),
    ).order_by('expansion__code', 'card_number')

    return render(request, 'pricehub/search_results.html', {
        'query': query, 'cards': cards, 'count': cards.count(),
    })


def card_list(request, expansion_code):
    expansion = get_object_or_404(Expansion, code=expansion_code)
    query = request.GET.get('q', '').strip()
    sort_by = request.GET.get('sort', 'number')

    latest_general_subquery = CardPrice.objects.filter(
        card=OuterRef('pk')
    ).order_by('-collected_at')

    cards = Card.objects.filter(expansion=expansion)

    if query:
        cards = cards.filter(Q(name__icontains=query) | Q(card_number__icontains=query))

    cards = cards.annotate(
        latest_general_price=Subquery(latest_general_subquery.values('price')[:1]),
        latest_general_source=Subquery(latest_general_subquery.values('source')[:1]),
    )

    rarity_order = Case(
        When(rarity='MUR', then=Value(1)),
        When(rarity='BWR', then=Value(2)),
        When(rarity='SAR', then=Value(3)),
        When(rarity='UR', then=Value(4)),
        When(rarity='SSR', then=Value(5)),
        When(rarity='SR', then=Value(6)),
        When(rarity='HR', then=Value(7)),
        When(rarity='CSR', then=Value(8)),
        When(rarity='CHR', then=Value(9)),
        When(rarity='AR', then=Value(10)),
        When(rarity='마스터볼', then=Value(11)),
        When(rarity='몬스터볼', then=Value(12)),
        When(rarity='이로치', then=Value(13)),
        When(rarity='미러', then=Value(14)),
        When(rarity='RRR', then=Value(15)),
        When(rarity='RR', then=Value(16)),
        When(rarity='R', then=Value(17)),
        When(rarity='U', then=Value(18)),
        When(rarity='C', then=Value(19)),
        default=Value(99),
        output_field=IntegerField(),
    )

    if sort_by == 'number':
        cards = cards.order_by('card_number')
    elif sort_by == 'name':
        cards = cards.order_by('name', 'card_number')
    elif sort_by == 'rarity':
        cards = cards.annotate(rarity_rank=rarity_order).order_by('rarity_rank', 'card_number')
    elif sort_by == 'general_high':
        cards = cards.order_by('-latest_general_price', 'card_number')
    elif sort_by == 'general_low':
        cards = cards.order_by('latest_general_price', 'card_number')
    else:
        cards = cards.order_by('card_number')

    return render(request, 'pricehub/card_list.html', {
        'expansion': expansion, 'cards': cards, 'query': query,
        'sort_by': sort_by, 'total_count': Card.objects.filter(expansion=expansion).count(),
    })


def card_detail(request, card_id):
    card = get_object_or_404(Card.objects.select_related('expansion'), id=card_id)
    period = request.GET.get('period', '30')

    now = timezone.now()
    if period == '7':
        start_date = now - timedelta(days=7)
        date_format = '%m-%d'
    elif period == '30':
        start_date = now - timedelta(days=30)
        date_format = '%m-%d'
    elif period == '90':
        start_date = now - timedelta(days=90)
        date_format = '%m-%d'
    elif period == 'all':
        start_date = None
        date_format = '%Y-%m-%d'
    else:
        start_date = now - timedelta(days=30)
        date_format = '%m-%d'

    if start_date:
        general_prices = CardPrice.objects.filter(card=card, collected_at__gte=start_date).order_by('collected_at')
    else:
        general_prices = CardPrice.objects.filter(card=card).order_by('collected_at')

    latest_general = CardPrice.objects.filter(card=card).order_by('-collected_at').first()

    stats = {
        'general': {
            'min': min([p.price for p in general_prices]) if general_prices else None,
            'max': max([p.price for p in general_prices]) if general_prices else None,
            'avg': sum([p.price for p in general_prices]) / len(general_prices) if general_prices else None,
        },
    }

    general_chart_data = {
        'labels': json.dumps([p.collected_at.strftime(date_format) for p in general_prices]),
        'data': json.dumps([float(p.price) for p in general_prices])
    }

    return render(request, 'pricehub/card_detail.html', {
        'card': card, 'latest_general': latest_general,
        'general_chart_data': general_chart_data, 'period': period, 'stats': stats,
    })


# ==================== 원피스 카드 뷰 ====================

def onepiece_expansion_list(request):
    expansions = OnePieceExpansion.objects.annotate(
        card_count=Count('cards')
    ).order_by('-release_date', '-created_at')
    return render(request, 'pricehub/onepiece_expansion_list.html', {'expansions': expansions})


def onepiece_card_search(request):
    query = request.GET.get('q', '').strip()

    if not query:
        return render(request, 'pricehub/onepiece_search_results.html', {'query': query, 'cards': [], 'count': 0})

    latest_general_subquery = OnePieceCardPrice.objects.filter(
        card=OuterRef('pk')
    ).order_by('-collected_at')

    cards = OnePieceCard.objects.filter(
        Q(name__icontains=query) | Q(card_number__icontains=query)
    ).select_related('expansion').annotate(
        latest_general_price=Subquery(latest_general_subquery.values('price')[:1]),
        latest_general_source=Subquery(latest_general_subquery.values('source')[:1]),
    ).order_by('expansion__code', 'card_number')

    return render(request, 'pricehub/onepiece_search_results.html', {
        'query': query, 'cards': cards, 'count': cards.count(),
    })


def onepiece_card_list(request, expansion_code):
    expansion = get_object_or_404(OnePieceExpansion, code=expansion_code)
    query = request.GET.get('q', '').strip()
    sort_by = request.GET.get('sort', 'number')

    latest_general_subquery = OnePieceCardPrice.objects.filter(
        card=OuterRef('pk')
    ).order_by('-collected_at')

    cards = OnePieceCard.objects.filter(expansion=expansion)

    if query:
        cards = cards.filter(Q(name__icontains=query) | Q(card_number__icontains=query))

    cards = cards.annotate(
        latest_general_price=Subquery(latest_general_subquery.values('price')[:1]),
        latest_general_source=Subquery(latest_general_subquery.values('source')[:1]),
    )

    rarity_order = Case(
        When(rarity='SEC', then=Value(1)),
        When(rarity='SP-SEC', then=Value(2)),
        When(rarity='P-SEC', then=Value(3)),
        When(rarity='SL', then=Value(4)),
        When(rarity='SP-SL', then=Value(5)),
        When(rarity='P-SL', then=Value(6)),
        When(rarity='SR', then=Value(7)),
        When(rarity='SP-SR', then=Value(8)),
        When(rarity='P-SR', then=Value(9)),
        When(rarity='SP', then=Value(10)),
        When(rarity='L', then=Value(11)),
        When(rarity='P-L', then=Value(12)),
        When(rarity='R', then=Value(13)),
        When(rarity='P-R', then=Value(14)),
        When(rarity='UC', then=Value(15)),
        When(rarity='P-UC', then=Value(16)),
        When(rarity='C', then=Value(17)),
        When(rarity='P-C', then=Value(18)),
        When(rarity='P', then=Value(19)),
        default=Value(99),
        output_field=IntegerField(),
    )

    if sort_by == 'number':
        cards = cards.order_by('card_number')
    elif sort_by == 'name':
        cards = cards.order_by('name', 'card_number')
    elif sort_by == 'rarity':
        cards = cards.annotate(rarity_rank=rarity_order).order_by('rarity_rank', 'card_number')
    elif sort_by == 'general_high':
        cards = cards.order_by('-latest_general_price', 'card_number')
    elif sort_by == 'general_low':
        cards = cards.order_by('latest_general_price', 'card_number')
    else:
        cards = cards.order_by('card_number')

    return render(request, 'pricehub/onepiece_card_list.html', {
        'expansion': expansion, 'cards': cards, 'query': query,
        'sort_by': sort_by, 'total_count': OnePieceCard.objects.filter(expansion=expansion).count(),
    })


def onepiece_card_detail(request, card_id):
    card = get_object_or_404(OnePieceCard.objects.select_related('expansion'), id=card_id)
    period = request.GET.get('period', '30')

    now = timezone.now()
    if period == '7':
        start_date = now - timedelta(days=7)
        date_format = '%m-%d'
    elif period == '30':
        start_date = now - timedelta(days=30)
        date_format = '%m-%d'
    elif period == '90':
        start_date = now - timedelta(days=90)
        date_format = '%m-%d'
    elif period == 'all':
        start_date = None
        date_format = '%Y-%m-%d'
    else:
        start_date = now - timedelta(days=30)
        date_format = '%m-%d'

    if start_date:
        general_prices = OnePieceCardPrice.objects.filter(card=card, collected_at__gte=start_date).order_by('collected_at')
    else:
        general_prices = OnePieceCardPrice.objects.filter(card=card).order_by('collected_at')

    latest_general = OnePieceCardPrice.objects.filter(card=card).order_by('-collected_at').first()

    stats = {
        'general': {
            'min': min([p.price for p in general_prices]) if general_prices else None,
            'max': max([p.price for p in general_prices]) if general_prices else None,
            'avg': sum([p.price for p in general_prices]) / len(general_prices) if general_prices else None,
        },
    }

    general_chart_data = {
        'labels': json.dumps([p.collected_at.strftime(date_format) for p in general_prices]),
        'data': json.dumps([float(p.price) for p in general_prices])
    }

    return render(request, 'pricehub/onepiece_card_detail.html', {
        'card': card, 'latest_general': latest_general,
        'general_chart_data': general_chart_data, 'period': period, 'stats': stats,
    })


# ==================== 포켓몬 일본판 뷰 ====================

def japan_expansion_list(request):
    expansions = JapanExpansion.objects.all().order_by('-release_date', '-created_at')
    for expansion in expansions:
        expansion.card_count = JapanCard.objects.filter(expansion=expansion).count()
        expansion.price_count = JapanCardPrice.objects.filter(
            card__expansion=expansion
        ).values('card').distinct().count()

    return render(request, 'pricehub/japan_expansion_list.html', {
        'expansions': expansions, 'page_title': '포켓몬 일본판 확장팩 목록'
    })


def japan_card_search(request):
    query = request.GET.get('q', '')

    if not query:
        return render(request, 'pricehub/japan_search_results.html', {
            'cards': [], 'query': query, 'page_title': '포켓몬 일본판 카드 검색'
        })

    latest_yuyu_subquery = JapanCardPrice.objects.filter(
        card=OuterRef('pk'), source='유유테이'
    ).order_by('-collected_at').values('price')[:1]

    latest_cardrush_subquery = JapanCardPrice.objects.filter(
        card=OuterRef('pk'), source='카드러쉬', condition='S'
    ).order_by('-collected_at').values('price')[:1]

    cards = JapanCard.objects.filter(
        Q(name__icontains=query) |
        Q(card_number__icontains=query) |
        Q(shop_product_code__icontains=query)
    ).select_related('expansion').annotate(
        latest_yuyu_price=Subquery(latest_yuyu_subquery),
        latest_cardrush_price=Subquery(latest_cardrush_subquery)
    ).order_by('expansion', 'card_number')

    return render(request, 'pricehub/japan_search_results.html', {
        'cards': cards, 'query': query, 'page_title': f'포켓몬 일본판 검색: {query}'
    })


def japan_card_list(request, expansion_code):
    expansion = get_object_or_404(JapanExpansion, code=expansion_code)
    query = request.GET.get('q', '')
    rarity_filter = request.GET.get('rarity', '')
    mirror_filter = request.GET.get('mirror', '')
    sort_by = request.GET.get('sort', 'card_number')

    cards = JapanCard.objects.filter(expansion=expansion).select_related('expansion')

    if query:
        cards = cards.filter(Q(name__icontains=query) | Q(card_number__icontains=query))
    if rarity_filter:
        cards = cards.filter(rarity=rarity_filter)
    if mirror_filter == 'mirror':
        cards = cards.filter(is_mirror=True)
    elif mirror_filter == 'normal':
        cards = cards.filter(is_mirror=False)

    latest_yuyu_subquery = JapanCardPrice.objects.filter(
        card=OuterRef('pk'), source='유유테이'
    ).order_by('-collected_at').values('price')[:1]

    latest_cardrush_s_subquery = JapanCardPrice.objects.filter(
        card=OuterRef('pk'), source='카드러쉬', condition='S'
    ).order_by('-collected_at').values('price')[:1]

    latest_cardrush_a_subquery = JapanCardPrice.objects.filter(
        card=OuterRef('pk'), source='카드러쉬', condition='A-'
    ).order_by('-collected_at').values('price')[:1]

    cards = cards.annotate(
        latest_yuyu_price=Subquery(latest_yuyu_subquery),
        latest_cardrush_s_price=Subquery(latest_cardrush_s_subquery),
        latest_cardrush_a_price=Subquery(latest_cardrush_a_subquery)
    )

    if sort_by == 'card_number':
        cards = cards.order_by('card_number', 'mirror_type')
    elif sort_by == 'name':
        cards = cards.order_by('name')
    elif sort_by == 'rarity':
        cards = cards.order_by('rarity', 'card_number')
    elif sort_by == 'yuyu_price':
        cards = cards.order_by('-latest_yuyu_price', 'card_number')
    elif sort_by == 'cardrush_price':
        cards = cards.order_by('-latest_cardrush_s_price', 'card_number')

    rarities = JapanCard.objects.filter(expansion=expansion).values_list('rarity', flat=True).distinct().order_by('rarity')

    return render(request, 'pricehub/japan_card_list.html', {
        'expansion': expansion, 'cards': cards, 'rarities': rarities,
        'query': query, 'rarity_filter': rarity_filter, 'mirror_filter': mirror_filter,
        'sort_by': sort_by, 'page_title': f'{expansion.name} - 카드 목록'
    })


def japan_card_detail(request, card_id):
    card = get_object_or_404(JapanCard.objects.select_related('expansion'), id=card_id)
    period = request.GET.get('period', '30')

    now = timezone.now()
    if period == '7':
        start_date = now - timedelta(days=7)
        period_label = '1주일'
        date_format = '%m-%d'
    elif period == '90':
        start_date = now - timedelta(days=90)
        period_label = '3개월'
        date_format = '%m-%d'
    elif period == 'all':
        start_date = None
        period_label = '전체'
        date_format = '%Y-%m-%d'
    else:
        start_date = now - timedelta(days=30)
        period_label = '1개월'
        date_format = '%m-%d'

    base_yuyu = JapanCardPrice.objects.filter(card=card, source='유유테이')
    base_cardrush = JapanCardPrice.objects.filter(card=card, source='카드러쉬')

    if start_date:
        yuyu_prices = base_yuyu.filter(collected_at__gte=start_date).order_by('collected_at')
        cardrush_prices = base_cardrush.filter(collected_at__gte=start_date).order_by('collected_at')
    else:
        yuyu_prices = base_yuyu.order_by('collected_at')
        cardrush_prices = base_cardrush.order_by('collected_at')

    cardrush_by_condition = {}
    for price in cardrush_prices:
        cardrush_by_condition.setdefault(price.condition, []).append(price)

    latest_yuyu = yuyu_prices.last() if yuyu_prices.exists() else None
    latest_cardrush_by_condition = {c: prices[-1] for c, prices in cardrush_by_condition.items() if prices}
    latest_cardrush_s = latest_cardrush_by_condition.get('S')

    lowest_price = None
    lowest_source = None
    if latest_yuyu and latest_cardrush_s:
        if latest_yuyu.price <= latest_cardrush_s.price:
            lowest_price, lowest_source = float(latest_yuyu.price), '유유테이'
        else:
            lowest_price, lowest_source = float(latest_cardrush_s.price), '카드러쉬'
    elif latest_yuyu:
        lowest_price, lowest_source = float(latest_yuyu.price), '유유테이'
    elif latest_cardrush_s:
        lowest_price, lowest_source = float(latest_cardrush_s.price), '카드러쉬'

    price_stats = {
        'yuyu': {
            'current': float(latest_yuyu.price) if latest_yuyu else None,
            'min': float(min([p.price for p in yuyu_prices])) if yuyu_prices.exists() else None,
            'max': float(max([p.price for p in yuyu_prices])) if yuyu_prices.exists() else None,
            'avg': float(sum([p.price for p in yuyu_prices]) / len(yuyu_prices)) if yuyu_prices.exists() else None,
        },
        'cardrush': {
            c: {
                'current': float(prices[-1].price),
                'min': float(min([p.price for p in prices])),
                'max': float(max([p.price for p in prices])),
                'avg': float(sum([p.price for p in prices]) / len(prices)),
            }
            for c, prices in cardrush_by_condition.items() if prices
        },
        'lowest': {'price': lowest_price, 'source': lowest_source} if lowest_price else None
    }

    chart_data = {
        'yuyu': {
            'labels': json.dumps([p.collected_at.strftime(date_format) for p in yuyu_prices]),
            'prices': json.dumps([float(p.price) for p in yuyu_prices])
        },
        'cardrush': {
            c: {
                'labels': json.dumps([p.collected_at.strftime(date_format) for p in prices]),
                'prices': json.dumps([float(p.price) for p in prices])
            }
            for c, prices in cardrush_by_condition.items()
        }
    }

    condition_order = ['S', 'A-', 'B', 'C']
    available_conditions = sorted(
        cardrush_by_condition.keys(),
        key=lambda x: condition_order.index(x) if x in condition_order else 99
    )

    return render(request, 'pricehub/japan_card_detail.html', {
        'card': card, 'latest_yuyu': latest_yuyu,
        'latest_cardrush_by_condition': latest_cardrush_by_condition,
        'available_conditions': available_conditions,
        'condition_labels': {'S': 'S급 (신품)', 'A-': 'A-급', 'B': 'B급', 'C': 'C급'},
        'price_stats': price_stats, 'chart_data': chart_data,
        'period': period, 'period_label': period_label,
        'page_title': f'{card.name} - 카드 상세'
    })